@echo off
ECHO.
ECHO #################################################
ECHO ##  YouTube Downloader Project Setup (Windows) ##
ECHO #################################################
ECHO.

ECHO # Step 1: Setting up the Python Backend...
ECHO #===========================================
cd backend

ECHO # Creating Python virtual environment...
IF NOT EXIST venv (
    python -m venv venv
) ELSE (
    ECHO # Virtual environment already exists. Skipping creation.
)

ECHO # Activating environment and installing Python packages...
call .\\venv\\Scripts\\activate
pip install -r requirements.txt

ECHO # Backend setup complete.
cd ..
ECHO.

ECHO # Step 2: Setting up the React Frontend...
ECHO #==========================================
cd frontend

ECHO # Installing Node.js packages...
npm install

cd ..
ECHO.

ECHO #################################################
ECHO ##      SETUP COMPLETE!          ##
ECHO #################################################
ECHO.
ECHO # To run the application, you now need to:
ECHO # 1. Open one terminal and run the backend.
ECHO # 2. Open a SECOND terminal and run the frontend.
ECHO # See the README.md for the exact commands.
ECHO.

pause