#!/bin/bash

echo "========================================"
echo "Cricket Prediction System - Quick Start"
echo "========================================"
echo ""

echo "Step 1: Installing required packages..."
pip3 install -r requirements.txt
echo ""

echo "Step 2: Setting up database..."
python3 manage.py makemigrations
python3 manage.py migrate
echo ""

echo "Step 3: Creating sample data..."
echo "Sample data will be created automatically when you run predictions"
echo ""

echo "Step 4: Starting server..."
echo ""
echo "========================================"
echo "Server is starting..."
echo "Open your browser and go to:"
echo "http://127.0.0.1:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""

python3 manage.py runserver
