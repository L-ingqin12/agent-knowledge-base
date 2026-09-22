@echo off
REM llm-start -- one-click: ensure Ollama is up, verify models, show how to start.
REM Usage:  llm-start          (ensure service, then list)
REM         llm-start lab      (ensure service, then launch the Agent lab)
setlocal enabledelayedexpansion
set SCRIPT_DIR=%~dp0
set OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe
set OLLAMA_APP=%LOCALAPPDATA%\Programs\Ollama\ollama app.exe

REM --- sleep helper -------------------------------------------------------
REM Do NOT use `timeout /t` here. From a bash/MSYS shell (which is how these
REM scripts get invoked in practice) the name resolves to GNU timeout, which
REM rejects /t: "timeout: invalid time interval '/t'" -- and the wait silently
REM does not happen. `ping -n N` is the collision-free cmd sleep.
REM (An earlier fix hard-coded %SystemRoot%\System32\timeout.exe and got
REM  mangled into a literal TAB + "imeout.exe" by an unescaped \t. Gone.)

echo [llm-start] checking Ollama...
curl -s --max-time 4 http://127.0.0.1:11434/api/version >nul 2>&1
if %errorlevel%==0 (
  echo [llm-start] service already up.
  goto :ready
)

echo [llm-start] not running - starting tray app...
if not exist "%OLLAMA_APP%" (
  echo [llm-start] ERROR: not found at "%OLLAMA_APP%"
  echo [llm-start] install Ollama first, or set OLLAMA_APP manually.
  exit /b 1
)
start "" "%OLLAMA_APP%"

set /a TRIES=0
:wait
set /a TRIES+=1
ping -n 3 127.0.0.1 >nul 2>&1
curl -s --max-time 4 http://127.0.0.1:11434/api/version >nul 2>&1
if %errorlevel%==0 goto :ready
if !TRIES! lss 25 goto :wait
echo [llm-start] ERROR: service did not come up in 50s.
echo [llm-start] fallback: run  "%OLLAMA_EXE%" serve   in a separate window.
exit /b 1

:ready
echo [llm-start] service OK.
echo.
if /i "%~1"=="lab" (
  echo [llm-start] launching Agent lab...
  REM MUST use !PY! here, not %PY%. Inside a parenthesised block cmd expands
  REM %VAR% once at parse time -- BEFORE the `set` on the line above runs -- so
  REM %PY% would expand to nothing and this became '"" "...agent-lab.py"' and
  REM failed silently. This script already enables delayed expansion.
  set PY=D:\ProgramData\miniconda3\python.exe
  if not exist "!PY!" set PY=python
  "!PY!" "%SCRIPT_DIR%agent-lab.py"
  goto :eof
)

echo [llm-start] available roles:
"%SCRIPT_DIR%llm.cmd" --list
echo.
echo [llm-start] next steps:
echo    llm "question"                  one-shot inference
echo    llm-start lab                   interactive Agent lab (tool calling)
echo    git diff ^| llm "write commit"    pipe usage
endlocal
