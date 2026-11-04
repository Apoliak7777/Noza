@echo off
chcp 65001 >nul
title NOZA - web (localhost:8097)
pushd "%~dp0web"
echo.
echo   Web bezi na  http://localhost:8097/sk/   (nemecky: /de/)
echo   Zavriet toto okno = vypnut web.
echo.
start "" "http://localhost:8097/sk/"
python -m http.server 8097 --bind 127.0.0.1
popd
