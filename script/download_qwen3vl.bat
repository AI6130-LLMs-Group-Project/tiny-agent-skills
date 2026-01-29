@echo off
setlocal enabledelayedexpansion

rem Script to download Qwen3-VL-2B-Instruct-GGUF and its mmproj (Windows)
rem Files are downloaded from Hugging Face: Qwen/Qwen3-VL-2B-Instruct-GGUF

set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..") do set REPO_ROOT=%%~fI

set MODEL_DIR=%REPO_ROOT%\runtime\models\Qwen3vl-2B
set HF_REPO=Qwen/Qwen3-VL-2B-Instruct-GGUF
set BASE_URL=https://huggingface.co/%HF_REPO%/resolve/main

set MODEL_FILE=Qwen3VL-2B-Instruct-Q8_0.gguf
set MMPROJ_FILE=mmproj-Qwen3VL-2B-Instruct-F16.gguf

if not exist "%MODEL_DIR%" mkdir "%MODEL_DIR%"

echo Downloading Qwen3-VL-2B-Instruct-GGUF files to %MODEL_DIR%
echo ==============================================

if exist "%MODEL_DIR%\%MODEL_FILE%" (
  echo Model file already exists: %MODEL_FILE%
) else (
  echo Downloading %MODEL_FILE%...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '%BASE_URL%/%MODEL_FILE%' -OutFile '%MODEL_DIR%\%MODEL_FILE%'"
  if errorlevel 1 exit /b 1
  echo Downloaded: %MODEL_FILE%
)

if exist "%MODEL_DIR%\%MMPROJ_FILE%" (
  echo mmproj file already exists: %MMPROJ_FILE%
) else (
  echo Downloading %MMPROJ_FILE%...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '%BASE_URL%/%MMPROJ_FILE%' -OutFile '%MODEL_DIR%\%MMPROJ_FILE%'"
  if errorlevel 1 exit /b 1
  echo Downloaded: %MMPROJ_FILE%
)

echo.
echo Download complete!
echo Files are located in: %MODEL_DIR%
dir "%MODEL_DIR%"

endlocal
