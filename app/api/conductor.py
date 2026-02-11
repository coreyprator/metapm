"""
Conductor API — Routes CC/CAI status updates through MetaPM (HO-Q5R6)

Endpoints:
  POST /api/conductor/update   - CC reports handoff status
  POST /api/conductor/dispatch - CAI dispatches work to CC
  GET  /api/conductor/status   - Dashboard data (all active handoffs)
  GET  /api/conductor/inbox    - CC polls for pending work
"""

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/api/conductor", tags=["Conductor"])

# In-memory state (prototype — replace with DB table in production)
conductor_state: dict = {}


class ConductorUpdate(BaseModel):
    id: str
    status: str
    file_path: Optional[str] = None
    project: Optional[str] = None
    timestamp: Optional[str] = None


class ConductorDispatch(BaseModel):
    id: str
    project: str
    prompt: str
    source: str  # "CAI" or "COREY"


@router.post("/update")
async def update_conductor_state(update: ConductorUpdate):
    """CC or conductor agent reports a handoff status update."""
    conductor_state[update.id] = {
        "id": update.id,
        "status": update.status,
        "project": update.project,
        "file_path": update.file_path,
        "updated_at": update.timestamp or datetime.now().isoformat(),
        "source": "CC",
    }
    return {"success": True, "id": update.id, "status": update.status}


@router.post("/dispatch")
async def dispatch_to_cc(dispatch: ConductorDispatch):
    """CAI dispatches work to CC inbox."""
    conductor_state[dispatch.id] = {
        "id": dispatch.id,
        "project": dispatch.project,
        "status": "PENDING",
        "prompt": dispatch.prompt,
        "dispatched_at": datetime.now().isoformat(),
        "source": dispatch.source,
    }
    return {"success": True, "id": dispatch.id, "status": "PENDING"}


@router.get("/status")
async def get_conductor_status():
    """Get all active handoffs for dashboard."""
    return {
        "handoffs": list(conductor_state.values()),
        "count": len(conductor_state),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/inbox")
async def get_cc_inbox():
    """CC polls this for pending work dispatched by CAI."""
    pending = [h for h in conductor_state.values() if h.get("status") == "PENDING"]
    return {"pending": pending, "count": len(pending)}
