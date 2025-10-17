@echo off
SETLOCAL

echo Instalando Lupan no Windows...

:: Pasta de destino
SET DEST=%ProgramFiles%\Lupan

:: Criar pasta se não existir
if not exist "%DEST%" (
    mkdir "%DEST%"
)

:: Copiar arquivos
xcopy /s /i /y "%~dp0lupan_interpreter.py" "%DEST%"
xcopy /s /i /y "%~dp0exemplos" "%DEST%\exemplos"
xcopy /s /i /y "%~dp0icone" "%DEST%\icone"

:: Adicionar Lupan ao PATH (usuário)
setx PATH "%PATH%;%DEST%"

echo Lupan instalado com sucesso!
echo Abra um novo CMD e digite: lupan exemplos\exemplo.lp
pause
