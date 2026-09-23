@echo off
rem Reset the database to the initial sample data (transaction history is deleted)
cd /d "%~dp0api"
.venv\Scripts\python.exe seed.py
pause
