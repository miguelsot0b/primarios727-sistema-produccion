@echo off
echo ===== Preparando repositorio para Streamlit Cloud =====
echo.
echo Este script eliminara archivos no necesarios para Streamlit Cloud.
echo.
echo Archivos que se eliminaran:
echo - app\app.py
echo - app\download_data.py
echo - run_app.bat
echo - run_app.ps1
echo - Carpeta .temp si existe
echo.
set /p CONFIRM=Estas seguro de eliminar estos archivos? (S/N): 

if /i "%CONFIRM%" neq "S" (
    echo Operacion cancelada.
    exit /b 0
)

echo.
echo Eliminando archivos...

if exist app\app.py (
    del app\app.py
    echo - app\app.py eliminado
)

if exist app\download_data.py (
    del app\download_data.py
    echo - app\download_data.py eliminado
)

if exist run_app.ps1 (
    del run_app.ps1
    echo - run_app.ps1 eliminado
)

if exist run_app.bat (
    del run_app.bat
    echo - run_app.bat eliminado
)

if exist .temp (
    rmdir /s /q .temp
    echo - Carpeta .temp eliminada
)

echo.
echo Limpieza completada!
echo Ahora puedes subir el repositorio a GitHub y desplegarlo en Streamlit Cloud.
echo Ver DEPLOY_GUIDE.md para instrucciones detalladas.
echo.

pause
