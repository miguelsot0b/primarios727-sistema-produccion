# Sistema de Producción Primarios 727

Esta aplicación Streamlit ayuda a planificar la producción basada en el inventario actual, requerimientos del cliente, y datos de referencia para piezas (std pack, tiempo de ciclo, etc).

## Características

- **Dashboard**: Visualiza la producción necesaria por número de parte
- **Inventario**: Gestión y visualización del inventario actual
- **Requerimientos**: Análisis de los requerimientos del cliente
- **Datos de Referencia**: Gestión de datos como std pack, tiempo de ciclo, color, etc.
- **Integración en tiempo real con Google Drive**: Los datos de inventario y requerimientos se leen directamente desde Google Drive, asegurando información siempre actualizada

## Demo en vivo

La aplicación está disponible en Streamlit Cloud: [https://primarios727-sistema-produccion.streamlit.app](https://primarios727-sistema-produccion.streamlit.app)

## Instalación local

1. Instalar Python 3.8 o superior
2. Clonar el repositorio
3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Configurar credenciales de Google:
   - Crear un proyecto en [Google Cloud Console](https://console.cloud.google.com/)
   - Habilitar Google Drive API y Google Sheets API
   - Crear una cuenta de servicio y descargar las credenciales JSON
   - Guardar las credenciales como `app/credentials.json`
   - O configurar secretos en Streamlit (ver "Configuración de Streamlit Cloud")

## Uso local

Ejecutar la aplicación:

```bash
streamlit run streamlit_app.py
```

## Despliegue en Streamlit Cloud

1. Crear una cuenta en [Streamlit Cloud](https://streamlit.io/cloud)
2. Crear un nuevo repositorio en GitHub con este código
3. Conectar Streamlit Cloud a tu repositorio de GitHub
4. Configurar los secretos en Streamlit Cloud (ver siguiente sección)
5. Desplegar la aplicación

### Configuración de Streamlit Cloud

No se requieren credenciales especiales para esta aplicación. Simplemente despliega la app en Streamlit Cloud conectada a tu repositorio de GitHub.

Si deseas modificar las URLs de Google Drive para los archivos de inventario y requerimientos, puedes editar las siguientes variables en `streamlit_app.py`:

```python
# URLs de los archivos en Google Drive
INVENTORY_URL = "https://docs.google.com/spreadsheets/d/1Jt7ErfTB5BHKG6H5XFWW-FACaqsiQBLd/edit?usp=sharing&ouid=108358405466089911607&rtpof=true&sd=true"
REQUIREMENTS_URL = "https://drive.google.com/file/d/1TxKmxwy8QnUnTQTee77LgyooR_Fq1AGu/view?usp=drive_link"
```

**Importante**: Asegúrate de que los archivos de Google Drive estén configurados con acceso público (al menos para lectura) o con acceso para "Cualquier persona con el enlace".

## Estructura de Datos

La aplicación utiliza tres conjuntos de datos:

1. **Inventario** (Google Drive): 
   - Contiene el inventario actual y su estado
   - Se descarga automáticamente desde Google Drive
   - Columnas: part_number, quantity, status, location, etc.

2. **Requerimientos** (Google Drive):
   - Contiene los requerimientos del cliente
   - Se descarga automáticamente desde Google Drive
   - Columnas: part_number, weekly_requirement, shipping_days, etc.

3. **Datos de Referencia** (CSV en el repositorio):
   - Contiene información de referencia sobre las piezas
   - Se incluye directamente en el repositorio como CSV
   - Se puede modificar desde la aplicación
   - Columnas: part_number, std_pack, cycle_time, color, description, machine, location, notes

## Actualización de datos

- Los archivos de Google Drive (inventario y requerimientos) se descargan automáticamente cada 5 minutos para mantenerse actualizados
- El archivo de referencia se incluye en el repositorio y puede ser modificado desde la aplicación
- No se requieren credenciales de Google, ya que la descarga se hace directamente usando la API pública

## Estructura del Proyecto

```
primarios727-sistema-produccion/
│
├── app/
│   ├── production_calculator.py   # Cálculos de producción
│   ├── reference_data.py          # Gestión de datos de referencia
│   └── google_drive_reader.py     # Descargador de Google Drive
│
├── data/
│   └── reference/
│      └── reference_data.csv      # Datos de referencia (incluidos en el repositorio)
│
├── .streamlit/
│   └── config.toml                # Configuración de Streamlit
│
├── requirements.txt               # Dependencias
├── setup.sh                       # Configuración para Streamlit Cloud
├── streamlit_app.py               # Punto de entrada principal
└── README.md                      # Documentación
```

## Mantenimiento

- Los datos de inventario y requerimientos se actualizan automáticamente desde Google Drive
- Los datos de referencia pueden editarse directamente en la aplicación
- Para modificar las URLs de Google Drive, actualiza los secretos en Streamlit Cloud o el archivo `streamlit_app.py`
