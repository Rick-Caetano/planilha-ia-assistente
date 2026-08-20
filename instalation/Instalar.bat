@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo   Assistente de Planilhas com IA - Instalador
echo ============================================
echo.

set "PYTHON_EXE="

rem 1) Tenta usar um Python ja instalado no PATH
where python >nul 2>nul
if %errorlevel%==0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
    echo Python encontrado no PATH: !PYVER!
    set "PYTHON_EXE=python"
) else (
    echo Python nao encontrado no PATH.
)

rem 2) Se nao achou, baixa e instala o Python oficial (silencioso, so para o usuario atual)
if not defined PYTHON_EXE (
    echo.
    echo Baixando o instalador oficial do Python 3.11.6 de python.org...
    set "PY_INSTALLER=%TEMP%\python-3.11.6-amd64.exe"
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe' -OutFile '%PY_INSTALLER%'"

    if not exist "%PY_INSTALLER%" (
        echo.
        echo ERRO: nao foi possivel baixar o instalador do Python.
        echo Verifique sua conexao com a internet e tente novamente.
        pause
        exit /b 1
    )

    echo Instalando Python 3.11.6 silenciosamente ^(pode levar 1-2 minutos^)...
    start /wait "" "%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0

    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python311\python.exe"
    if not exist "!PYTHON_EXE!" (
        echo.
        echo ERRO: a instalacao do Python parece ter falhado.
        echo Instale manualmente em https://www.python.org/downloads/ e rode este instalador de novo.
        pause
        exit /b 1
    )
    echo Python instalado com sucesso.
)

echo.

if not exist "app.py" (
    echo ERRO: nao encontrei app.py nesta pasta.
    echo Extraia o zip por completo antes de rodar este instalador.
    pause
    exit /b 1
)

echo Instalando dependencias do projeto...
"!PYTHON_EXE!" "instalation\install.py"

echo.
echo Limpando arquivos que so serviram para a instalacao...
rmdir /s /q "instalation" 2>nul

echo.
echo ============================================
echo   Instalacao concluida!
echo   Use o atalho criado na Area de Trabalho
echo   para abrir o Assistente de Planilhas com IA.
echo ============================================
pause

start /min cmd /c "timeout /t 1 >nul & del "%~f0""
exit /b
