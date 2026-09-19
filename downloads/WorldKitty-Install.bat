@echo off
setlocal
set "URL=https://worldkitty.vercel.app"
set "DIR=%LOCALAPPDATA%\WorldKitty"
mkdir "%DIR%" 2>nul
(
  echo [InternetShortcut]
  echo URL=%URL%
  echo IconIndex=0
) > "%DIR%\WORLDKITTY.url"
(
  echo [InternetShortcut]
  echo URL=%URL%
  echo IconIndex=0
) > "%USERPROFILE%\Desktop\WORLDKITTY.url"
start "" "%URL%"
echo WORLDKITTY installed. Desktop shortcut created.
endlocal
