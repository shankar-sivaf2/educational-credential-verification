"""Application settings, read from environment variables / backend/.env."""
import json
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
ABI_DIR = BACKEND_DIR / "app" / "blockchain" / "abi"
ABI_FILE = ABI_DIR / "CertificateRegistry.json"
DEPLOYMENT_FILE = ABI_DIR / "deployment.json"
STORAGE_DIR = PROJECT_ROOT / "storage"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "An Efficient Blockchain-Based Approach to Educational Credential Verification"
    database_url: str = f"sqlite:///{(STORAGE_DIR / 'database' / 'credentials.db').as_posix()}"

    # Auth
    jwt_secret: str = "dev-only-change-me"
    jwt_expire_minutes: int = 60
    admin_username: str = "admin"
    admin_password: str = ""  # if empty, no admin is created automatically

    # Blockchain
    blockchain_rpc_url: str = "http://127.0.0.1:8545"
    contract_address: str = ""  # if empty, deployment.json written by deploy.js is used
    issuer_private_key: str = ""  # local Hardhat test key only; never a real wallet key

    frontend_origin: str = "http://localhost:5173"

    def resolved_contract_address(self) -> str:
        if self.contract_address.strip():
            return self.contract_address.strip()
        if DEPLOYMENT_FILE.exists():
            try:
                return json.loads(DEPLOYMENT_FILE.read_text(encoding="utf-8"))["address"]
            except (OSError, ValueError, KeyError):
                return ""
        return ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()