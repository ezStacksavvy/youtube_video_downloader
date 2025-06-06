@echo off
echo --- Setting up environment ---

REM Step 1: Set the full path to your FFmpeg bin directory.
REM Make sure this path is 100% correct! Use the path you found with Get-Command.
set FFMPEG_PATH=C:\Users\sanje\AppData\Local\Microsoft\WinGet\Packages\Gyan.Ffmpeg.Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-7.1.1-full_build\bin

REM Step 2: Add the FFmpeg path to the PATH for this session.
set PATH=%FFMPEG_PATH%;%PATH%
echo FFmpeg path added to session PATH.

REM Step 3: Activate the Python virtual environment.
call .\venv\Scripts\activate
echo Virtual environment activated.

REM Step 4: Run the Flask application with debug mode.
echo --- Starting Flask Server ---
python -m flask run --debug