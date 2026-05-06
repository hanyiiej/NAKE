from fastapi import FastAPI, Request, Depends, HTTPException, Form, Response, Cookie, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
import os, uuid, logging, threading

# 加载 .env 文件（本地开发用）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 生产环境直接用系统环境变量，无需 dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PreviewRequest(BaseModel):
    content: str
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import Optional
import math

from database import get_db, init_db, Category, Article, Admin, Video
from schemas import ArticleCreate, ArticleUpdate, LoginRequest
from auth import hash_password, verify_password, create_session, verify_session, get_session_admin, delete_session
from markdown_utils import render_markdown, slugify
from video_processor import process_video_subtitles

app = FastAPI(title="NAKE - New Ample Knowledge Eye", description="A personal blog with markdown support")

# 目录
VIDEOS_DIR = "uploads/videos"
SUBTITLES_DIR = "uploads/subtitles"
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(SUBTITLES_DIR, exist_ok=True)

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


# ===================== VIDEO ROUTES =====================

def _do_process_video(video_id: int, video_path: str):
    """后台线程：调用 Whisper 生成字幕，更新数据库状态"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return
        video.status = "processing"
        db.commit()

        result = process_video_subtitles(video_id, video_path, SUBTITLES_DIR)
        video.status = "done"
        video.detected_language = result.get("detected_language", "")
        video.duration = result.get("duration", 0)
        db.commit()
        logger.info(f"Video {video_id} processed successfully.")
    except Exception as e:
        logger.error(f"Video {video_id} processing failed: {e}")
        db = SessionLocal()
        v = db.query(Video).filter(Video.id == video_id).first()
        if v:
            v.status = "error"
            v.error_msg = str(e)[:500]
            db.commit()
    finally:
        db.close()


@app.get("/videos", response_class=HTMLResponse)
def video_list(request: Request, db: Session = Depends(get_db)):
    admin = get_current_admin(request)
    videos = db.query(Video).order_by(desc(Video.created_at)).all()
    return templates.TemplateResponse("video_list.html", {
        "request": request, "videos": videos, "admin": admin
    })


@app.get("/videos/{video_id}", response_class=HTMLResponse)
def video_player(video_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_current_admin(request)
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return templates.TemplateResponse("video_player.html", {
        "request": request, "video": video, "admin": admin
    })


@app.post("/api/videos/upload")
async def upload_video(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(""),
    db: Session = Depends(get_db),
):
    # 限制文件类型
    allowed_types = {"video/mp4", "video/quicktime", "video/x-msvideo",
                     "video/x-matroska", "video/webm", "video/mpeg"}
    if file.content_type not in allowed_types and not (file.filename or "").lower().endswith(
        (".mp4", ".mov", ".avi", ".mkv", ".webm", ".mpeg", ".mpg")
    ):
        raise HTTPException(status_code=400, detail="不支持的文件格式，请上传视频文件")

    # 生成唯一文件名
    ext = os.path.splitext(file.filename or "video.mp4")[1].lower() or ".mp4"
    stored_name = f"{uuid.uuid4().hex}{ext}"
    video_path = os.path.join(VIDEOS_DIR, stored_name)

    # 保存文件
    with open(video_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            f.write(chunk)

    # 数据库记录
    video_title = title.strip() or os.path.splitext(file.filename or "视频")[0]
    video = Video(
        title=video_title,
        filename=stored_name,
        original_filename=file.filename or stored_name,
        status="pending",
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    # 后台线程处理（不阻塞请求）
    t = threading.Thread(target=_do_process_video, args=(video.id, video_path), daemon=True)
    t.start()

    return JSONResponse({"id": video.id, "title": video_title, "status": "pending"})


@app.get("/api/videos/{video_id}/status")
def video_status(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Not found")
    return JSONResponse({
        "id": video.id,
        "status": video.status,
        "detected_language": video.detected_language,
        "duration": video.duration,
        "error_msg": video.error_msg,
    })


@app.get("/api/videos/{video_id}/stream")
def stream_video(video_id: int, request: Request, db: Session = Depends(get_db)):
    """支持 Range 请求的视频流"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Not found")
    video_path = os.path.join(VIDEOS_DIR, video.filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(video_path, media_type="video/mp4", headers={
        "Accept-Ranges": "bytes"
    })


@app.get("/api/videos/{video_id}/subtitle/{lang}")
def get_subtitle(video_id: int, lang: str, db: Session = Depends(get_db)):
    """返回 WebVTT 字幕文件"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video or video.status != "done":
        raise HTTPException(status_code=404, detail="Subtitle not ready")
    if lang not in ("orig", "en"):
        raise HTTPException(status_code=400, detail="lang must be orig or en")
    vtt_path = os.path.join(SUBTITLES_DIR, f"{video_id}_{lang}.vtt")
    if not os.path.exists(vtt_path):
        raise HTTPException(status_code=404, detail="Subtitle file not found")
    return FileResponse(vtt_path, media_type="text/vtt")


@app.delete("/api/videos/{video_id}")
def delete_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Not found")
    # 删除文件
    for path in [
        os.path.join(VIDEOS_DIR, video.filename),
        os.path.join(SUBTITLES_DIR, f"{video_id}_orig.vtt"),
        os.path.join(SUBTITLES_DIR, f"{video_id}_en.vtt"),
    ]:
        if os.path.exists(path):
            os.remove(path)
    db.delete(video)
    db.commit()
    return JSONResponse({"ok": True})

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
