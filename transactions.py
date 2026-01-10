"""
MetaPM Transactions API
History, search, and analytics for AI conversations
"""

from typing import Optional
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query

from app.models.transaction import (
    ConversationCreate, ConversationResponse,
    TransactionResponse, SearchRequest, SearchResponse, SearchResult,
    CostSummary, UsagePattern
)
from app.core.database import execute_query, execute_procedure

router = APIRouter()


# ============================================
# CONVERSATIONS
# ============================================

@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(conversation: ConversationCreate):
    """Start a new conversation"""
    result = execute_procedure("sp_StartConversation", {
        "Source": conversation.source,
        "ProjectCode": conversation.project_code,
        "Title": conversation.title,
        "DeviceInfo": conversation.device_info,
        "Location": conversation.location
    })
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create conversation")
    
    return await get_conversation(result[0]["ConversationGUID"])


@router.get("/conversations/{conversation_guid}", response_model=ConversationResponse)
async def get_conversation(conversation_guid: UUID):
    """Get conversation details"""
    query = """
        SELECT 
            c.ConversationID as conversationId,
            c.ConversationGUID as conversationGuid,
            c.Title as title,
            c.Source as source,
            p.ProjectCode as projectCode,
            p.ProjectName as projectName,
            c.Status as status,
            c.CreatedAt as createdAt,
            c.UpdatedAt as updatedAt,
            (SELECT COUNT(*) FROM Transactions t WHERE t.ConversationID = c.ConversationID) as transactionCount
        FROM Conversations c
        LEFT JOIN Projects p ON c.ProjectID = p.ProjectID
        WHERE c.ConversationGUID = ?
    """
    
    row = execute_query(query, (str(conversation_guid),), fetch="one")
    
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return ConversationResponse(**row)


