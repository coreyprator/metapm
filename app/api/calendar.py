"""
MetaPM Google Calendar Integration
==================================

Provides read/write access to Google Calendar:
- GET /api/calendar/today - Today's events
- GET /api/calendar/week - This week's events  
- POST /api/calendar/events - Create new event
- POST /api/calendar/from-voice - Claude parses text → creates event

Prerequisites:
- OAuth credentials stored in Secret Manager
- Calendar API enabled in GCP
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, Query
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)
router = APIRouter()

# Token URI for Google OAuth
TOKEN_URI = "https://oauth2.googleapis.com/token"


# ============================================
# MODELS
# ============================================

class CalendarEvent(BaseModel):
    """Calendar event for display"""
    id: Optional[str] = None
    title: str
    start_time: str = Field(..., alias="startTime")
    end_time: Optional[str] = Field(None, alias="endTime")
    location: Optional[str] = None
    description: Optional[str] = None
    all_day: bool = Field(default=False, alias="allDay")
    
    class Config:
        populate_by_name = True


class CreateEventRequest(BaseModel):
    """Request to create a calendar event"""
    title: str
    start_time: datetime = Field(..., alias="startTime")
    end_time: Optional[datetime] = Field(None, alias="endTime")
    location: Optional[str] = None
    description: Optional[str] = None
    all_day: bool = Field(default=False, alias="allDay")
    
    class Config:
        populate_by_name = True


class VoiceToCalendarRequest(BaseModel):
    """Request to parse voice text into calendar event"""
    text: str
    timezone: str = "America/Chicago"


# ============================================
# CALENDAR SERVICE
# ============================================

def get_calendar_credentials() -> Optional[Credentials]:
    """
    Get Google Calendar credentials from environment/secrets.
    
    Required env vars (from Secret Manager):
    - GOOGLE_CALENDAR_REFRESH_TOKEN
    - GOOGLE_OAUTH_CLIENT_ID  
    - GOOGLE_OAUTH_CLIENT_SECRET
    """
    refresh_token = os.getenv("GOOGLE_CALENDAR_REFRESH_TOKEN")
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    
    if not all([refresh_token, client_id, client_secret]):
        logger.warning("Google Calendar credentials not configured")
        return None
    
    # Debug logging
    logger.info(f"Calendar OAuth - Client ID length: {len(client_id) if client_id else 0}, starts with: {client_id[:20] if client_id else 'None'}")
    
    try:
        credentials = Credentials(
            token=None,  # Will be refreshed automatically
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri=TOKEN_URI
        )
        return credentials
    except Exception as e:
        logger.error(f"Failed to create calendar credentials: {e}")
        return None


def get_calendar_service():
    """Get authenticated Google Calendar service."""
    credentials = get_calendar_credentials()
    if not credentials:
        return None
    
    try:
        return build('calendar', 'v3', credentials=credentials)
    except Exception as e:
        logger.error(f"Failed to build calendar service: {e}")
        return None


# ============================================
# ENDPOINTS
# ============================================

@router.get("/status")
async def calendar_status():
    """Check if calendar integration is configured."""
    credentials = get_calendar_credentials()
    if credentials:
        return {
            "configured": True,
            "message": "Google Calendar integration is ready"
        }
    return {
        "configured": False,
        "message": "Google Calendar OAuth not configured. See /docs for setup instructions.",
        "required_secrets": [
            "GOOGLE_CALENDAR_REFRESH_TOKEN",
            "GOOGLE_OAUTH_CLIENT_ID",
            "GOOGLE_OAUTH_CLIENT_SECRET"
        ]
    }


@router.get("/today")
async def get_today_events(timezone: str = Query(default="America/Chicago")):
    """Get today's calendar events."""
    service = get_calendar_service()
    
    if not service:
        # Return placeholder when not configured
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timezone": timezone,
            "events": [],
            "configured": False,
            "message": "Google Calendar not configured"
        }
    
    try:
        # Calculate today's boundaries in UTC
        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_day.isoformat() + 'Z',
            timeMax=end_of_day.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime',
            timeZone=timezone
        ).execute()
    except Exception as e:
        logger.error(f"Calendar API error: {e}")
        # Return graceful error instead of 500
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timezone": timezone,
            "events": [],
            "configured": False,
            "error": "OAuth credentials invalid. Please recreate as Desktop app type.",
            "message": str(e)
        }
    
    try:
        
        events = []
        for e in events_result.get('items', []):
            start = e['start'].get('dateTime', e['start'].get('date'))
            end = e['end'].get('dateTime', e['end'].get('date'))
            all_day = 'date' in e['start']
            
            events.append({
                "id": e['id'],
                "title": e.get('summary', 'No Title'),
                "startTime": start,
                "endTime": end,
                "location": e.get('location'),
                "description": e.get('description'),
                "allDay": all_day
            })
        
        return {
            "date": now.strftime("%Y-%m-%d"),
            "timezone": timezone,
            "events": events,
            "count": len(events),
            "configured": True
        }
        
    except HttpError as e:
        logger.error(f"Calendar API error: {e}")
        raise HTTPException(status_code=502, detail=f"Calendar API error: {e}")


