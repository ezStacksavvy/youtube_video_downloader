@echo off
echo --- Setting up environment ---

REM Step 1: Set the YouTube Cookies variable for this session.
REM Paste your FULL cookies.txt content between the parentheses.

REM Step 2: Set the full path to your FFmpeg bin directory.
set FFMPEG_PATH=C:\Your\Path\To\ffmpeg\bin

REM Step 3: Add the FFmpeg path to the PATH for this session.
set PATH=%FFMPEG_PATH%;%PATH%
echo FFmpeg path added to session PATH.

REM Step 4: Activate the Python virtual environment.
call .\venv\Scripts\activate
echo Virtual environment activated.

REM Step 5: Run the Flask application with debug mode.
echo --- Starting Flask Server ---
python -m flask run --debug