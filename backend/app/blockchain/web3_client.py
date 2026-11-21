"""Real blockchain client built on web3.py (talks to the Hardhat node or any EVM chain)."""
import json
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

import requests
from web3 import Web3
from web3.exceptions import ContractLogicError

from app.blockchain.contract_service import (
    ChainError,
    ChainRecord,
    ChainTransactionError,
    ChainUnavailableError,
    TxResult,
)
from app.crypto.hashing import hex_to_bytes32


class Web3ChainClient:
    """Connects lazily, so the backend can start before the node is running.

    The contract address is looked up on every (re)connect, so redeploying the contract
    after a node restart works without restarting the backend.
    """

    def __init__(
        self,
        rpc_url: str,
        address_provider: Callable[[], str],
        private_key: str,
        abi_path: Path,
        timeout: int = 10,
    ) -> None:
        self._rpc_url = rpc_url
        self._address_provider = address_provider
        self._private_key = private_key.strip()
        self._abi_path = Path(abi_path)
        self._timeout = timeout
        self._lock = threading.Lock()
        self._w3 = None
        self._contract = None
        self._account = None

    # ------------------------------------------------------------ connection
    def _reset(self) -> None:
        self._w3 = None
        self._contract = None
        self._account = None

    def _connect(self):
        if self._contract is not None:
            return self._contract

        address = (self._address_provider() or "").strip()
        if not address:
            raise ChainUnavailableError(
                "Contract address is not configured. Deploy the contract first (npm run deploy)."
            )
        try:
            abi = json.loads(self._abi_path.read_text(encoding="utf-8"))["abi"]
        except (OSError, ValueError, KeyError) as exc:
            raise ChainUnavailableError(f"Cannot read the contract ABI file: {exc}") from exc

        w3 = Web3(Web3.HTTPProvider(self._rpc_url, request_kwargs={"timeout": self._timeout}))
        try:
            reachable = w3.is_connected()
        except Exception:  # noqa: BLE001
            reachable = False
        if not reachable:
            raise ChainUnavailableError(f"Cannot connect to the blockchain node at {self._rpc_url}.")

        try:
            checksum = Web3.to_checksum_address(address)
        except ValueError as exc:
            raise ChainUnavailableError(f"Invalid contract address '{address}'.") from exc
        if len(w3.eth.get_code(checksum)) == 0:
            raise ChainUnavailableError(
                "No contract exists at the configured address. If the node was restarted, "
                "run `npm run deploy` again."
            )

        self._w3 = w3
        self._contract = w3.eth.contract(address=checksum, abi=abi)
        self._account = w3.eth.account.from_key(self._private_key) if self._private_key else None
        return self._contract

    @contextmanager
    def _guard(self, write: bool = False):
        """Translate low-level errors into ChainUnavailableError / ChainTransactionError."""
        try:
            yield
        except ChainError:
            raise
        except (requests.exceptions.RequestException, ConnectionError, TimeoutError, OSError) as exc:
            self._reset()
            raise ChainUnavailableError(f"Blockchain node unreachable: {exc}") from exc
        except ContractLogicError as exc:
            if write:
                raise ChainTransactionError(f"Contract rejected the call: {exc}") from exc
            raise ChainUnavailableError(f"Contract call failed: {exc}") from exc
        except Exception as exc:  # noqa: BLE001  (web3 / RPC errors)
            self._reset()
            if write:
                raise ChainTransactionError(f"Blockchain error: {exc}") from exc
            raise ChainUnavailableError(f"Blockchain error: {exc}") from exc

    # ---------------------------------------------------------------- reads
    def health(self) -> dict:
        info = {
            "connected": False,
            "chain_id": None,
            "block_number": None,
            "contract_address": None,
            "signer": None,
            "signer_is_issuer": None,
            "error": None,
        }
        try:
            contract = self._connect()
            w3 = self._w3
            info.update(
                connected=True,
                chain_id=w3.eth.chain_id,
                block_number=w3.eth.block_number,
                contract_address=contract.address,
            )
            if self._account is not None:
                info["signer"] = self._account.address
                info["signer_is_issuer"] = bool(
                    contract.functions.isAuthorizedIssuer(self._account.address).call()
                )
        except ChainError as exc:
            info["error"] = str(exc)
        except Exception as exc:  # noqa: BLE001
            self._reset()
            info.update(connected=False, error=f"{type(exc).__name__}: {exc}")
        return info

    def get(self, cert_key: str) -> ChainRecord:
        with self._guard():
            contract = self._connect()
            exists, commitment, issuer, issued_at, revoked = contract.functions.getCertificate(
                hex_to_bytes32(cert_key)
            ).call()
            return ChainRecord(
                exists=bool(exists),
                commitment="0x" + bytes(commitment).hex(),
                issuer=issuer,
                issued_at=int(issued_at),
                revoked=bool(revoked),
            )

    def is_authorized_issuer(self, address: str) -> bool:
        with self._guard():
            contract = self._connect()
            return bool(contract.functions.isAuthorizedIssuer(Web3.to_checksum_address(address)).call())

    # --------------------------------------------------------------- writes
    def register(self, cert_key: str, commitment: str) -> TxResult:
        with self._guard(write=True):
            contract = self._connect()
            return self._send(
                contract.functions.registerCertificate(hex_to_bytes32(cert_key), hex_to_bytes32(commitment))
            )

    def revoke(self, cert_key: str) -> TxResult:
        with self._guard(write=True):
            contract = self._connect()
            return self._send(contract.functions.revokeCertificate(hex_to_bytes32(cert_key)))

    def _send(self, contract_call) -> TxResult:
        if self._account is None:
            raise ChainTransactionError("ISSUER_PRIVATE_KEY is not configured in backend/.env.")
        w3 = self._w3
        with self._lock:  # one transaction at a time keeps nonces in order
            tx = contract_call.build_transaction(
                {
                    "from": self._account.address,
                    "nonce": w3.eth.get_transaction_count(self._account.address, "pending"),
                    "chainId": w3.eth.chain_id,
                }
            )
            signed = self._account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        if receipt["status"] != 1:
            raise ChainTransactionError("The transaction was mined but reverted.")
        return TxResult(
            tx_hash="0x" + tx_hash.hex().removeprefix("0x"),
            gas_used=int(receipt["gasUsed"]),
            issuer=self._account.address,
        )