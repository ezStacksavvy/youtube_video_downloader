#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# ANSI Color Codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}#################################################${NC}"
echo -e "${GREEN}##  YouTube Downloader Project Setup (Mac/Linux) ##${NC}"
echo -e "${GREEN}#################################################${NC}"
echo

echo -e "${YELLOW}# Step 1: Setting up the Python Backend...${NC}"
echo -e "${YELLOW}#===========================================${NC}"
cd backend

echo "# Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
else
    echo "# Virtual environment already exists. Skipping creation."
fi

echo "# Activating environment and installing Python packages..."
source venv/bin/activate
pip install -r requirements.txt
deactivate # Deactivate after installation

echo "# Backend setup complete."
cd ..
echo

echo -e "${YELLOW}# Step 2: Setting up the React Frontend...${NC}"
echo -e "${YELLOW}#==========================================${NC}"
cd frontend

echo "# Installing Node.js packages..."
npm install

cd ..
echo

echo -e "${GREEN}#################################################${NC}"
echo -e "${GREEN}##              SETUP COMPLETE!                ##${NC}"
echo -e "${GREEN}#################################################${NC}"
echo
echo -e "# To run the application, you now need to:"
echo -e "# 1. Open one terminal and run the backend."
echo -e "# 2. Open a SECOND terminal and run the frontend."
echo -e "# See the README.md for the exact commands."
echo