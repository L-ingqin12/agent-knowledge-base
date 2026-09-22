@echo off
REM llm-learn -- one command from "nothing running" to "hands on keyboard".
REM
REM ENCODING: this file is saved as GBK (cp936) ON PURPOSE. cmd.exe reads .cmd files
REM using the ANSI code page (936 here), so a UTF-8 file shows mojibake in the menu.
REM If you edit this file, save it back as ANSI/GBK -- do NOT save as UTF-8.
REM (The sibling llm-start.cmd / llm-stop.cmd are pure ASCII and immune.)
REM
REM Usage:
REM   llm-learn              menu
REM   llm-learn react        裸 API + 手写 ReAct 循环  (agent-lab.py)
REM   llm-learn lg           LangGraph 课程            (lab/lg-lab.py)
REM   llm-learn skill        LangGraph 能力自测        (lab/test_langgraph_skill.py)
REM   llm-learn stop         停止并清理
setlocal
set SCRIPT_DIR=%~dp0
set LAB=%~dp0..\lab
set VENV_PY=%LAB%\.venv\Scripts\python.exe

REM --- 1) 确保服务在跑（llm-start 幂等）---
REM 不把 llm-start 的输出丢进 nul：它失败时那句原因正是用户需要看的东西。
call "%SCRIPT_DIR%llm-start.cmd"
curl -s --max-time 4 http://127.0.0.1:11434/api/version >nul 2>&1
if not %errorlevel%==0 (
  echo [llm-learn] Ollama 未就绪（见上方 llm-start 的输出）。
  exit /b 1
)

if /i "%~1"=="react" goto :react
if /i "%~1"=="lg"    goto :lg
if /i "%~1"=="skill" goto :skill
if /i "%~1"=="stop"  goto :stop

:menu
echo.
echo ============================================================
echo   本地 LLM 实践台 -- 选一个开始
echo ============================================================
echo   1) ReAct 裸循环    agent-lab   手写循环，看清每一步   (用 miniconda python)
echo   2) LangGraph 课程  lg-lab      6 节课，由浅入深       (用 lab venv)
echo   3) LangGraph 自测  test_...    先 stub 验图再测模型   (用 lab venv)
echo   4) 关闭并清理      llm-stop    释放显存/内存，清 Python 残留
echo   q) 退出
echo.
set "CHOICE="
set /p CHOICE=选择 ^>
if not defined CHOICE (
  echo 已退出。
  goto :eof
)
if /i "%CHOICE%"=="1" goto :react
if /i "%CHOICE%"=="2" goto :lg
if /i "%CHOICE%"=="3" goto :skill
if /i "%CHOICE%"=="4" goto :stop
if /i "%CHOICE%"=="q" goto :eof
echo 无效选择：%CHOICE%
goto :eof

:react
set PY=D:\ProgramData\miniconda3\python.exe
if not exist "%PY%" set PY=python
"%PY%" "%SCRIPT_DIR%agent-lab.py"
goto :eof

:lg
call :needvenv || goto :eof
"%VENV_PY%" "%LAB%\lg-lab.py"
goto :eof

:skill
call :needvenv || goto :eof
"%VENV_PY%" "%LAB%\test_langgraph_skill.py"
goto :eof

:stop
call "%SCRIPT_DIR%llm-stop.cmd"
if errorlevel 1 echo [llm-learn] 注意：llm-stop 报了未完全清理，见上方输出。
goto :eof

:needvenv
if exist "%VENV_PY%" exit /b 0
echo [llm-learn] 缺少 venv: %VENV_PY%
echo [llm-learn] 建一次即可（版本已钉住，lg-lab 依赖 create_agent，需 langchain 1.x）:
echo     D:\ProgramData\miniconda3\python.exe -m venv "%LAB%\.venv"
echo     "%VENV_PY%" -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple langchain==1.4.2 langgraph==1.2.12 langchain-ollama==1.1.0
echo [llm-learn] 已中止。
exit /b 1
