@echo off
chcp 65001 >nul
echo ====================================
echo    Запуск Telegram бота
echo ====================================
echo.

cd /d "%~dp0"

echo Текущая директория: %CD%
echo.

echo Проверка Python...
py --version
if errorlevel 1 (
    echo ОШИБКА: Python не найден!
    echo Убедитесь, что Python установлен и добавлен в PATH
    pause
    exit /b 1
)

echo.
echo Запуск бота...
echo Нажмите Ctrl+C для остановки
echo ====================================
echo.

py bot.py

if errorlevel 1 (
    echo.
    echo ====================================
    echo Бот завершился с ошибкой!
    echo ====================================
    pause
)


