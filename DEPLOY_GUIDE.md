# Guía para desplegar en Streamlit Cloud

## Pasos para desplegar la aplicación

1. **Crear una cuenta en Streamlit Cloud** (si aún no tienes una)
   - Visita [https://streamlit.io/cloud](https://streamlit.io/cloud)
   - Regístrate con tu cuenta de GitHub

2. **Subir este repositorio a GitHub**
   - Crea un nuevo repositorio en GitHub
   - Sube todos los archivos importantes a ese repositorio

3. **Conectar Streamlit Cloud a tu repositorio**
   - En el dashboard de Streamlit Cloud, haz clic en "New app"
   - Selecciona tu repositorio
   - En "Main file path", escribe: `streamlit_app.py`
   - Haz clic en "Deploy"

## Archivos esenciales para el despliegue

Solo estos archivos son necesarios para Streamlit Cloud:

```
primarios727-sistema-produccion/
│
├── streamlit_app.py       # Punto de entrada principal (IMPORTANTE)
├── requirements.txt       # Dependencias para instalar
│
├── app/
│   ├── production_calculator.py   # Cálculos de producción
│   ├── reference_data.py          # Gestión de datos de referencia
│   └── google_drive_reader.py     # Descargador de Google Drive
│
├── data/
│   └── reference/
│      └── reference_data.csv      # Datos de referencia (incluido en el repositorio)
│
├── .streamlit/            # (Opcional) Configuración de apariencia
│   └── config.toml        
│
└── README.md              # Documentación
```

## Archivos no necesarios en Streamlit Cloud

Estos archivos son solo para desarrollo local y no son necesarios en el repositorio:

- `run_app.bat` y `run_app.ps1` - Scripts para ejecutar localmente
- `app/download_data.py` - Ya no se usa, ahora descargamos en streamlit_app.py
- `app/app.py` - Ya no es el punto de entrada principal
- `.venv/` o cualquier entorno virtual
- Archivos temporales como `.temp/` 

## Verificación

Después del despliegue, asegúrate de que:

1. La aplicación se cargue correctamente
2. Los datos se descarguen desde Google Drive 
3. Los datos de referencia estén disponibles y sean modificables

Si hay errores, revisa los logs en Streamlit Cloud para diagnosticar el problema.
