@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="/hidden" goto :RUN

where pythonw >nul 2>nul
if errorlevel 1 (
    mshta "javascript:new ActiveXObject('WScript.Shell').Popup('Python nao foi encontrado nesta pasta. Rode o instalador novamente.', 0, 'Assistente de Planilhas com IA', 16);close();"
    exit /b 1
)

set "VBS=%TEMP%\abrir_assistente_%RANDOM%.vbs"
> "%VBS%" echo Set objShell = CreateObject("WScript.Shell")
>> "%VBS%" echo objShell.Run "cmd /c ""%~f0"" /hidden", 0, False
cscript //nologo "%VBS%"
del "%VBS%"
exit /b

:RUN
start "" /min pythonw "launcher.pyw"
exit /b
