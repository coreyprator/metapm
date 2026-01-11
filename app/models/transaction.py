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


class ConversationCreate(BaseModel):
    """Create a new conversation"""
    source: str
    project_code: Optional[str] = None
    title: Optional[str] = None
    device_info: Optional[str] = None
    location: Optional[str] = None


class ConversationResponse(BaseModel):
    """Conversation details response"""
    conversationId: int
    conversationGuid: str
    title: Optional[str] = None
    source: str
    projectCode: Optional[str] = None
    projectName: Optional[str] = None
    status: str
    createdAt: datetime
    updatedAt: datetime
    transactionCount: int


class TransactionResponse(BaseModel):
    """Transaction details response"""
    transactionId: int
    transactionGuid: str
    conversationGuid: str
    prompt: str
    response: str
    transcription: Optional[str] = None
    processingTimeMs: int
    createdAt: datetime


class SearchResult(BaseModel):
    """Single search result"""
    conversationGuid: str
    source: str
    transcription: Optional[str] = None
    prompt: str
    response: str
    createdAt: datetime


class SearchRequest(BaseModel):
    """Search request"""
    query: str
    project_code: Optional[str] = None
    limit: int = 20


class SearchResponse(BaseModel):
    """Search results response"""
    query: str
    resultCount: int
    results: List[SearchResult]


class CostSummary(BaseModel):
    """Cost summary by project/model"""
    projectCode: str
    totalCost: float
    gpt4Cost: float
    gpt35Cost: float
    claudeCost: float
    transactionCount: int


class UsagePattern(BaseModel):
    """Usage pattern analysis"""
    intentType: str
    count: int
    percentage: float
