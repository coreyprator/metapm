"""
MetaPM Quick Capture API
Minimal endpoint for mobile/voice task capture
"""

from fastapi import APIRouter, HTTPException

from app.models.task import QuickCaptureRequest, QuickCaptureResponse
from app.core.database import execute_procedure

router = APIRouter()


@router.post("", response_model=QuickCaptureResponse, status_code=201)
async def quick_capture(request: QuickCaptureRequest):
    """
    Quick capture endpoint for mobile/voice input.
    
    Minimal required fields - just title.
    Optional project and category for basic classification.
    
    Use case: "Hey Siri, capture task: Add PIE etymology to flashcards for project SF"
    """
    result = execute_procedure("sp_QuickCapture", {
        "Title": request.title,
        "ProjectCode": request.project,
        "CategoryCode": request.category or "IDEA"
    })
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to capture task")
    
    new_task_id = result[0]["NewTaskID"]
    
    return QuickCaptureResponse(
        taskId=new_task_id,
        title=request.title,
        project=request.project,
        category=request.category or "IDEA",
        message=f"Task captured successfully as #{new_task_id}"
    )


@router.post("/voice", response_model=QuickCaptureResponse, status_code=201)
async def voice_capture(request: QuickCaptureRequest):
    """
    Alias for quick capture, explicitly marked as voice source.
    
    Same as /capture but sets source to VOICE for tracking.
    """
    # Use the full sp_AddTask to set source
    from app.core.database import execute_query
    
    # Insert task
    result = execute_query("""
        INSERT INTO Tasks (Title, Source, Status)
        OUTPUT INSERTED.TaskID
        VALUES (?, 'VOICE', 'NEW')
    """, (request.title,), fetch="one")
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to capture task")
    
    new_task_id = result["TaskID"]
    
    # Link to project if provided
    if request.project:
        execute_query("""
            INSERT INTO TaskProjectLinks (TaskID, ProjectID, IsPrimary)
            SELECT ?, ProjectID, 1 FROM Projects WHERE ProjectCode = ?
        """, (new_task_id, request.project), fetch="none")
    
    # Link to category
    category = request.category or "IDEA"
    execute_query("""
        INSERT INTO TaskCategoryLinks (TaskID, CategoryID)
        SELECT ?, CategoryID FROM Categories WHERE CategoryCode = ?
    """, (new_task_id, category), fetch="none")
    
    return QuickCaptureResponse(
        taskId=new_task_id,
        title=request.title,
        project=request.project,
        category=category,
        message=f"Voice task captured as #{new_task_id}"
    )
