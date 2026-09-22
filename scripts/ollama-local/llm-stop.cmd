@echo off
REM llm-stop -- fast, COMPLETE shutdown of the local LLM stack.
REM
REM Why this exists: `taskkill ollama.exe` does NOT kill its child llama-server.exe.
REM The orphans keep holding VRAM and RAM (measured: 2 orphans ~7 GB, model GPU share
REM dropped to 8%, decode halved).
REM
REM Defects fixed here, all found by process census + timing (2026-09-22):
REM
REM  1. FALSE-PASS VERIFIER. The old check was `Get-Process ollama,llama-server`,
REM     an EXACT-NAME match -- it cannot see "ollama app.exe". Verified live:
REM           Get-Process ollama,llama-server -> ollama 1996, llama-server 17196
REM           Get-Process *ollama*            -> ollama 1996, ollama app 9384
REM     So if the tray app survived, this script printed "clean" and exited 0.
REM
REM  2. PYTHON CLIENTS NEVER REAPED. A leftover python client keeps touching :11434,
REM     renewing OLLAMA_KEEP_ALIVE and pinning the model in VRAM -- "stopped" but VRAM
REM     never came back. Now reaped BY PATH, never by image name (taskkill /IM python.exe
REM     would kill unrelated python toolchains).
REM
REM  3. NO PORT CHECK. `ollama app.exe` holds a second listening port, 127.0.0.1:3000,
REM     that was never verified. Ports are now an acceptance criterion.
REM
REM  4. SELF-INFLICTED SLOWNESS (measured, this was the biggest surprise). An earlier
REM     revision added a "bounded port poll" to replace fixed sleeps -- but curl against
REM     a STOPPED port takes a full 1178 ms here (the connection is dropped, not refused),
REM     so the poll never short-circuited and each iteration burned ~2.35 s. `taskkill /F`
REM     is already synchronous: when it returns the process is dead. The wait is gone
REM     entirely, and that poll was the single largest cost in the script.
REM
REM     Timing ledger (measured on this machine):
REM       curl to stopped :11434 .......... 1178 ms   (per poll iteration!)
REM       Get-NetTCPConnection (all) ...... 2190 ms
REM       netstat -ano (all) ..............  174 ms   <- replaced it, 12x faster
REM       Get-CimInstance Win32_Process ... 1169 ms  (client-side filter)
REM       Get-CimInstance -Filter python ..  768 ms   <- server-side filter
REM       PowerShell startup ..............  416 ms   <- so: only ONE call, not three
REM       nvidia-smi ......................  226 ms
REM
REM Note OllamaSetup.exe (auto-updater) is DETECTED but deliberately NOT killed --
REM killing an installer mid-write is worse than letting it finish and re-launch.
REM
REM Sleeps, if ever needed here, use `ping -n N`, never `timeout /t` -- from bash the
REM latter resolves to GNU timeout and the wait silently does not happen.
setlocal enabledelayedexpansion

echo [llm-stop] stopping Ollama processes...
REM Order matters: app is the supervisor (its server_windows.go even taskkills
REM "foreign" `ollama serve` on startup). Kill the supervisor first, then the rest.
taskkill /F /IM "ollama app.exe"     >nul 2>&1
taskkill /F /IM "ollama.exe"         >nul 2>&1
taskkill /F /IM "llama-server.exe"   >nul 2>&1
taskkill /F /IM "llama-quantize.exe" >nul 2>&1

