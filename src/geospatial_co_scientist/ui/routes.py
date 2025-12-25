"""API routes for the Geospatial AI Co-Scientist."""

import asyncio
import logging
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from geospatial_co_scientist.models.research import ResearchOverview
from geospatial_co_scientist.orchestration.workflow import GeospatialCoScientist

logger = logging.getLogger(__name__)

router = APIRouter(tags=["research"])

# Store active sessions
_sessions: dict[str, GeospatialCoScientist] = {}


class ResearchRequest(BaseModel):
    """Request model for starting research."""

    question: str = Field(..., description="The research question")
    domain: str = Field(default="general_gis", description="Research domain")
    context: Optional[str] = Field(default=None, description="Additional context")
    constraints: list[str] = Field(default_factory=list, description="Research constraints")
    keywords: list[str] = Field(default_factory=list, description="Keywords")
    max_iterations: int = Field(default=3, ge=1, le=10, description="Max iterations")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "How can satellite imagery detect urban heat islands?",
                "domain": "remote_sensing",
                "context": "Focus on tropical cities",
                "constraints": ["Use freely available data"],
                "keywords": ["thermal", "Landsat", "NDVI"],
                "max_iterations": 3
            }
        }


class FeedbackRequest(BaseModel):
    """Request model for providing feedback."""

    feedback: str = Field(..., description="Feedback text")


class SessionResponse(BaseModel):
    """Response model for session info."""

    session_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    """Response model for session status."""

    session_id: str
    status: dict[str, Any]
    hypotheses_count: int
    top_hypotheses: list[dict[str, Any]]


@router.post("/research", response_model=SessionResponse)
async def start_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a new research session.

    This endpoint initiates an asynchronous research session that runs in the background.
    Use the session_id to check status and retrieve results.
    """
    session_id = str(uuid4())
    scientist = GeospatialCoScientist()
    _sessions[session_id] = scientist

    # Start research in background
    background_tasks.add_task(
        run_research_background,
        session_id,
        scientist,
        request
    )

    return SessionResponse(
        session_id=session_id,
        status="started",
        message="Research session started. Use GET /research/{session_id}/status to check progress."
    )


async def run_research_background(
    session_id: str,
    scientist: GeospatialCoScientist,
    request: ResearchRequest
):
    """Run research in the background."""
    try:
        await scientist.research(
            question=request.question,
            domain=request.domain,
            context=request.context,
            constraints=request.constraints,
            keywords=request.keywords,
            max_iterations=request.max_iterations
        )
        logger.info(f"Research session {session_id} completed")
    except Exception as e:
        logger.error(f"Research session {session_id} failed: {e}")


@router.get("/research/{session_id}/status", response_model=StatusResponse)
async def get_status(session_id: str):
    """Get the status of a research session."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    scientist = _sessions[session_id]
    status = scientist.get_status()
    top_hyps = scientist.get_top_hypotheses(3)

    return StatusResponse(
        session_id=session_id,
        status=status,
        hypotheses_count=len(scientist.get_hypotheses()),
        top_hypotheses=top_hyps
    )


@router.get("/research/{session_id}/hypotheses")
async def get_hypotheses(
    session_id: str,
    top_n: int = 10
):
    """Get hypotheses from a research session."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    scientist = _sessions[session_id]
    hypotheses = scientist.get_hypotheses()

    # Sort by Elo score
    sorted_hyps = sorted(
        hypotheses,
        key=lambda x: x.get("elo_score", 1000),
        reverse=True
    )

    return {
        "session_id": session_id,
        "total": len(hypotheses),
        "hypotheses": sorted_hyps[:top_n]
    }


@router.get("/research/{session_id}/experiments")
async def get_experiments(session_id: str):
    """Get experiment designs from a research session."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    scientist = _sessions[session_id]
    experiments = scientist.get_experiment_designs()

    return {
        "session_id": session_id,
        "total": len(experiments),
        "experiments": experiments
    }


@router.get("/research/{session_id}/overview")
async def get_overview(session_id: str):
    """Get the full research overview."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    scientist = _sessions[session_id]

    if not scientist._current_state:
        raise HTTPException(status_code=400, detail="Research not started")

    overview_data = scientist._current_state.research_overview
    if not overview_data:
        # Generate basic overview
        overview = scientist._create_basic_overview(
            scientist._current_state.model_dump()
        )
        return overview.model_dump()

    return overview_data


@router.post("/research/{session_id}/feedback")
async def provide_feedback(
    session_id: str,
    request: FeedbackRequest
):
    """Provide feedback to a research session."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    scientist = _sessions[session_id]

    try:
        await scientist.provide_feedback(request.feedback)
        return {
            "session_id": session_id,
            "status": "feedback_received",
            "message": "Feedback processed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/research/{session_id}")
async def delete_session(session_id: str):
    """Delete a research session."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    del _sessions[session_id]
    return {"message": "Session deleted"}


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time updates.

    Clients can connect to receive live updates about research progress.
    """
    await websocket.accept()

    if session_id not in _sessions:
        await websocket.send_json({"error": "Session not found"})
        await websocket.close()
        return

    scientist = _sessions[session_id]

    try:
        while True:
            # Send status updates
            status = scientist.get_status()
            await websocket.send_json({
                "type": "status",
                "data": status
            })

            # Check for client messages
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=2.0
                )

                if data.get("type") == "feedback":
                    await scientist.provide_feedback(data.get("feedback", ""))
                    await websocket.send_json({
                        "type": "feedback_received",
                        "message": "Feedback processed"
                    })

            except asyncio.TimeoutError:
                pass  # No message, continue polling

            # Check if session is complete
            if scientist._current_state and not scientist._current_state.should_continue:
                await websocket.send_json({
                    "type": "complete",
                    "data": scientist.get_status()
                })
                break

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")


@router.get("/datasets")
async def list_datasets():
    """List available geospatial datasets."""
    from geospatial_co_scientist.tools.geospatial import GEOSPATIAL_DATASETS

    return {
        "datasets": [
            {
                "key": key,
                "name": ds.name,
                "provider": ds.provider,
                "resolution": ds.spatial_resolution,
                "coverage": ds.coverage
            }
            for key, ds in GEOSPATIAL_DATASETS.items()
        ]
    }


@router.get("/methodologies/{analysis_type}")
async def get_methodology(analysis_type: str):
    """Get methodology recommendations for an analysis type."""
    from geospatial_co_scientist.tools.geospatial import GeospatialAnalysisTool

    tool = GeospatialAnalysisTool()
    methods = tool.get_analysis_methods(analysis_type)

    if not methods:
        raise HTTPException(
            status_code=404,
            detail=f"No methodology found for: {analysis_type}"
        )

    return methods
