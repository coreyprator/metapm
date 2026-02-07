"""
MetaPM Capture API
==================

Handles voice and text captures, integrating:
- Whisper for transcription
- Claude for understanding
- Task creation
- Transaction logging
"""

import os
import logging
import httpx
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.core.database import execute_query, execute_procedure

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# MODELS
# ============================================

class TextCaptureRequest(BaseModel):
    text: str
    projectCode: Optional[str] = None


# ============================================
# HELPERS
# ============================================

async def call_whisper(audio_data: bytes) -> dict:
    """Transcribe audio using OpenAI Whisper API."""
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": ("audio.webm", audio_data, "audio/webm")},
            data={"model": "whisper-1"},
            timeout=30.0
        )
        
        if response.status_code != 200:
            logger.error(f"Whisper error: {response.text}")
            raise HTTPException(status_code=502, detail="Transcription failed")
        
        return response.json()


async def call_claude(text: str, project_code: Optional[str] = None) -> dict:
    """Use Claude to understand the capture and extract intent."""
    api_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")
    
    # Get available projects for context
    available_projects = []
    try:
        projects = execute_query("SELECT ProjectCode, ProjectName FROM Projects WHERE Status = 'ACTIVE' OR Status = 'NOT_STARTED' ORDER BY ProjectCode")
        available_projects = [f"{p['ProjectCode']} ({p['ProjectName']})" for p in projects[:20]]  # Limit to 20 for prompt size
    except Exception as e:
        logger.warning(f"Could not fetch projects for Claude context: {e}")
    
    projects_context = ""
    if available_projects:
        projects_context = "\n\nAvailable projects:\n" + "\n".join(f"- {p}" for p in available_projects)
    
    system_prompt = """You are a task management assistant. Analyze the user's input and extract:
1. Intent: CREATE_TASK, UPDATE_TASK, QUERY, NOTE, or OTHER
2. If CREATE_TASK:
   - title: A concise task title
   - description: Additional details
   - priority: 1-5 (1=critical, 5=someday). Default 3.
   - projectCode: If mentioned or inferable from available projects
   - categories: Any applicable categories
""" + projects_context + """

Respond with JSON only:
{
    "intent": "CREATE_TASK",
    "task": {
        "title": "...",
        "description": "...",
        "priority": 3,
        "projectCode": "META",
        "categories": ["BUG"]
    },
    "response": "I'll create that task for you."
}

Or for other intents:
{
    "intent": "NOTE",
    "response": "Got it, I've noted that.",
    "summary": "..."
}"""

    if project_code:
        system_prompt += f"\n\nContext: The user is working on project {project_code}."

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "system": system_prompt,
                "messages": [{"role": "user", "content": text}]
            },
            timeout=30.0
        )
        
        if response.status_code != 200:
            logger.error(f"Claude error: {response.text}")
            raise HTTPException(status_code=502, detail="AI processing failed")
        
        result = response.json()
        content = result["content"][0]["text"]
        
        # Parse JSON from response
        import json
        try:
            # Strip markdown if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
        except json.JSONDecodeError:
            return {
                "intent": "NOTE",
                "response": content,
                "summary": text[:100]
            }


def create_conversation(source: str, project_code: Optional[str] = None, title: Optional[str] = None) -> dict:
    """Create a new conversation record."""
    result = execute_procedure("sp_StartConversation", {
        "Source": source,
        "ProjectCode": project_code,
        "Title": title
    })
    
    if result and len(result) > 0:
        return result[0]
    
    # Fallback: create directly
    query = """
        INSERT INTO Conversations (Source, Title)
        OUTPUT INSERTED.ConversationID, INSERTED.ConversationGUID, INSERTED.CreatedAt
        VALUES (?, ?)
    """
    return execute_query(query, (source, title), fetch="one")


def record_transaction(conversation_guid: str, prompt: str, response: str, intent: str = None, project_code: str = None):
    """Record a transaction in the conversation."""
    try:
        execute_procedure("sp_RecordTransaction", {
            "ConversationGUID": conversation_guid,
            "PromptText": prompt,
            "PromptType": "TEXT",
            "ResponseText": response,
            "ResponseModel": "claude-sonnet-4-20250514",
            "AIProvider": "ANTHROPIC",
            "ExtractedIntent": intent,
            "ExtractedProjectCode": project_code
        })
    except Exception as e:
        logger.error(f"Failed to record transaction: {e}")


