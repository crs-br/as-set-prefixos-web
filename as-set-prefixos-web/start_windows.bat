@echo off
setlocal enabledelayedexpansion
title Registry Console - prefixos por as-set
cd /d "%~dp0"

echo ============================================
echo  Registry Console - prefixos por as-set
echo ============================================
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    set "PYEXE=python"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set "PYEXE=py"
    ) else (
        echo [ERRO] Python 3 nao foi encontrado neste computador.
        echo Instale em https://www.python.org/downloads/
        echo IMPORTANTE: durante a instalacao, marque a caixa "Add Python to PATH".
        echo.
        pause
        exit /b 1
    )
)

if not exist ".venv" (
    echo Criando ambiente virtual (.venv) ...
    %PYEXE% -m venv .venv
    if not %errorlevel%==0 (
        echo [ERRO] Falha ao criar o ambiente virtual.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo Instalando dependencias (Flask) ...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet
if not %errorlevel%==0 (
    echo [ERRO] Falha ao instalar dependencias. Verifique sua conexao com a internet.
    pause
    exit /b 1
)

echo.
echo Iniciando o servidor... o navegador deve abrir automaticamente.
echo Para encerrar, feche esta janela ou pressione CTRL+C.
echo.

python app.py

pause
