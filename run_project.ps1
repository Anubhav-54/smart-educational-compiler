$ErrorActionPreference = "Stop"

Write-Host "Starting Smart Educational Compiler..." -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'D:\pbl compiler design'; python web_api_1.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'D:\pbl compiler design\frontend'; npm run dev"

Write-Host "Backend:  http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Green
