# app/api/themes.py
"""
Themes CRUD API - Safe for Cloud Run cold starts
NO database operations at import time - all DB calls inside request handlers
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

# Import the execute_query function but DON'T call it at module level
from app.database import execute_query

router = APIRouter(prefix="/api/themes", tags=["themes"])


# Pydantic models - these are safe, no DB calls
class ThemeCreate(BaseModel):
    themeCode: str
    themeName: str
    description: Optional[str] = None
    displayOrder: Optional[int] = 0
    colorCode: Optional[str] = None


class ThemeUpdate(BaseModel):
    themeName: Optional[str] = None
    description: Optional[str] = None
    displayOrder: Optional[int] = None
    colorCode: Optional[str] = None
    isActive: Optional[bool] = None


class ThemeResponse(BaseModel):
    themeId: int
    themeCode: str
    themeName: str
    description: Optional[str]
    displayOrder: int
    colorCode: Optional[str]
    isActive: bool


# ALL database operations are inside async functions - called at REQUEST time, not IMPORT time

@router.get("")
async def list_themes(include_inactive: bool = False):
    """List all themes."""
    try:
        if include_inactive:
            query = """
                SELECT ThemeID as themeId, ThemeCode as themeCode, 
                       ThemeName as themeName, Description as description,
                       DisplayOrder as displayOrder, ColorCode as colorCode,
                       IsActive as isActive
                FROM Themes 
                ORDER BY DisplayOrder
            """
        else:
            query = """
                SELECT ThemeID as themeId, ThemeCode as themeCode, 
                       ThemeName as themeName, Description as description,
                       DisplayOrder as displayOrder, ColorCode as colorCode,
                       IsActive as isActive
                FROM Themes 
                WHERE IsActive = 1 
                ORDER BY DisplayOrder
            """
        
        themes = execute_query(query)
        return {"themes": themes or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{theme_id}")
async def get_theme(theme_id: int):
    """Get single theme by ID."""
    try:
        themes = execute_query(
            """
            SELECT ThemeID as themeId, ThemeCode as themeCode, 
                   ThemeName as themeName, Description as description,
                   DisplayOrder as displayOrder, ColorCode as colorCode,
                   IsActive as isActive
            FROM Themes 
            WHERE ThemeID = ?
            """,
            [theme_id]
        )
        
        if not themes:
            raise HTTPException(status_code=404, detail="Theme not found")
        
        return themes[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_theme(theme: ThemeCreate):
    """Create a new theme."""
    try:
        result = execute_query(
            """
            INSERT INTO Themes (ThemeCode, ThemeName, Description, DisplayOrder, ColorCode)
            OUTPUT INSERTED.ThemeID
            VALUES (?, ?, ?, ?, ?)
            """,
            [theme.themeCode, theme.themeName, theme.description,
             theme.displayOrder, theme.colorCode]
        )
        
        if result:
            return {"themeId": result[0].get('ThemeID'), "message": "Theme created"}
        else:
            return {"message": "Theme created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{theme_id}")
async def update_theme(theme_id: int, theme: ThemeUpdate):
    """Update an existing theme."""
    try:
        updates = []
        params = []
        
        if theme.themeName is not None:
            updates.append("ThemeName = ?")
            params.append(theme.themeName)
        if theme.description is not None:
            updates.append("Description = ?")
            params.append(theme.description)
        if theme.displayOrder is not None:
            updates.append("DisplayOrder = ?")
            params.append(theme.displayOrder)
        if theme.colorCode is not None:
            updates.append("ColorCode = ?")
            params.append(theme.colorCode)
        if theme.isActive is not None:
            updates.append("IsActive = ?")
            params.append(1 if theme.isActive else 0)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updates.append("UpdatedAt = GETUTCDATE()")
        params.append(theme_id)
        
        execute_query(
            f"UPDATE Themes SET {', '.join(updates)} WHERE ThemeID = ?",
            params
        )
        
        return {"message": "Theme updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{theme_id}")
async def delete_theme(theme_id: int, hard_delete: bool = False):
    """Delete a theme (soft delete by default)."""
    try:
        if hard_delete:
            # Check for projects using this theme
            projects = execute_query(
                "SELECT COUNT(*) as cnt FROM Projects WHERE ThemeID = ?",
                [theme_id]
            )
            
            if projects and projects[0].get('cnt', 0) > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete theme with associated projects"
                )
            
            execute_query("DELETE FROM Themes WHERE ThemeID = ?", [theme_id])
        else:
            execute_query(
                "UPDATE Themes SET IsActive = 0, UpdatedAt = GETUTCDATE() WHERE ThemeID = ?",
                [theme_id]
            )
        
        return {"message": "Theme deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
