"""
MetaPM Themes API - Sprint 3 Feature 4
======================================

Full CRUD operations for project themes.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import execute_query

router = APIRouter()


# ============================================
# MODELS
# ============================================

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


# ============================================
# ENDPOINTS
# ============================================

@router.get("")
async def list_themes(include_inactive: bool = Query(default=False)):
    """List all themes."""
    query = """
        SELECT 
            ThemeID as themeId,
            ThemeCode as themeCode,
            ThemeName as themeName,
            Description as description,
            DisplayOrder as displayOrder,
            ColorCode as colorCode,
            IsActive as isActive,
            CreatedAt as createdAt,
            UpdatedAt as updatedAt
        FROM Themes
    """
    
    if not include_inactive:
        query += " WHERE IsActive = 1"
    
    query += " ORDER BY DisplayOrder, ThemeName"
    
    themes = execute_query(query)
    
    # Get project count for each theme
    for theme in themes:
        project_count = execute_query(
            "SELECT COUNT(*) as count FROM Projects WHERE ThemeID = ?",
            (theme['themeId'],),
            fetch="one"
        )
        theme['projectCount'] = project_count['count'] if project_count else 0
    
    return {"themes": themes, "count": len(themes)}


@router.get("/{theme_id}")
async def get_theme(theme_id: int):
    """Get a single theme by ID."""
    query = """
        SELECT 
            ThemeID as themeId,
            ThemeCode as themeCode,
            ThemeName as themeName,
            Description as description,
            DisplayOrder as displayOrder,
            ColorCode as colorCode,
            IsActive as isActive,
            CreatedAt as createdAt,
            UpdatedAt as updatedAt
        FROM Themes
        WHERE ThemeID = ?
    """
    
    theme = execute_query(query, (theme_id,), fetch="one")
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    # Get associated projects
    projects = execute_query("""
        SELECT ProjectCode as projectCode, ProjectName as projectName
        FROM Projects
        WHERE ThemeID = ?
        ORDER BY ProjectCode
    """, (theme_id,))
    
    theme['projects'] = projects
    return theme


@router.post("")
async def create_theme(theme: ThemeCreate):
    """Create a new theme."""
    # Check for duplicate code or name
    existing = execute_query(
        "SELECT ThemeID FROM Themes WHERE ThemeCode = ? OR ThemeName = ?",
        (theme.themeCode, theme.themeName),
        fetch="one"
    )
    if existing:
        raise HTTPException(status_code=400, detail="Theme code or name already exists")
    
    query = """
        INSERT INTO Themes (ThemeCode, ThemeName, Description, DisplayOrder, ColorCode)
        OUTPUT INSERTED.ThemeID, INSERTED.ThemeCode, INSERTED.ThemeName
        VALUES (?, ?, ?, ?, ?)
    """
    
    result = execute_query(
        query,
        (theme.themeCode, theme.themeName, theme.description,
         theme.displayOrder, theme.colorCode),
        fetch="one"
    )
    
    return {"message": "Theme created", "theme": result}


@router.put("/{theme_id}")
async def update_theme(theme_id: int, theme: ThemeUpdate):
    """Update a theme."""
    existing = execute_query(
        "SELECT ThemeID FROM Themes WHERE ThemeID = ?",
        (theme_id,),
        fetch="one"
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    # Build dynamic update
    updates = []
    params = []
    
    field_map = {
        'themeName': 'ThemeName',
        'description': 'Description',
        'displayOrder': 'DisplayOrder',
        'colorCode': 'ColorCode',
        'isActive': 'IsActive'
    }
    
    for py_field, sql_field in field_map.items():
        value = getattr(theme, py_field, None)
        if value is not None:
            updates.append(f"{sql_field} = ?")
            params.append(value)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("UpdatedAt = GETUTCDATE()")
    params.append(theme_id)
    
    query = f"UPDATE Themes SET {', '.join(updates)} WHERE ThemeID = ?"
    execute_query(query, tuple(params), fetch="none")
    
    return {"message": "Theme updated", "themeId": theme_id}


@router.delete("/{theme_id}")
async def delete_theme(theme_id: int, hard_delete: bool = Query(default=False)):
    """Delete a theme (soft delete by default)."""
    existing = execute_query(
        "SELECT ThemeID FROM Themes WHERE ThemeID = ?",
        (theme_id,),
        fetch="one"
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Theme not found")
    
    if hard_delete:
        # Check for projects using this theme
        project_count = execute_query(
            "SELECT COUNT(*) as count FROM Projects WHERE ThemeID = ?",
            (theme_id,),
            fetch="one"
        )
        if project_count and project_count['count'] > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete theme: {project_count['count']} projects are using it"
            )
        
        execute_query("DELETE FROM Themes WHERE ThemeID = ?", (theme_id,), fetch="none")
        return {"message": "Theme permanently deleted", "themeId": theme_id}
    else:
        execute_query(
            "UPDATE Themes SET IsActive = 0, UpdatedAt = GETUTCDATE() WHERE ThemeID = ?",
            (theme_id,),
            fetch="none"
        )
        return {"message": "Theme deactivated", "themeId": theme_id}