@router.get("/conversations")
async def list_conversations(
    project_code: Optional[str] = Query(None, alias="projectCode"),
    source: Optional[str] = Query(None),
    status: Optional[str] = Query(default="ACTIVE"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100)
):
    """List conversations with filters"""
    conditions = ["1=1"]
    params = []
    
    if project_code:
        conditions.append("p.ProjectCode = ?")
        params.append(project_code)
    
    if source:
        conditions.append("c.Source = ?")
        params.append(source)
    
    if status:
        conditions.append("c.Status = ?")
        params.append(status)
    
    where_clause = " AND ".join(conditions)
    offset = (page - 1) * page_size
    
    query = f"""
        SELECT 
            c.ConversationID as conversationId,
            c.ConversationGUID as conversationGuid,
            c.Title as title,
            c.Source as source,
            p.ProjectCode as projectCode,
            c.Status as status,
            c.CreatedAt as createdAt,
            c.UpdatedAt as updatedAt,
            (SELECT COUNT(*) FROM Transactions t WHERE t.ConversationID = c.ConversationID) as transactionCount
        FROM Conversations c
        LEFT JOIN Projects p ON c.ProjectID = p.ProjectID
        WHERE {where_clause}
        ORDER BY c.UpdatedAt DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    
    params.extend([offset, page_size])
    rows = execute_query(query, tuple(params), fetch="all") or []
    
    # Count total
    count_query = f"""
        SELECT COUNT(*) as total
        FROM Conversations c
        LEFT JOIN Projects p ON c.ProjectID = p.ProjectID
        WHERE {where_clause}
    """
    count_result = execute_query(count_query, tuple(params[:-2]) if params[:-2] else None, fetch="one")
    total = count_result["total"] if count_result else 0
    
    return {
        "conversations": rows,
        "total": total,
        "page": page,
        "pageSize": page_size
    }


@router.get("/conversations/{conversation_guid}/full")
async def get_conversation_full(conversation_guid: UUID):
    """Get conversation with all transactions and media"""
    # This returns multiple result sets, so we need custom handling
    
    # Get conversation
    conv_query = """
        SELECT 
            c.ConversationID as conversationId,
            c.ConversationGUID as conversationGuid,
            c.Title as title,
            c.Source as source,
            c.Status as status,
            c.CreatedAt as createdAt,
            c.UpdatedAt as updatedAt,
            p.ProjectCode as projectCode,
            p.ProjectName as projectName
        FROM Conversations c
        LEFT JOIN Projects p ON c.ProjectID = p.ProjectID
        WHERE c.ConversationGUID = ?
    """
    conversation = execute_query(conv_query, (str(conversation_guid),), fetch="one")
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get transactions
    trans_query = """
        SELECT 
            t.TransactionID as transactionId,
            t.TransactionGUID as transactionGuid,
            t.PromptText as promptText,
            t.PromptType as promptType,
            t.ResponseText as responseText,
            t.ResponseModel as responseModel,
            t.AIProvider as aiProvider,
            t.ExtractedIntent as extractedIntent,
            t.ExtractedProjectCode as extractedProjectCode,
            t.CostUSD as costUsd,
            t.AudioDurationSeconds as audioDurationSeconds,
            t.CreatedAt as createdAt
        FROM Transactions t
        JOIN Conversations c ON t.ConversationID = c.ConversationID
        WHERE c.ConversationGUID = ?
        ORDER BY t.CreatedAt
    """
    transactions = execute_query(trans_query, (str(conversation_guid),), fetch="all") or []
    
    # Get media for all transactions
    media_query = """
        SELECT 
            m.MediaID as mediaId,
            m.MediaGUID as mediaGuid,
            m.FileName as fileName,
            m.FileType as fileType,
            m.GCSUrl as gcsUrl,
            m.TranscriptionText as transcriptionText,
            m.ImageDescription as imageDescription,
            tm.TransactionID as transactionId,
            tm.MediaRole as mediaRole
        FROM MediaFiles m
        JOIN TransactionMedia tm ON m.MediaID = tm.MediaID
        JOIN Transactions t ON tm.TransactionID = t.TransactionID
        JOIN Conversations c ON t.ConversationID = c.ConversationID
        WHERE c.ConversationGUID = ?
        ORDER BY t.CreatedAt, tm.DisplayOrder
    """
    media = execute_query(media_query, (str(conversation_guid),), fetch="all") or []
    
    # Group media by transaction
    media_by_transaction = {}
    for m in media:
        tid = m["transactionId"]
        if tid not in media_by_transaction:
            media_by_transaction[tid] = []
        media_by_transaction[tid].append(m)
    
    # Attach media to transactions
    for t in transactions:
        t["media"] = media_by_transaction.get(t["transactionId"], [])
    
    return {
        "conversation": conversation,
        "transactions": transactions
    }


# ============================================
# SEARCH
# ============================================

@router.post("/search", response_model=SearchResponse)
async def search_content(request: SearchRequest):
    """
    Full-text search across all content:
    - Transaction prompts and responses
    - Audio transcriptions
    - Image OCR and descriptions
    """
    query = """
        SELECT TOP (?)
            ContentType as contentType,
            ContentID as contentId,
            ContentGUID as contentGuid,
            Context as context,
            LEFT(PrimaryText, 500) as primaryText,
            LEFT(SecondaryText, 500) as secondaryText,
            CreatedAt as createdAt,
            ProjectCode as projectCode
        FROM vw_SearchableContent
        WHERE 
            (PrimaryText LIKE '%' + ? + '%' OR SecondaryText LIKE '%' + ? + '%')
            AND (? IS NULL OR ProjectCode = ?)
            AND (? IS NULL OR ContentType = ?)
            AND (? IS NULL OR CreatedAt >= ?)
            AND (? IS NULL OR CreatedAt <= ?)
        ORDER BY CreatedAt DESC
    """
    
    params = (
        request.max_results,
        request.query, request.query,
        request.project_code, request.project_code,
        request.content_type, request.content_type,
        request.start_date, request.start_date,
        request.end_date, request.end_date
    )
    
    rows = execute_query(query, params, fetch="all") or []
    
    results = [SearchResult(**row) for row in rows]
    
    return SearchResponse(
        results=results,
        total=len(results),
        query=request.query
    )


@router.get("/search/quick")
async def quick_search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(default=20, ge=1, le=100)
):
    """Quick search endpoint for autocomplete/typeahead"""
    query = """
        SELECT TOP (?)
            ContentType as contentType,
            ContentID as contentId,
            Context as context,
            LEFT(PrimaryText, 200) as primaryText,
            CreatedAt as createdAt
        FROM vw_SearchableContent
        WHERE PrimaryText LIKE '%' + ? + '%'
        ORDER BY CreatedAt DESC
    """
    
    rows = execute_query(query, (limit, q), fetch="all") or []
    
    return {"results": rows, "query": q}


# ============================================
# ANALYTICS
# ============================================

@router.get("/analytics/costs")
async def get_cost_analysis(
    days_back: int = Query(default=30, alias="daysBack", ge=1, le=365),
    project_code: Optional[str] = Query(None, alias="projectCode")
):
    """Get cost analysis by project and model"""
    query = """
        SELECT 
            COALESCE(p.ProjectCode, 'UNASSIGNED') AS projectCode,
            t.AIProvider as aiProvider,
            t.ResponseModel as responseModel,
            COUNT(*) AS transactionCount,
            SUM(t.CostUSD) AS totalCostUsd,
            SUM(t.PromptTokens) AS totalPromptTokens,
            SUM(t.ResponseTokens) AS totalResponseTokens,
            SUM(t.AudioDurationSeconds) AS totalAudioSeconds
        FROM Transactions t
        JOIN Conversations c ON t.ConversationID = c.ConversationID
        LEFT JOIN Projects p ON c.ProjectID = p.ProjectID
        WHERE t.CreatedAt >= DATEADD(DAY, -?, GETUTCDATE())
            AND (? IS NULL OR p.ProjectCode = ?)
        GROUP BY p.ProjectCode, t.AIProvider, t.ResponseModel
        ORDER BY totalCostUsd DESC
    """
    
    rows = execute_query(query, (days_back, project_code, project_code), fetch="all") or []
    
    total_cost = sum(r["totalCostUsd"] or 0 for r in rows)
    total_transactions = sum(r["transactionCount"] for r in rows)
    
    return {
        "breakdown": rows,
        "totalCostUsd": total_cost,
        "totalTransactions": total_transactions,
        "daysBack": days_back
    }


@router.get("/analytics/usage")
async def get_usage_patterns(
    days_back: int = Query(default=30, alias="daysBack", ge=1, le=365),
    project_code: Optional[str] = Query(None, alias="projectCode")
):
    """Get usage patterns for analysis"""
    
    # Intent distribution
    intent_query = """
        SELECT 
            ExtractedIntent as intent,
            COUNT(*) AS count
        FROM Transactions t
        JOIN Conversations c ON t.ConversationID = c.ConversationID
        LEFT JOIN Projects p ON c.ProjectID = p.ProjectID
        WHERE t.CreatedAt >= DATEADD(DAY, -?, GETUTCDATE())
            AND (? IS NULL OR p.ProjectCode = ?)
            AND t.ExtractedIntent IS NOT NULL
        GROUP BY ExtractedIntent
        ORDER BY count DESC
    """
    intents = execute_query(intent_query, (days_back, project_code, project_code), fetch="all") or []
    
    # Source distribution
    source_query = """
        SELECT 
            c.Source as source,
            COUNT(*) AS count
        FROM Conversations c
        LEFT JOIN Projects p ON c.ProjectID = p.ProjectID
        WHERE c.CreatedAt >= DATEADD(DAY, -?, GETUTCDATE())
            AND (? IS NULL OR p.ProjectCode = ?)
        GROUP BY c.Source
        ORDER BY count DESC
    """
    sources = execute_query(source_query, (days_back, project_code, project_code), fetch="all") or []
    
    # Daily volume
    daily_query = """
        SELECT 
            CAST(t.CreatedAt AS DATE) AS date,
            COUNT(*) AS count,
            SUM(t.CostUSD) AS costUsd
        FROM Transactions t
        WHERE t.CreatedAt >= DATEADD(DAY, -?, GETUTCDATE())
        GROUP BY CAST(t.CreatedAt AS DATE)
        ORDER BY date
    """
    daily = execute_query(daily_query, (days_back,), fetch="all") or []
    
    return {
        "intentDistribution": intents,
        "sourceDistribution": sources,
        "dailyVolume": daily,
        "daysBack": days_back
    }


@router.get("/analytics/projects")
async def get_project_activity(
    days_back: int = Query(default=30, alias="daysBack", ge=1, le=365)
):
    """Get activity summary by project"""
    query = """
        SELECT 
            p.ProjectCode as projectCode,
            p.ProjectName as projectName,
            COUNT(DISTINCT c.ConversationID) as conversationCount,
            COUNT(t.TransactionID) as transactionCount,
            SUM(t.CostUSD) as totalCostUsd,
            MAX(t.CreatedAt) as lastActivity
        FROM Projects p
        LEFT JOIN Conversations c ON p.ProjectID = c.ProjectID 
            AND c.CreatedAt >= DATEADD(DAY, -?, GETUTCDATE())
        LEFT JOIN Transactions t ON c.ConversationID = t.ConversationID
        GROUP BY p.ProjectCode, p.ProjectName
        ORDER BY transactionCount DESC
    """
    
    rows = execute_query(query, (days_back,), fetch="all") or []
    
    return {
        "projects": rows,
        "daysBack": days_back
    }
