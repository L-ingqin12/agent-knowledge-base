@echo off
REM llm -- one-line local inference entry point (Ollama).
REM See llm.py header for usage. Example: llm -t coder "write quicksort"
setlocal
set PY=D:\ProgramData\miniconda3\python.exe
if not exist "%PY%" set PY=python
"%PY%" "%~dp0llm.py" %*
