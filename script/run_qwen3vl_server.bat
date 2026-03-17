@echo off
setlocal

rem Script to run llama-server with Qwen3VL-2B-Instruct model
rem This script is for Windows OS only, for Unix OS's, run the .sh scripts

set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..") do set PROJECT_ROOT=%%~fI

set LLAMA_SERVER=%PROJECT_ROOT%\runtime\llama-cpp\build\bin\llama-server.exe
set MODEL_DIR=%PROJECT_ROOT%\runtime\models\Qwen3vl-2B
set MODEL=%MODEL_DIR%\Qwen3VL-2B-Instruct-Q8_0.gguf
set MMPROJ=%MODEL_DIR%\mmproj-Qwen3VL-2B-Instruct-F16.gguf
set PORT=%~1
if "%PORT%"=="" set PORT=1025

if not exist "%LLAMA_SERVER%" (
  echo Error: llama-server not found at %LLAMA_SERVER%
  exit /b 1
)

if not exist "%MODEL%" (
  echo Error: Model file not found at %MODEL%
  exit /b 1
)

if not exist "%MMPROJ%" (
  echo Error: MMProj file not found at %MMPROJ%
  exit /b 1
)

echo Starting llama-server with Qwen3VL-2B-Instruct...
echo Model: %MODEL%
echo MMProj: %MMPROJ%

echo Port: %PORT%

"%LLAMA_SERVER%" ^
  -m "%MODEL%" ^
  --mmproj "%MMPROJ%" ^
  -c 4096 ^
  -ngl 999 ^
  --port %PORT%

endlocal
