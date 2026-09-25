@echo off
setlocal
title Publiser maanedskatalog
cd /d "%~dp0"

echo.
echo Publiserer maanedskatalogen til GitHub og Render...
echo.

git add -- server.py hub.html hub.js oktober-katalog tools/build_october_catalog.py supabase/migrations/030_october_monthly_catalog_access.sql Publiser_Maanedskatalog.cmd
if errorlevel 1 goto :error

git diff --cached --quiet
if errorlevel 1 (
  git commit -m "Publiser maanedens tilbudskatalog"
  if errorlevel 1 goto :error
) else (
  echo Ingen nye katalogendringer aa lagre.
)

git push origin main
if errorlevel 1 goto :error

echo.
echo Ferdig. Render starter publiseringen automatisk.
echo Du kan lukke dette vinduet.
pause
exit /b 0

:error
echo.
echo Publiseringen stoppet. Ta bilde av feilmeldingen og send den til Codex.
pause
exit /b 1
