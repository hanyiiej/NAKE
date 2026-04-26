from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    icon: str = "folder"
    display_order: int = 0

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ArticleBase(BaseModel):
    title: str
    slug: str
    summary: Optional[str] = None
    content: str
    category_id: int
    status: str = "published"

class ArticleCreate(ArticleBase):
    pass

class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    category_id: Optional[int] = None
    status: Optional[str] = None

class ArticleResponse(ArticleBase):
    id: int
    view_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str

class MessageResponse(BaseModel):
    message: str
    success: bool = True
