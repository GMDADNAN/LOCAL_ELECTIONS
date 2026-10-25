@echo off
title Voter Search App - Kurnool Ward 9
color 1F
cls
echo.
echo  =====================================================
echo   Voter Search App - Kurnool Municipal Corporation
echo   Ward 9 - Photo Electoral Roll 2026
echo  =====================================================
echo.

cd /d "D:\Zubair_mamu\PDF_Search_App"

:: Step 1 - Extract PDF data if not already done
if not exist "voter_data.json" (
    echo  [1/2] Extracting voter data from PDF...
    echo       This may take 1-2 minutes on first run.
    echo.
    python extract_pdf.py
    echo.
) else (
    echo  [1/2] Voter data already extracted. Skipping...
)

:: Step 2 - Start the web server
echo  [2/2] Starting web server...
echo.
echo  -------------------------------------------------------
echo   Open your browser and go to:  http://localhost:5000
echo  -------------------------------------------------------
echo.
echo  Press Ctrl+C to stop the server.
echo.

:: Auto-open browser
start "" http://localhost:5000

python app.py
pause
