"""
MetaPM Quick Capture API
Full voice capture with Whisper + Claude + GCS
"""

import time
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from google.cloud import storage
import httpx

from app.models.task import QuickCaptureRequest, QuickCaptureResponse
from app.models.transaction import VoiceCaptureResponse, TaskSummaryBrief
from app.core.database import execute_procedure, execute_query
from app.core.config import settings

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


async def upload_to_gcs(file: UploadFile, file_type: str) -> dict:
    """Upload file to Google Cloud Storage"""
    client = storage.Client()
    bucket = client.bucket(settings.GCS_MEDIA_BUCKET)
    
    # Generate unique filename
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'webm'
    blob_name = f"{file_type}/{uuid.uuid4()}.{file_ext}"
    blob = bucket.blob(blob_name)
    
    # Upload
    content = await file.read()
    blob.upload_from_string(content, content_type=file.content_type)
    
    return {
        "bucket": settings.GCS_MEDIA_BUCKET,
        "path": blob_name,
        "size": len(content),
        "content_type": file.content_type
    }


async def transcribe_audio(gcs_path: str) -> dict:
    """
    Send audio to OpenAI Whisper for transcription.
    
    Uses Whisper API which provides:
    - Superior noise handling
    - 99%+ accuracy
    - Multiple language support
    """
    # Download from GCS
    client = storage.Client()
    bucket = client.bucket(settings.GCS_MEDIA_BUCKET)
    blob = bucket.blob(gcs_path)
    audio_content = blob.download_as_bytes()
    
    # Call OpenAI Whisper API
    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
            },
            files={
                "file": (gcs_path.split('/')[-1], audio_content, "audio/webm")
            },
            data={
                "model": "whisper-1",
                "response_format": "verbose_json"
            },
            timeout=60.0
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Whisper API error: {response.text}"
            )
        
        result = response.json()
        
        return {
            "text": result.get("text", ""),
            "language": result.get("language", "en"),
            "duration": result.get("duration", 0),
            "confidence": 0.95 if result.get("language") else 0.80
        }


async def understand_with_claude(
    transcription: str,
    project_context: Optional[str] = None
) -> dict:
    """
    Send transcription to Claude for understanding and task extraction.
    
    Claude identifies:
    - Intent (create task, query, update, etc.)
    - Project (if mentioned or inferred)
    - Categories
    - Structured task data
    """
    system_prompt = """You are a task management assistant for MetaPM. 
    
Your job is to understand natural language input and extract structured task information.

Available projects (use these codes):
- AF: ArtForge (art creation, RLHF)
- EM: Etymython (Greek mythology, etymology)
- HL: HarmonyLab (jazz chord training)
- SF: Super-Flashcards (language learning)
- META: Meta Project Manager (this system)
- CUBIST: Cubist Art Software
- VID-*: Video projects
- TRIP-*: Travel projects
- LANG-FRENCH, LANG-GREEK: Language learning
- MUSIC-JAZZ: Jazz piano development

Available categories:
- ACTION: Concrete next step
- IDEA: Concept to explore
- BUG: Defect to fix
- REQUIREMENT: Feature needed
- TEST: Verification task
- RESEARCH: Investigation task

Respond with JSON only:
{
    "intent": "CREATE_TASK" | "QUERY" | "UPDATE" | "SEARCH" | "UNCLEAR",
    "project_code": "XX" | null,
    "categories": ["CATEGORY1", "CATEGORY2"],
    "task_title": "...",
    "task_description": "...",
    "priority": 1-5,
    "response": "Natural language confirmation to user"
}"""

    user_prompt = f"User said: {transcription}"
    if project_context:
        user_prompt += f"\n\nContext: Currently working on project {project_context}"
    
    async with httpx.AsyncClient() as http_client:
        start_time = time.time()
        
        response = await http_client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": user_prompt}
                ]
            },
            timeout=30.0
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Claude API error: {response.text}"
            )
        
        result = response.json()
        content = result["content"][0]["text"]
        
        # Parse JSON from response
        import json
        try:
            # Handle case where Claude wraps in markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            parsed = json.loads(content.strip())
        except json.JSONDecodeError:
            parsed = {
                "intent": "UNCLEAR",
                "response": content,
                "project_code": None,
                "categories": []
            }
        
        # Add token counts for cost tracking
        parsed["prompt_tokens"] = result.get("usage", {}).get("input_tokens", 0)
        parsed["response_tokens"] = result.get("usage", {}).get("output_tokens", 0)
        parsed["processing_time_ms"] = processing_time
        
        return parsed


