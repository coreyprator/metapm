"""
MetaPM Categories API
Category management for task classification
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.database import execute_query

router = APIRouter()


class CategoryResponse(BaseModel):
    """Category response model"""
    category_id: int = Field(..., alias="categoryId")
    category_code: str = Field(..., alias="categoryCode")
    category_name: str = Field(..., alias="categoryName")
    category_type: str = Field(..., alias="categoryType")
    description: Optional[str] = None
    sort_order: int = Field(..., alias="sortOrder")
    is_active: bool = Field(..., alias="isActive")
    task_count: int = Field(default=0, alias="taskCount")
    
    class Config:
        populate_by_name = True


class CategoryCreate(BaseModel):
    """Create a new category"""
    category_code: str = Field(..., alias="categoryCode", max_length=20)
    category_name: str = Field(..., alias="categoryName", max_length=100)
    category_type: str = Field(..., alias="categoryType", pattern="^(TASK_TYPE|DOMAIN)$")
    description: Optional[str] = Field(None, max_length=500)
    sort_order: int = Field(default=0, alias="sortOrder")
    
    class Config:
        populate_by_name = True


class CategoryUpdate(BaseModel):
    """Update a category"""
    category_name: Optional[str] = Field(None, alias="categoryName", max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    sort_order: Optional[int] = Field(None, alias="sortOrder")
    is_active: Optional[bool] = Field(None, alias="isActive")
    
    class Config:
        populate_by_name = True


@router.get("")
async def list_categories(
    category_type: Optional[str] = Query(None, alias="type", pattern="^(TASK_TYPE|DOMAIN)$"),
    active_only: bool = Query(True, alias="activeOnly"),
):
    """List all categories with optional type filter"""
    conditions = []
    params = []
    
    if category_type:
        conditions.append("c.CategoryType = ?")
        params.append(category_type)
    
    if active_only:
        conditions.append("c.IsActive = 1")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    query = f"""
        SELECT 
            c.CategoryID as categoryId,
            c.CategoryCode as categoryCode,
            c.CategoryName as categoryName,
            c.CategoryType as categoryType,
            c.Description as description,
            c.SortOrder as sortOrder,
            c.IsActive as isActive,
            (SELECT COUNT(*) FROM TaskCategoryLinks tcl WHERE tcl.CategoryID = c.CategoryID) as taskCount
        FROM Categories c
        WHERE {where_clause}
        ORDER BY c.CategoryType, c.SortOrder, c.CategoryName
    """
    
    rows = execute_query(query, tuple(params) if params else None, fetch="all") or []
    
    # Group by type for easier consumption
    task_types = [CategoryResponse(**r) for r in rows if r["categoryType"] == "TASK_TYPE"]
    domains = [CategoryResponse(**r) for r in rows if r["categoryType"] == "DOMAIN"]
    
    return {
        "task_types": task_types,
        "domains": domains,
        "total": len(rows)
    }


@router.get("/{category_code}", response_model=CategoryResponse)
async def get_category(category_code: str):
    """Get a single category"""
    query = """
        SELECT 
            c.CategoryID as categoryId,
            c.CategoryCode as categoryCode,
            c.CategoryName as categoryName,
            c.CategoryType as categoryType,
            c.Description as description,
            c.SortOrder as sortOrder,
            c.IsActive as isActive,
            (SELECT COUNT(*) FROM TaskCategoryLinks tcl WHERE tcl.CategoryID = c.CategoryID) as taskCount
        FROM Categories c
        WHERE c.CategoryCode = ?
    """
    
    row = execute_query(query, (category_code,), fetch="one")
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Category {category_code} not found")
    
    return CategoryResponse(**row)


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(category: CategoryCreate):
    """Create a new category"""
    # Check for duplicate
    existing = execute_query(
        "SELECT CategoryID FROM Categories WHERE CategoryCode = ?",
        (category.category_code,),
        fetch="one"
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Category code {category.category_code} already exists")
    
    query = """
        INSERT INTO Categories (CategoryCode, CategoryName, CategoryType, Description, SortOrder)
        OUTPUT INSERTED.CategoryID
        VALUES (?, ?, ?, ?, ?)
    """
    
    result = execute_query(query, (
        category.category_code,
        category.category_name,
        category.category_type,
        category.description,
        category.sort_order
    ), fetch="one")
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create category")
    
    return await get_category(category.category_code)


@router.put("/{category_code}", response_model=CategoryResponse)
async def update_category(category_code: str, category: CategoryUpdate):
    """Update a category"""
    existing = execute_query(
        "SELECT CategoryID FROM Categories WHERE CategoryCode = ?",
        (category_code,),
        fetch="one"
    )
    if not existing:
        raise HTTPException(status_code=404, detail=f"Category {category_code} not found")
    
    updates = []
    params = []
    
    if category.category_name is not None:
        updates.append("CategoryName = ?")
        params.append(category.category_name)
    if category.description is not None:
        updates.append("Description = ?")
        params.append(category.description)
    if category.sort_order is not None:
        updates.append("SortOrder = ?")
        params.append(category.sort_order)
    if category.is_active is not None:
        updates.append("IsActive = ?")
        params.append(1 if category.is_active else 0)
    
    if updates:
        updates.append("UpdatedAt = GETUTCDATE()")
        params.append(category_code)
        
        query = f"UPDATE Categories SET {', '.join(updates)} WHERE CategoryCode = ?"
        execute_query(query, tuple(params), fetch="none")
    
    return await get_category(category_code)


@router.delete("/{category_code}", status_code=204)
async def delete_category(category_code: str):
    """
    Soft delete a category (set IsActive = 0).
    Hard delete not allowed if tasks are linked.
    """
    existing = execute_query(
        "SELECT CategoryID FROM Categories WHERE CategoryCode = ?",
        (category_code,),
        fetch="one"
    )
    if not existing:
        raise HTTPException(status_code=404, detail=f"Category {category_code} not found")
    
    # Check for linked tasks
    linked = execute_query(
        "SELECT COUNT(*) as cnt FROM TaskCategoryLinks WHERE CategoryID = ?",
        (existing["CategoryID"],),
        fetch="one"
    )
    
    if linked and linked["cnt"] > 0:
        # Soft delete
        execute_query(
            "UPDATE Categories SET IsActive = 0, UpdatedAt = GETUTCDATE() WHERE CategoryCode = ?",
            (category_code,),
            fetch="none"
        )
    else:
        # Hard delete if no links
        execute_query(
            "DELETE FROM Categories WHERE CategoryCode = ?",
            (category_code,),
            fetch="none"
        )
    
    return None
