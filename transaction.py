"""
MetaPM Transaction Models
Models for AI conversation history and media attachments
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field
from decimal import Decimal


# ============================================
# CONVERSATION MODELS
# ============================================

class ConversationCreate(BaseModel):
    """Start a new conversation"""
    source: str = Field(..., pattern="^(VOICE|WEB|API|MOBILE|VSCODE)$")
    project_code: Optional[str] = Field(None, alias="projectCode")
    title: Optional[str] = None
    device_info: Optional[str] = Field(None, alias="deviceInfo")
    location: Optional[str] = None
    tags: Optional[str] = None
    
    class Config:
        populate_by_name = True


class ConversationResponse(BaseModel):
    """Conversation details"""
    conversation_id: int = Field(..., alias="conversationId")
    conversation_guid: UUID = Field(..., alias="conversationGuid")
    title: Optional[str] = None
    source: str
    project_code: Optional[str] = Field(None, alias="projectCode")
    project_name: Optional[str] = Field(None, alias="projectName")
    status: str
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    transaction_count: int = Field(default=0, alias="transactionCount")
    
    class Config:
        populate_by_name = True
        from_attributes = True


# ============================================
# TRANSACTION MODELS
# ============================================

class TransactionCreate(BaseModel):
    """Record a prompt/response transaction"""
    conversation_guid: UUID = Field(..., alias="conversationGuid")
    prompt_text: str = Field(..., alias="promptText")
    prompt_type: str = Field(default="TEXT", alias="promptType", pattern="^(TEXT|VOICE|IMAGE|DOCUMENT)$")
    response_text: Optional[str] = Field(None, alias="responseText")
    response_model: Optional[str] = Field(None, alias="responseModel")
    ai_provider: Optional[str] = Field(None, alias="aiProvider", pattern="^(ANTHROPIC|OPENAI|GOOGLE)$")
    prompt_tokens: Optional[int] = Field(None, alias="promptTokens")
    response_tokens: Optional[int] = Field(None, alias="responseTokens")
    processing_time_ms: Optional[int] = Field(None, alias="processingTimeMs")
    cost_usd: Optional[Decimal] = Field(None, alias="costUsd")
    audio_duration_seconds: Optional[Decimal] = Field(None, alias="audioDurationSeconds")
    transcription_confidence: Optional[Decimal] = Field(None, alias="transcriptionConfidence")
    extracted_intent: Optional[str] = Field(None, alias="extractedIntent")
    extracted_project_code: Optional[str] = Field(None, alias="extractedProjectCode")
    extracted_categories: Optional[str] = Field(None, alias="extractedCategories")
    
    class Config:
        populate_by_name = True


class TransactionResponse(BaseModel):
    """Full transaction details"""
    transaction_id: int = Field(..., alias="transactionId")
    transaction_guid: UUID = Field(..., alias="transactionGuid")
    conversation_id: int = Field(..., alias="conversationId")
    prompt_text: Optional[str] = Field(None, alias="promptText")
    prompt_type: str = Field(..., alias="promptType")
    response_text: Optional[str] = Field(None, alias="responseText")
    response_model: Optional[str] = Field(None, alias="responseModel")
    ai_provider: Optional[str] = Field(None, alias="aiProvider")
    extracted_intent: Optional[str] = Field(None, alias="extractedIntent")
    extracted_project_code: Optional[str] = Field(None, alias="extractedProjectCode")
    cost_usd: Optional[Decimal] = Field(None, alias="costUsd")
    audio_duration_seconds: Optional[Decimal] = Field(None, alias="audioDurationSeconds")
    created_at: datetime = Field(..., alias="createdAt")
    media: List["MediaSummary"] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True
        from_attributes = True


# ============================================
# MEDIA MODELS
# ============================================

class MediaUploadResponse(BaseModel):
    """Response after uploading media"""
    media_id: int = Field(..., alias="mediaId")
    media_guid: UUID = Field(..., alias="mediaGuid")
    file_name: str = Field(..., alias="fileName")
    file_type: str = Field(..., alias="fileType")
    mime_type: str = Field(..., alias="mimeType")
    gcs_url: Optional[str] = Field(None, alias="gcsUrl")
    processing_status: str = Field(..., alias="processingStatus")
    
    class Config:
        populate_by_name = True


class MediaSummary(BaseModel):
    """Minimal media info for embedding in transactions"""
    media_id: int = Field(..., alias="mediaId")
    media_guid: UUID = Field(..., alias="mediaGuid")
    file_name: str = Field(..., alias="fileName")
    file_type: str = Field(..., alias="fileType")
    media_role: str = Field(..., alias="mediaRole")  # INPUT or OUTPUT
    transcription_text: Optional[str] = Field(None, alias="transcriptionText")
    image_description: Optional[str] = Field(None, alias="imageDescription")
    
    class Config:
        populate_by_name = True


class MediaDetailResponse(BaseModel):
    """Full media details"""
    media_id: int = Field(..., alias="mediaId")
    media_guid: UUID = Field(..., alias="mediaGuid")
    file_name: str = Field(..., alias="fileName")
    file_type: str = Field(..., alias="fileType")
    mime_type: str = Field(..., alias="mimeType")
    file_size_bytes: Optional[int] = Field(None, alias="fileSizeBytes")
    gcs_bucket: str = Field(..., alias="gcsBucket")
    gcs_path: str = Field(..., alias="gcsPath")
    gcs_url: Optional[str] = Field(None, alias="gcsUrl")
    processing_status: str = Field(..., alias="processingStatus")
    audio_duration_seconds: Optional[Decimal] = Field(None, alias="audioDurationSeconds")
    transcription_text: Optional[str] = Field(None, alias="transcriptionText")
    image_width: Optional[int] = Field(None, alias="imageWidth")
    image_height: Optional[int] = Field(None, alias="imageHeight")
    ocr_text: Optional[str] = Field(None, alias="ocrText")
    image_description: Optional[str] = Field(None, alias="imageDescription")
    created_at: datetime = Field(..., alias="createdAt")
    
    class Config:
        populate_by_name = True
        from_attributes = True


# ============================================
# VOICE CAPTURE MODELS
# ============================================

class VoiceCaptureRequest(BaseModel):
    """Request to process voice input"""
    conversation_guid: Optional[UUID] = Field(None, alias="conversationGuid")  # None = start new
    project_code: Optional[str] = Field(None, alias="projectCode")
    source: str = Field(default="MOBILE")
    
    class Config:
        populate_by_name = True


class VoiceCaptureResponse(BaseModel):
    """Response after processing voice input"""
    conversation_guid: UUID = Field(..., alias="conversationGuid")
    transaction_guid: UUID = Field(..., alias="transactionGuid")
    transcription: str
    transcription_confidence: Decimal = Field(..., alias="transcriptionConfidence")
    ai_response: str = Field(..., alias="aiResponse")
    extracted_intent: Optional[str] = Field(None, alias="extractedIntent")
    extracted_project_code: Optional[str] = Field(None, alias="extractedProjectCode")
    task_created: Optional["TaskSummaryBrief"] = Field(None, alias="taskCreated")
    processing_time_ms: int = Field(..., alias="processingTimeMs")
    
    class Config:
        populate_by_name = True


class TaskSummaryBrief(BaseModel):
    """Minimal task info for voice capture response"""
    task_id: int = Field(..., alias="taskId")
    title: str
    project_code: Optional[str] = Field(None, alias="projectCode")
    
    class Config:
        populate_by_name = True


# ============================================
# SEARCH MODELS
# ============================================

class SearchRequest(BaseModel):
    """Search across all content"""
    query: str = Field(..., min_length=2)
    project_code: Optional[str] = Field(None, alias="projectCode")
    content_type: Optional[str] = Field(None, alias="contentType", pattern="^(TRANSACTION|MEDIA)$")
    start_date: Optional[datetime] = Field(None, alias="startDate")
    end_date: Optional[datetime] = Field(None, alias="endDate")
    max_results: int = Field(default=50, alias="maxResults", ge=1, le=200)
    
    class Config:
        populate_by_name = True


class SearchResult(BaseModel):
    """Single search result"""
    content_type: str = Field(..., alias="contentType")
    content_id: int = Field(..., alias="contentId")
    content_guid: UUID = Field(..., alias="contentGuid")
    context: Optional[str] = None
    primary_text: Optional[str] = Field(None, alias="primaryText")
    secondary_text: Optional[str] = Field(None, alias="secondaryText")
    project_code: Optional[str] = Field(None, alias="projectCode")
    created_at: datetime = Field(..., alias="createdAt")
    
    class Config:
        populate_by_name = True


class SearchResponse(BaseModel):
    """Search results"""
    results: List[SearchResult]
    total: int
    query: str


# ============================================
# ANALYTICS MODELS
# ============================================

class CostSummary(BaseModel):
    """Cost analysis by project/model"""
    project_code: str = Field(..., alias="projectCode")
    ai_provider: Optional[str] = Field(None, alias="aiProvider")
    response_model: Optional[str] = Field(None, alias="responseModel")
    transaction_count: int = Field(..., alias="transactionCount")
    total_cost_usd: Decimal = Field(..., alias="totalCostUsd")
    total_prompt_tokens: int = Field(..., alias="totalPromptTokens")
    total_response_tokens: int = Field(..., alias="totalResponseTokens")
    total_audio_seconds: Optional[Decimal] = Field(None, alias="totalAudioSeconds")
    
    class Config:
        populate_by_name = True


class UsagePattern(BaseModel):
    """Usage pattern analysis"""
    intent_distribution: List[dict] = Field(..., alias="intentDistribution")
    source_distribution: List[dict] = Field(..., alias="sourceDistribution")
    daily_volume: List[dict] = Field(..., alias="dailyVolume")
    
    class Config:
        populate_by_name = True


# Update forward references
TransactionResponse.model_rebuild()
VoiceCaptureResponse.model_rebuild()
