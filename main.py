from fastapi import FastAPI, Request, Depends, HTTPException, Form, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
import os

# 加载 .env 文件（本地开发用）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 生产环境直接用系统环境变量，无需 dotenv

class PreviewRequest(BaseModel):
    content: str
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import Optional
import math

from database import get_db, init_db, Category, Article, Admin
from schemas import ArticleCreate, ArticleUpdate, LoginRequest
from auth import hash_password, verify_password, create_session, verify_session, get_session_admin, delete_session
from markdown_utils import render_markdown, slugify

app = FastAPI(title="NAKE - New Ample Knowledage Eye", description="A personal blog with markdown support")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
templates = Jinja2Templates(directory="templates")

def get_current_admin(request: Request):
    token = request.cookies.get("session_token")
    if not token or not verify_session(token):
        return None
    admin_id = get_session_admin(token)
    db = next(get_db())
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    db.close()
    return admin

@app.on_event("startup")
def startup():
    init_db()
    db = next(get_db())
    admin = db.query(Admin).first()
    if not admin:
        default_user = os.getenv("ADMIN_USERNAME", "admin")
        default_pass = os.getenv("ADMIN_PASSWORD", "admin123")
        admin = Admin(username=default_user, password_hash=hash_password(default_pass))
        db.add(admin)
        db.commit()
    categories = db.query(Category).all()
    if not categories:
        default_categories = [
            Category(name="Tools & Resources", slug="tools-resources", description="Useful tools, resources and guides", icon="wrench", display_order=1),
            Category(name="Inspirational", slug="inspirational", description="Stories and quotes to inspire", icon="fire", display_order=2),
            Category(name="Aesthetics", slug="aesthetics", description="Art, design and visual appreciation", icon="star", display_order=3),
        ]
        for cat in default_categories:
            db.add(cat)
        db.commit()
    db.close()

# ===================== PUBLIC ROUTES =====================

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    categories = db.query(Category).order_by(Category.display_order).all()
    latest_articles = db.query(Article).filter(Article.status == "published").order_by(desc(Article.created_at)).limit(6).all()
    return templates.TemplateResponse("index.html", {"request": request, "categories": categories, "latest_articles": latest_articles})

@app.get("/category/{slug}", response_class=HTMLResponse)
def category_page(slug: str, request: Request, page: int = 1, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    per_page = 5
    total = db.query(Article).filter(Article.category_id == category.id, Article.status == "published").count()
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    offset = (page - 1) * per_page
    articles = db.query(Article).filter(Article.category_id == category.id, Article.status == "published").order_by(desc(Article.created_at)).offset(offset).limit(per_page).all()
    
    return templates.TemplateResponse("category.html", {
        "request": request,
        "category": category,
        "articles": articles,
        "page": page,
        "total_pages": total_pages,
        "per_page": per_page
    })

@app.get("/article/{slug}", response_class=HTMLResponse)
def article_page(slug: str, request: Request, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.slug == slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    article.view_count += 1
    db.commit()
    
    category = db.query(Category).filter(Category.id == article.category_id).first()
    html_content = render_markdown(article.content)
    
    return templates.TemplateResponse("article.html", {
        "request": request,
        "article": article,
        "category": category,
        "html_content": html_content
    })

# ===================== ADMIN ROUTES =====================

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    admin = get_current_admin(request)
    if admin:
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
async def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin or not verify_password(password, admin.password_hash):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    
    token = create_session(admin.id)
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(key="session_token", value=token, httponly=True, max_age=86400, samesite="lax")
    return response

@app.get("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        delete_session(token)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_token")
    return response

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/login", status_code=303)
    
    categories = db.query(Category).order_by(Category.display_order).all()
    articles = db.query(Article).order_by(desc(Article.created_at)).limit(50).all()
    total_views = sum(a.view_count for a in articles)
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "admin": admin,
        "categories": categories,
        "articles": articles,
        "total_views": total_views
    })

@app.get("/admin/editor", response_class=HTMLResponse)
def new_article(request: Request, db: Session = Depends(get_db)):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/login", status_code=303)
    
    categories = db.query(Category).order_by(Category.display_order).all()
    return templates.TemplateResponse("editor.html", {"request": request, "admin": admin, "categories": categories, "article": None})

@app.get("/admin/editor/{article_id}", response_class=HTMLResponse)
def edit_article(article_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/login", status_code=303)
    
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    categories = db.query(Category).order_by(Category.display_order).all()
    return templates.TemplateResponse("editor.html", {"request": request, "admin": admin, "categories": categories, "article": article})

@app.post("/admin/article")
async def create_article(request: Request, response: Response, db: Session = Depends(get_db)):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/login", status_code=303)
    
    form = await request.form()
    title = form.get("title")
    slug = form.get("slug") or slugify(title)
    summary = form.get("summary", "")
    content = form.get("content", "")
    image_url = form.get("image_url", "")
    category_id = int(form.get("category_id", 1))
    status = form.get("status", "published")
    
    existing = db.query(Article).filter(Article.slug == slug).first()
    if existing:
        slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    article = Article(title=title, slug=slug, summary=summary, content=content, image_url=image_url, category_id=category_id, status=status)
    db.add(article)
    db.commit()
    
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/article/{article_id}/update")
async def update_article(article_id: int, request: Request, response: Response, db: Session = Depends(get_db)):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/login", status_code=303)
    
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    form = await request.form()
    article.title = form.get("title", article.title)
    new_slug = form.get("slug", article.slug)
    if new_slug != article.slug:
        existing = db.query(Article).filter(Article.slug == new_slug).first()
        if existing:
            new_slug = f"{new_slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        article.slug = new_slug
    article.summary = form.get("summary", article.summary)
    article.content = form.get("content", article.content)
    article.image_url = form.get("image_url", article.image_url)
    article.category_id = int(form.get("category_id", article.category_id))
    article.status = form.get("status", article.status)
    article.updated_at = datetime.utcnow()
    db.commit()
    
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/admin/article/{article_id}/delete")
def delete_article(article_id: int, request: Request, response: Response, db: Session = Depends(get_db)):
    admin = get_current_admin(request)
    if not admin:
        return RedirectResponse(url="/login", status_code=303)
    
    article = db.query(Article).filter(Article.id == article_id).first()
    if article:
        db.delete(article)
        db.commit()
    
    return RedirectResponse(url="/admin", status_code=303)

# ===================== API ROUTES =====================

@app.post("/api/preview")
def preview_markdown(data: PreviewRequest):
    html = render_markdown(data.content)
    return JSONResponse({"html": html})

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