@router.get("/week")
async def get_week_events(timezone: str = Query(default="America/Chicago")):
    """Get this week's calendar events."""
    service = get_calendar_service()
    
    if not service:
        return {
            "startDate": datetime.now().strftime("%Y-%m-%d"),
            "endDate": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "events": [],
            "configured": False,
            "message": "Google Calendar not configured"
        }
    
    try:
        now = datetime.utcnow()
        start_of_week = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=7)
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_week.isoformat() + 'Z',
            timeMax=end_of_week.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime',
            timeZone=timezone,
            maxResults=50
        ).execute()
        
        events = []
        for e in events_result.get('items', []):
            start = e['start'].get('dateTime', e['start'].get('date'))
            end = e['end'].get('dateTime', e['end'].get('date'))
            all_day = 'date' in e['start']
            
            events.append({
                "id": e['id'],
                "title": e.get('summary', 'No Title'),
                "startTime": start,
                "endTime": end,
                "location": e.get('location'),
                "allDay": all_day
            })
        
        return {
            "startDate": start_of_week.strftime("%Y-%m-%d"),
            "endDate": end_of_week.strftime("%Y-%m-%d"),
            "timezone": timezone,
            "events": events,
            "count": len(events),
            "configured": True
        }
        
    except HttpError as e:
        logger.error(f"Calendar API error: {e}")
        raise HTTPException(status_code=502, detail=f"Calendar API error: {e}")


@router.post("/events")
async def create_event(request: CreateEventRequest):
    """Create a new calendar event."""
    service = get_calendar_service()
    
    if not service:
        raise HTTPException(
            status_code=503, 
            detail="Google Calendar not configured. Add OAuth secrets to enable."
        )
    
    try:
        # Build event body
        event = {
            'summary': request.title,
            'location': request.location,
            'description': request.description,
        }
        
        if request.all_day:
            event['start'] = {'date': request.start_time.strftime("%Y-%m-%d")}
            event['end'] = {'date': (request.end_time or request.start_time).strftime("%Y-%m-%d")}
        else:
            event['start'] = {
                'dateTime': request.start_time.isoformat(),
                'timeZone': 'America/Chicago'
            }
            event['end'] = {
                'dateTime': (request.end_time or request.start_time + timedelta(hours=1)).isoformat(),
                'timeZone': 'America/Chicago'
            }
        
        created = service.events().insert(calendarId='primary', body=event).execute()
        
        return {
            "success": True,
            "eventId": created['id'],
            "link": created.get('htmlLink'),
            "title": request.title,
            "startTime": str(request.start_time)
        }
        
    except HttpError as e:
        logger.error(f"Failed to create event: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to create event: {e}")


@router.post("/from-voice")
async def create_event_from_voice(request: VoiceToCalendarRequest):
    """
    Parse natural language text and create a calendar event.
    
    Example: "Add my flight to Buenos Aires on December 15th at 8am"
    
    Uses Claude to extract structured event data.
    """
    import httpx
    import json
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")
    
    # Ask Claude to parse the event
    system_prompt = """You are a calendar assistant. Extract calendar event details from natural language.

Respond with JSON only (no markdown, no explanation):
{
    "title": "Event title",
    "date": "YYYY-MM-DD",
    "start_time": "HH:MM" (24-hour format),
    "end_time": "HH:MM" or null,
    "location": "location" or null,
    "all_day": true/false,
    "confidence": 0.0-1.0
}

If you cannot parse a valid event, respond:
{"error": "reason", "confidence": 0.0}

Today's date is: """ + datetime.now().strftime("%Y-%m-%d")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 500,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": request.text}]
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Claude API error: {response.text}")
            
            result = response.json()
            content = result["content"][0]["text"]
            
            # Parse Claude's response
            # Strip markdown if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            parsed = json.loads(content.strip())
            
            if "error" in parsed:
                return {
                    "success": False,
                    "error": parsed["error"],
                    "originalText": request.text
                }
            
            # Build datetime from parsed data
            event_date = datetime.strptime(parsed["date"], "%Y-%m-%d")
            
            if parsed.get("all_day"):
                start_dt = event_date
                end_dt = event_date
            else:
                start_time = datetime.strptime(parsed["start_time"], "%H:%M")
                start_dt = event_date.replace(hour=start_time.hour, minute=start_time.minute)
                
                if parsed.get("end_time"):
                    end_time = datetime.strptime(parsed["end_time"], "%H:%M")
                    end_dt = event_date.replace(hour=end_time.hour, minute=end_time.minute)
                else:
                    end_dt = start_dt + timedelta(hours=1)
            
            # Create the event
            create_request = CreateEventRequest(
                title=parsed["title"],
                startTime=start_dt,
                endTime=end_dt,
                location=parsed.get("location"),
                allDay=parsed.get("all_day", False)
            )
            
            # Check if calendar is configured
            service = get_calendar_service()
            if not service:
                return {
                    "success": False,
                    "parsed": parsed,
                    "error": "Google Calendar not configured - event parsed but not created",
                    "originalText": request.text
                }
            
            # Create the event
            event_result = await create_event(create_request)
            
            return {
                "success": True,
                "parsed": parsed,
                "event": event_result,
                "originalText": request.text
            }
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response: {e}")
        return {
            "success": False,
            "error": f"Failed to parse event details: {e}",
            "originalText": request.text
        }
    except Exception as e:
        logger.error(f"Error in from-voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendars")
async def list_calendars():
    """List all accessible calendars."""
    service = get_calendar_service()
    
    if not service:
        raise HTTPException(status_code=503, detail="Google Calendar not configured")
    
    try:
        calendars = service.calendarList().list().execute()
        return {
            "calendars": [
                {
                    "id": cal['id'],
                    "name": cal['summary'],
                    "primary": cal.get('primary', False),
                    "accessRole": cal.get('accessRole')
                }
                for cal in calendars.get('items', [])
            ]
        }
    except HttpError as e:
        raise HTTPException(status_code=502, detail=f"Calendar API error: {e}")