def create_task_from_capture(task_data: dict) -> dict:
    """Create a task from Claude's extracted data."""
    query = """
        INSERT INTO Tasks (Title, Description, Priority, Status)
        OUTPUT INSERTED.TaskID
        VALUES (?, ?, ?, 'NEW')
    """
    
    result = execute_query(
        query,
        (task_data.get('title'), task_data.get('description'), task_data.get('priority', 3)),
        fetch="one"
    )
    
    task_id = result['TaskID']
    
    # Link to project if specified
    project_code = task_data.get('projectCode')
    if project_code:
        project = execute_query(
            "SELECT ProjectID FROM Projects WHERE ProjectCode = ?",
            (project_code,),
            fetch="one"
        )
        if project:
            execute_query(
                "INSERT INTO TaskProjectLinks (TaskID, ProjectID) VALUES (?, ?)",
                (task_id, project['ProjectID']),
                fetch="none"
            )
    
    # Link to categories
    for cat_code in task_data.get('categories', []):
        cat = execute_query(
            "SELECT CategoryID FROM Categories WHERE CategoryCode = ?",
            (cat_code,),
            fetch="one"
        )
        if cat:
            execute_query(
                "INSERT INTO TaskCategoryLinks (TaskID, CategoryID) VALUES (?, ?)",
                (task_id, cat['CategoryID']),
                fetch="none"
            )
    
    return {"taskId": task_id, "title": task_data.get('title')}


# ============================================
# ENDPOINTS
# ============================================

@router.post("/text")
async def capture_text(request: TextCaptureRequest):
    """Process a text capture."""
    try:
        # Create conversation
        conv = create_conversation(
            source="WEB",
            project_code=request.projectCode,
            title=request.text[:100]
        )
        
        conv_guid = conv.get('ConversationGUID') or conv.get('conversationGuid')
        
        # Process with Claude
        ai_result = await call_claude(request.text, request.projectCode)
        
        # Record transaction
        if conv_guid:
            record_transaction(
                conversation_guid=str(conv_guid),
                prompt=request.text,
                response=ai_result.get('response', ''),
                intent=ai_result.get('intent'),
                project_code=ai_result.get('task', {}).get('projectCode') or request.projectCode
            )
        
        # Create task if intent is CREATE_TASK
        task_created = None
        if ai_result.get('intent') == 'CREATE_TASK' and ai_result.get('task'):
            task_created = create_task_from_capture(ai_result['task'])
        
        return {
            "success": True,
            "message": ai_result.get('response', 'Captured!'),
            "intent": ai_result.get('intent'),
            "taskCreated": task_created,
            "conversationId": str(conv_guid) if conv_guid else None
        }
        
    except Exception as e:
        logger.error(f"Text capture error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice")
async def capture_voice(
    audio: UploadFile = File(...),
    projectCode: Optional[str] = Form(default=None)
):
    """Process a voice capture."""
    try:
        # Read audio data
        audio_data = await audio.read()
        
        # Create conversation
        conv = create_conversation(
            source="VOICE",
            project_code=projectCode,
            title="Voice capture"
        )
        
        conv_guid = conv.get('ConversationGUID') or conv.get('conversationGuid')
        
        # Transcribe with Whisper
        whisper_result = await call_whisper(audio_data)
        transcript = whisper_result.get('text', '')
        
        if not transcript:
            return {
                "success": False,
                "message": "Could not transcribe audio",
                "transcript": ""
            }
        
        # Update conversation title
        if conv_guid:
            execute_query(
                "UPDATE Conversations SET Title = ? WHERE ConversationGUID = ?",
                (transcript[:100], str(conv_guid)),
                fetch="none"
            )
        
        # Process with Claude
        ai_result = await call_claude(transcript, projectCode)
        
        # Record transaction
        if conv_guid:
            record_transaction(
                conversation_guid=str(conv_guid),
                prompt=transcript,
                response=ai_result.get('response', ''),
                intent=ai_result.get('intent'),
                project_code=ai_result.get('task', {}).get('projectCode') or projectCode
            )
        
        # Create task if intent is CREATE_TASK
        task_created = None
        if ai_result.get('intent') == 'CREATE_TASK' and ai_result.get('task'):
            task_created = create_task_from_capture(ai_result['task'])
        
        return {
            "success": True,
            "message": ai_result.get('response', 'Voice captured!'),
            "transcript": transcript,
            "intent": ai_result.get('intent'),
            "taskCreated": task_created,
            "conversationId": str(conv_guid) if conv_guid else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice capture error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
