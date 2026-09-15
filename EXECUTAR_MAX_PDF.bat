@echo off
REM ============================================================
REM  MAX PDF - Executar em modo de desenvolvimento
REM  Nao contem caminhos fixos: sempre roda a partir da pasta
REM  onde este arquivo .bat esta localizado.
REM ============================================================

setlocal
cd /d "%~dp0"

echo Verificando instalacao do Python...
where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo [ERRO] Python nao foi encontrado no PATH do sistema.
    echo Instale o Python 3.12 em https://www.python.org/downloads/
    echo e marque a opcao "Add Python to PATH" durante a instalacao.
    echo.
    pause
    exit /b 1
)

echo Verificando dependencias do Max PDF...
python -m pip show customtkinter >nul 2>nul
if errorlevel 1 (
    echo Instalando dependencias necessarias ^(primeira execucao^)...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERRO] Falha ao instalar as dependencias.
        pause
        exit /b 1
    )
)

echo.
echo Iniciando Max PDF...
echo.
python src\main.py

if errorlevel 1 (
    echo.
    echo [ERRO] O Max PDF foi encerrado com um erro. Consulte os logs
    echo em %%LOCALAPPDATA%%\MaxPDF\logs\maxpdf.log para mais detalhes.
    pause
)

endlocal
