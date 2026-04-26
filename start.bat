@echo off
echo ========================================
echo   MyBlog - Starting Server
echo ========================================
echo.
echo Activating conda environment...
call conda activate fastapi_env
echo.
echo Installing dependencies (if needed)...
pip install -q -r requirements.txt
echo.
echo Starting FastAPI server at http://localhost:8000
echo.
echo Admin Login:
echo   Username: admin
echo   Password: admin123
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

cd /d "%~dp0"
python main.py

pause