echo [llm-stop] reaping leftover lab clients (by path, not by image name)...
REM One PowerShell call does the reaping AND the RAM read -- PowerShell startup alone
REM is ~420 ms, so calling it three times costs more than the work itself.
REM The match below must be ANCHORED. An earlier revision used -like '*OllamaModels*'
REM against the whole command line, which would force-kill any unrelated python that
REM merely MENTIONED the path (e.g. `python backup.py D:\OllamaModels`). Anchoring to
REM our own script locations keeps recall high without that blast radius.
REM NOTE: keep every REM OUTSIDE the ^-continued block. A REM placed inside it is
REM spliced into the same logical line and handed to powershell as literal arguments.
powershell -NoProfile -Command ^
  "$me = $PID;" ^
  "$all = Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" -EA SilentlyContinue;" ^
  "$t = $all | Where-Object { $_.ProcessId -ne $me -and (" ^
  "   $_.ExecutablePath -like 'D:\OllamaModels\lab\.venv\*' -or" ^
  "   $_.CommandLine -match 'OllamaModels\\(bin|bench|lab)\\[^\\]+\.py' ) };" ^
  "$skipped = @($all | Where-Object { -not $_.CommandLine -and -not $_.ExecutablePath }).Count;" ^
  "if ($t) { $t | ForEach-Object { Write-Host ('  kill {0}  {1}' -f $_.ProcessId, $_.ExecutablePath); Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue } }" ^
  "else { Write-Host '  no lab python leftovers' };" ^
  "if ($skipped) { Write-Host ('  note: {0} python process(es) had no readable command line; not touched' -f $skipped) };" ^
  "$os = Get-CimInstance Win32_OperatingSystem;" ^
  "Write-Host ('  RAM free : ' + [math]::Round($os.FreePhysicalMemory/1MB,2) + ' GB')"

echo [llm-stop] verifying...
set BAD=0

REM --- processes: tasklist (~180 ms) instead of a second PowerShell round trip ---
REM /V /C:"OllamaSetup" excludes the auto-updater from the gate. It matches "ollama"
REM but is NOT ours to kill (killing an installer mid-write is worse than letting it
REM finish), and without this exclusion every shutdown during an auto-update would
REM report a false failure. It is reported separately below.
tasklist /FO CSV /NH 2>nul | findstr /I /C:"ollama" /C:"llama" | findstr /I /V /C:"OllamaSetup" >nul 2>&1
if not errorlevel 1 (
  set BAD=1
  echo   PROCESSES still alive:
  tasklist /FO CSV /NH 2>nul | findstr /I /C:"ollama" /C:"llama" | findstr /I /V /C:"OllamaSetup"
) else (
  echo   processes : clean ^(ollama / ollama app / llama-server all gone^)
)

REM --- ports: REPORT ONLY, never a pass/fail gate ---
REM An earlier revision gated on "ports 11434 and 3000 released". That was wrong twice:
REM   (a) Verified 2026-09-22: `ollama app.exe` CAN be running with port 3000 NOT
REM       listening at all -- the "app always holds 3000" assumption did not hold.
REM   (b) 3000 is one of the most common dev ports. Any unrelated program (node,
REM       Jupyter, Grafana...) binding it would make this script report failure and
REM       exit 1 even after a perfectly clean shutdown.
REM The process check above is the real acceptance criterion. Ports are printed so a
REM human can see the whole picture, and so a port held by the WRONG program is visible.
netstat -ano 2>nul | findstr ":11434" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
  echo   port 11434: released
) else (
  echo   port 11434: STILL LISTENING -- owner:
  netstat -ano 2>nul | findstr ":11434" | findstr "LISTENING"
  echo     ^(not counted as failure here; if the owner is not ollama, another program took the port^)
)

tasklist /FO CSV /NH 2>nul | findstr /I /C:"OllamaSetup.exe" >nul 2>&1
if not errorlevel 1 echo   NOTE: OllamaSetup.exe is running (auto-update). Left alone on purpose.

echo.
echo   VRAM ^(used, total^):
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader

if "!BAD!"=="1" (
  echo.
  echo [llm-stop] WARNING: something survived. Retrying process kill once...
  taskkill /F /IM "ollama app.exe"   >nul 2>&1
  taskkill /F /IM "ollama.exe"       >nul 2>&1
  taskkill /F /IM "llama-server.exe" >nul 2>&1
  tasklist /FO CSV /NH 2>nul | findstr /I /C:"ollama" /C:"llama" >nul 2>&1
  if not errorlevel 1 (
    echo [llm-stop] STILL LEFTOVER - check manually.
    exit /b 1
  )
  echo [llm-stop] clean now.
  exit /b 0
)

echo.
echo [llm-stop] done. Restart anytime with:  llm-start
endlocal
