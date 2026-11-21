"""Blockchain interface used by the services.

The services depend on the small `ChainClient` interface below, not on web3 directly.
`Web3ChainClient` (web3_client.py) is the real implementation. `InMemoryChainClient`
is a TEST DOUBLE that copies the contract's rules so the API can be tested without a
running node; it is never used by the running application.
"""
import time
from dataclasses import dataclass
from typing import Optional, Protocol

ZERO_COMMITMENT = "0x" + "00" * 32


class ChainError(Exception):
    """Base class for blockchain problems."""


class ChainUnavailableError(ChainError):
    """Node unreachable, contract not deployed, or misconfigured: nothing was written."""


class ChainTransactionError(ChainError):
    """The chain was reached but rejected the transaction (revert, no permission, ...)."""


@dataclass(frozen=True)
class ChainRecord:
    exists: bool
    commitment: str
    issuer: str
    issued_at: int  # unix seconds
    revoked: bool


@dataclass(frozen=True)
class TxResult:
    tx_hash: str
    gas_used: int
    issuer: str


class ChainClient(Protocol):
    def health(self) -> dict: ...
    def get(self, cert_key: str) -> ChainRecord: ...
    def register(self, cert_key: str, commitment: str) -> TxResult: ...
    def revoke(self, cert_key: str) -> TxResult: ...
    def is_authorized_issuer(self, address: str) -> bool: ...


def build_chain_client() -> ChainClient:
    """Create the real web3 client from the application settings."""
    from app.blockchain.web3_client import Web3ChainClient
    from app.core.config import ABI_FILE, settings

    return Web3ChainClient(
        rpc_url=settings.blockchain_rpc_url,
        address_provider=settings.resolved_contract_address,
        private_key=settings.issuer_private_key,
        abi_path=ABI_FILE,
    )


class InMemoryChainClient:
    """Test double that mimics CertificateRegistry. Knobs let tests simulate failures."""

    ISSUER = "0x" + "11" * 20

    def __init__(self) -> None:
        self.records: dict[str, dict] = {}
        self.available = True
        self.fail_register: Optional[Exception] = None
        self.signer_is_issuer = True
        self.issuer_authorized = True
        self.register_calls = 0
        self._counter = 0

    # --- helpers
    def _require_available(self) -> None:
        if not self.available:
            raise ChainUnavailableError("Simulated blockchain outage.")

    def _tx(self) -> TxResult:
        self._counter += 1
        return TxResult(tx_hash="0x" + f"{self._counter:064x}", gas_used=70000, issuer=self.ISSUER)

    # --- ChainClient interface
    def health(self) -> dict:
        return {
            "connected": self.available,
            "chain_id": 31337,
            "block_number": self._counter,
            "contract_address": "0x" + "22" * 20,
            "signer": self.ISSUER,
            "signer_is_issuer": self.signer_is_issuer,
            "error": None if self.available else "Simulated blockchain outage.",
        }

    def get(self, cert_key: str) -> ChainRecord:
        self._require_available()
        rec = self.records.get(cert_key.lower())
        if rec is None:
            return ChainRecord(False, ZERO_COMMITMENT, "0x" + "00" * 20, 0, False)
        return ChainRecord(True, rec["commitment"], rec["issuer"], rec["issued_at"], rec["revoked"])

    def register(self, cert_key: str, commitment: str) -> TxResult:
        self._require_available()
        self.register_calls += 1
        if self.fail_register is not None:
            raise self.fail_register
        if not self.signer_is_issuer:
            raise ChainTransactionError("Contract rejected the call: AccessControlUnauthorizedAccount")
        if commitment.lower() == ZERO_COMMITMENT:
            raise ChainTransactionError("Contract rejected the call: ZeroCommitment")
        key = cert_key.lower()
        if key in self.records:
            raise ChainTransactionError("Contract rejected the call: AlreadyRegistered")
        self.records[key] = {
            "commitment": commitment.lower(),
            "issuer": self.ISSUER,
            "issued_at": int(time.time()),
            "revoked": False,
        }
        return self._tx()

    def revoke(self, cert_key: str) -> TxResult:
        self._require_available()
        rec = self.records.get(cert_key.lower())
        if rec is None:
            raise ChainTransactionError("Contract rejected the call: NotRegistered")
        if rec["revoked"]:
            raise ChainTransactionError("Contract rejected the call: AlreadyRevoked")
        if not self.signer_is_issuer:
            raise ChainTransactionError("Contract rejected the call: NotAllowedToRevoke")
        rec["revoked"] = True
        return self._tx()

    def is_authorized_issuer(self, address: str) -> bool:
        self._require_available()
        return self.issuer_authorized