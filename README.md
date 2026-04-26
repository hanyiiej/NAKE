# NAKE - New Ample Knowledge Eye

> A personal blog built with FastAPI + SQLite, featuring Markdown support and a clean dark-themed UI.

## Features

- 📝 Markdown article editor with live preview
- 🗂️ Category management
- 🔐 Password-protected admin panel
- 🌙 Dark theme UI
- 📱 Responsive design

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/2819067496/NAKE.git
cd NAKE
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and set your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password_here
SECRET_KEY=your-random-secret-key-here
PASSWORD_SALT=your-random-salt-here
```

> ⚠️ **Never commit `.env` to Git!** It's already in `.gitignore`.

### 3. Run

```bash
uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000` in your browser.  
Admin panel: `http://127.0.0.1:8000/admin`

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Frontend**: Jinja2 Templates + Vanilla JS
- **Markdown**: Mistune 3.x with syntax highlighting (Pygments)
- **Auth**: Session-based with hashed passwords

## Project Structure

```
NAKE/
├── main.py          # FastAPI app & routes
├── database.py      # SQLAlchemy models
├── auth.py          # Authentication & sessions
├── schemas.py       # Pydantic schemas
├── markdown_utils.py# Markdown rendering
├── templates/       # Jinja2 HTML templates
├── static/          # CSS, JS, images
├── uploads/         # User uploaded files
├── requirements.txt
└── .env.example     # Environment variable template
```