@router.post("/voice", response_model=VoiceCaptureResponse)
async def voice_capture(
    audio: UploadFile = File(..., description="Audio file (webm, mp3, wav, m4a)"),
    conversation_guid: Optional[str] = Form(None, alias="conversationGuid"),
    project_code: Optional[str] = Form(None, alias="projectCode"),
    source: str = Form(default="MOBILE")
):
    """
    Process voice input end-to-end:
    1. Upload audio to GCS
    2. Transcribe with Whisper
    3. Understand with Claude
    4. Create task if appropriate
    5. Record transaction history
    
    Returns transcription, AI response, and any created task.
    """
    start_time = time.time()
    
    # Validate audio file
    allowed_types = ["audio/webm", "audio/mp3", "audio/mpeg", "audio/wav", "audio/m4a", "audio/x-m4a"]
    if audio.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported audio type: {audio.content_type}. Allowed: {allowed_types}"
        )
    
    # 1. Upload to GCS
    gcs_info = await upload_to_gcs(audio, "audio")
    
    # 2. Record media file
    media_result = execute_query("""
        INSERT INTO MediaFiles (
            FileName, FileType, MimeType, FileSizeBytes,
            GCSBucket, GCSPath, ProcessingStatus, UploadSource
        )
        OUTPUT INSERTED.MediaID, INSERTED.MediaGUID
        VALUES (?, 'AUDIO', ?, ?, ?, ?, 'PROCESSING', ?)
    """, (
        audio.filename,
        audio.content_type,
        gcs_info["size"],
        gcs_info["bucket"],
        gcs_info["path"],
        source
    ), fetch="one")
    
    if not media_result:
        raise HTTPException(status_code=500, detail="Failed to create media record - MediaFiles table may not exist")
    
    media_id = media_result["MediaID"]
    
    # 3. Transcribe with Whisper
    try:
        transcription_result = await transcribe_audio(gcs_info["path"])
    except Exception as e:
        # Update media status to failed
        execute_query(
            "UPDATE MediaFiles SET ProcessingStatus = 'FAILED' WHERE MediaID = ?",
            (media_id,), fetch="none"
        )
        raise HTTPException(status_code=502, detail=f"Transcription failed: {str(e)}")
    
    # Update media with transcription
    execute_query("""
        UPDATE MediaFiles SET 
            ProcessingStatus = 'PROCESSED',
            ProcessedAt = GETUTCDATE(),
            AudioDurationSeconds = ?,
            TranscriptionText = ?
        WHERE MediaID = ?
    """, (
        transcription_result["duration"],
        transcription_result["text"],
        media_id
    ), fetch="none")
    
    # 4. Understand with Claude
    claude_result = await understand_with_claude(
        transcription_result["text"],
        project_code
    )
    
    # 5. Create or get conversation
    if conversation_guid:
        conv_guid = uuid.UUID(conversation_guid)
    else:
        # Start new conversation
        conv_result = execute_procedure("sp_StartConversation", {
            "Source": source,
            "ProjectCode": project_code or claude_result.get("project_code"),
            "Title": transcription_result["text"][:100],
            "DeviceInfo": None,
            "Location": None
        })
        if not conv_result:
            raise HTTPException(status_code=500, detail="Failed to start conversation - sp_StartConversation may not exist")
        conv_guid = conv_result[0]["ConversationGUID"]
    
    # 6. Create task if intent is CREATE_TASK
    task_created = None
    if claude_result.get("intent") == "CREATE_TASK" and claude_result.get("task_title"):
        task_result = execute_procedure("sp_AddTask", {
            "Title": claude_result["task_title"],
            "Description": claude_result.get("task_description"),
            "Priority": claude_result.get("priority", 3),
            "ProjectCode": claude_result.get("project_code"),
            "CategoryCodes": ",".join(claude_result.get("categories", ["IDEA"])),
            "Source": "VOICE"
        })
        
        if task_result:
            task_created = TaskSummaryBrief(
                taskId=task_result[0]["NewTaskID"],
                title=claude_result["task_title"],
                projectCode=claude_result.get("project_code")
            )
    
    # 7. Record transaction
    total_time = int((time.time() - start_time) * 1000)
    
    # Calculate cost (approximate)
    whisper_cost = (transcription_result["duration"] / 60) * 0.006  # $0.006/min
    claude_cost = (claude_result["prompt_tokens"] * 0.003 + claude_result["response_tokens"] * 0.015) / 1000
    total_cost = whisper_cost + claude_cost
    
    trans_result = execute_procedure("sp_RecordTransaction", {
        "ConversationGUID": str(conv_guid),
        "PromptText": transcription_result["text"],
        "PromptType": "VOICE",
        "ResponseText": claude_result.get("response", ""),
        "ResponseModel": "claude-sonnet-4-20250514",
        "AIProvider": "ANTHROPIC",
        "PromptTokens": claude_result.get("prompt_tokens"),
        "ResponseTokens": claude_result.get("response_tokens"),
        "ProcessingTimeMs": total_time,
        "CostUSD": total_cost,
        "AudioDurationSeconds": transcription_result["duration"],
        "TranscriptionConfidence": transcription_result["confidence"],
        "ExtractedIntent": claude_result.get("intent"),
        "ExtractedProjectCode": claude_result.get("project_code"),
        "ExtractedCategories": ",".join(claude_result.get("categories", []))
    })
    
    if not trans_result:
        raise HTTPException(status_code=500, detail="Failed to record transaction - sp_RecordTransaction may not exist")
    
    trans_guid = trans_result[0]["TransactionGUID"]
    
    # Link media to transaction
    execute_query("""
        INSERT INTO TransactionMedia (TransactionID, MediaID, MediaRole)
        SELECT t.TransactionID, ?, 'INPUT'
        FROM Transactions t WHERE t.TransactionGUID = ?
    """, (media_id, str(trans_guid)), fetch="none")
    
    return VoiceCaptureResponse(
        conversationGuid=conv_guid,
        transactionGuid=trans_guid,
        transcription=transcription_result["text"],
        transcriptionConfidence=transcription_result["confidence"],
        aiResponse=claude_result.get("response", "I understood your request."),
        extractedIntent=claude_result.get("intent"),
        extractedProjectCode=claude_result.get("project_code"),
        taskCreated=task_created,
        processingTimeMs=total_time
    )
