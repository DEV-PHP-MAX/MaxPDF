@echo off
REM ============================================================
REM  MAX PDF - Gerar executavel portatil (MaxPDF.exe)
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

echo.
echo Instalando/atualizando dependencias de build...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements-dev.txt
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao instalar as dependencias de build.
    pause
    exit /b 1
)

echo.
echo Limpando builds anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist MaxPDF.spec del /q MaxPDF.spec

echo.
echo Gerando MaxPDF.exe com PyInstaller...
echo ^(isso pode levar alguns minutos^)
echo.

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name "MaxPDF" ^
    --collect-all customtkinter ^
    src\main.py

if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao gerar o executavel. Veja as mensagens acima.
    pause
    exit /b 1
)

echo.
echo ==========================================================
echo   MaxPDF.exe gerado com sucesso em:
echo   %cd%\dist\MaxPDF.exe
echo.
echo   Voce pode copiar esse arquivo para qualquer computador
echo   com Windows 10/11 e executa-lo sem instalar Python.
echo ==========================================================
echo.
pause
endlocal
