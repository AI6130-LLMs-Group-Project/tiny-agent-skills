@echo off
setlocal enabledelayedexpansion

rem Setup script to download and build llama.cpp (Windows)

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"

set "LLAMA_DIR=%REPO_ROOT%\runtime\llama-cpp"
set "BUILD_DIR=%LLAMA_DIR%\build"
set "LLAMA_EXE=%BUILD_DIR%\bin\llama-server.exe"
set "LLAMA_EXE_RELEASE=%BUILD_DIR%\bin\Release\llama-server.exe"

rem Auto-detect backend with minimal deps:
set "BACKEND=cpu"
where nvcc >nul 2>nul
if %errorlevel%==0 (
  set "BACKEND=cuda"
) else (
  if defined VULKAN_SDK set "BACKEND=vulkan"
)

echo ============================================================
echo Backend auto-detect: %BACKEND%
echo ============================================================

where git >nul 2>nul
if errorlevel 1 (
  echo Error: git not found in PATH.
  goto :fail
)

where cmake >nul 2>nul
if errorlevel 1 (
  echo Error: cmake not found in PATH.
  goto :fail
)

if not exist "%LLAMA_DIR%" (
  echo Cloning llama.cpp into %LLAMA_DIR%...
  git clone https://github.com/ggml-org/llama.cpp "%LLAMA_DIR%"
  if errorlevel 1 goto :fail
) else (
  echo llama.cpp already exists: %LLAMA_DIR%
)

if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

echo Configuring build (Release, static, "%BACKEND%")...

if "%BACKEND%"=="cuda" (
  cmake -S "%LLAMA_DIR%" -B "%BUILD_DIR%" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_CUDA=ON
) else (
  if "%BACKEND%"=="vulkan" (
    cmake -S "%LLAMA_DIR%" -B "%BUILD_DIR%" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_VULKAN=ON
  ) else (
    cmake -S "%LLAMA_DIR%" -B "%BUILD_DIR%" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF
  )
)
if errorlevel 1 goto :fail

echo Building llama-server (Release)...
cmake --build "%BUILD_DIR%" --config Release --target llama-server
if errorlevel 1 goto :fail

if exist "%LLAMA_EXE_RELEASE%" (
  if not exist "%BUILD_DIR%\bin" mkdir "%BUILD_DIR%\bin"
  copy /y "%LLAMA_EXE_RELEASE%" "%LLAMA_EXE%" >nul
)

if exist "%LLAMA_EXE%" (
  echo Built: %LLAMA_EXE%
  goto :ok
)

echo Error: llama-server.exe not found after build.
goto :fail

:fail
echo.
echo Build FAILED (errorlevel=%errorlevel%).
echo (Scroll up to see the real error message.)
echo By Hanny: Have you cleared your previous build files yet? If not, pls do so
pause
endlocal & exit /b 1

:ok
echo.
echo Build SUCCEEDED.
pause
endlocal & exit /b 0
