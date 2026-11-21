from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_chain
from app.blockchain.contract_service import ChainClient
from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db), chain: ChainClient = Depends(get_chain)):
    try:
        db.execute(text("SELECT 1"))
        database_ok = True
    except Exception:  # noqa: BLE001
        database_ok = False

    blockchain = chain.health()
    all_ok = database_ok and blockchain["connected"]
    return {
        "status": "ok" if all_ok else "degraded",
        "service": "backend",
        "database": {"connected": database_ok},
        "blockchain": blockchain,
    }