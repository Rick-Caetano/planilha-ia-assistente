@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."

set "NOME=AssistentePlanilhasIA"
set "DIST=dist\%NOME%"

echo Montando pacote de distribuicao em %DIST%...

if exist "dist" rmdir /s /q "dist"
mkdir "%DIST%"
mkdir "%DIST%\instalation"

rem Instalador (raiz do pacote) + logica de dependencias
copy "instalation\Instalar.bat" "%DIST%\Instalar.bat" >nul
copy "instalation\install.py" "%DIST%\instalation\install.py" >nul
copy "instalation\dependencies.json" "%DIST%\instalation\dependencies.json" >nul
copy "instalation\icon.ico" "%DIST%\instalation\icon.ico" >nul

rem App do dia a dia: mesma estrutura plana do repositorio.
rem Nunca copiar .env, config.json ou logs/ (segredos/estado real do dev).
copy "app.py" "%DIST%\app.py" >nul
copy "AbrirAssistente.bat" "%DIST%\AbrirAssistente.bat" >nul
copy "launcher.pyw" "%DIST%\launcher.pyw" >nul
copy "requirements.txt" "%DIST%\requirements.txt" >nul
robocopy "core" "%DIST%\core" /E /XD __pycache__ >nul
robocopy "data" "%DIST%\data" /E >nul
robocopy "assets" "%DIST%\assets" /E >nul

echo Compactando %NOME%.zip...
powershell -NoProfile -Command "Compress-Archive -Path '%DIST%\*' -DestinationPath 'dist\%NOME%.zip' -Force"

echo.
echo Pronto: dist\%NOME%.zip
echo Esse e o arquivo pra anexar numa Release do GitHub.
pause
