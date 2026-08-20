@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "ENTRY_FILE=app.py"
set "VENV_DIR=.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "REQUIREMENTS_FILE=requirements.txt"
set "STAMP_FILE=%VENV_DIR%\.clover_requirements.sha256"
set "VENV_CREATED=0"
set "NEEDS_INSTALL=0"

if not exist "%ENTRY_FILE%" (
    echo Clover could not start because "%ENTRY_FILE%" was not found.
    goto :fail
)

if not exist "%PYTHON_EXE%" (
    echo Creating Clover virtual environment...
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 -m venv "%VENV_DIR%" || goto :fail
    ) else (
        python -m venv "%VENV_DIR%" || goto :fail
    )
    set "VENV_CREATED=1"
)

call "%VENV_DIR%\Scripts\activate.bat" || goto :fail

if "%VENV_CREATED%"=="1" (
    echo Upgrading pip in the new virtual environment...
    python -m pip install --upgrade pip || goto :fail
)

for /f "usebackq delims=" %%H in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-FileHash -Algorithm SHA256 '%REQUIREMENTS_FILE%').Hash.ToLower()"`) do set "REQ_HASH=%%H"

if not exist "%STAMP_FILE%" set "NEEDS_INSTALL=1"

if exist "%STAMP_FILE%" (
    set /p STORED_HASH=<"%STAMP_FILE%"
    if /I not "%STORED_HASH%"=="%REQ_HASH%" set "NEEDS_INSTALL=1"
)

if "%NEEDS_INSTALL%"=="0" (
    python -c "import reportlab, streamlit" >nul 2>&1 || set "NEEDS_INSTALL=1"
)

if "%NEEDS_INSTALL%"=="1" (
    echo Installing Clover dependencies...
    python -m pip install -r "%REQUIREMENTS_FILE%" || goto :fail
    > "%STAMP_FILE%" echo %REQ_HASH%
)

echo Starting Clover...
python -m streamlit run "%ENTRY_FILE%"
if errorlevel 1 goto :fail
goto :eof

:fail
echo.
echo Clover failed to start. Review the messages above.
pause
exit /b 1
