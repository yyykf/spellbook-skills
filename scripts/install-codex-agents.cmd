@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-codex-agents.ps1" %*
