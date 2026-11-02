@echo off
title Phenom Assistant Launcher
cd /d "C:\Phenom\apps\desktop"
echo ========================================================
echo Starting Phenom Personal Desktop Assistant...
echo ========================================================
start "" "node_modules\electron\dist\electron.exe" .
exit
