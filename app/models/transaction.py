"""
Transaction and Voice Capture Models
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class TaskSummaryBrief(BaseModel):
    """Brief task information for responses"""
    taskId: int
    title: str
    projectCode: Optional[str] = None


class VoiceCaptureRequest(BaseModel):
    """Request model for voice capture (multipart form)"""
    conversationGuid: Optional[str] = None
    projectCode: Optional[str] = None
    source: str = "MOBILE"


class VoiceCaptureResponse(BaseModel):
    """Response from voice capture endpoint"""
    conversationGuid: UUID
    transactionGuid: UUID
    transcription: str
    transcriptionConfidence: float
    aiResponse: str
    extractedIntent: Optional[str] = None
    extractedProjectCode: Optional[str] = None
    taskCreated: Optional[TaskSummaryBrief] = None
    processingTimeMs: int


class TextCaptureRequest(BaseModel):
    """Request model for text-based capture"""
    text: str
    conversationGuid: Optional[str] = None
    projectCode: Optional[str] = None
    source: str = "WEB"


class TextCaptureResponse(BaseModel):
    """Response from text capture endpoint"""
    conversationGuid: str
    transactionGuid: str
    aiResponse: str
    extractedIntent: Optional[str] = None
    extractedProjectCode: Optional[str] = None
    taskCreated: Optional[dict] = None
    processingTimeMs: int
