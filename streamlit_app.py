import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
import time

# Añadir la carpeta de la aplicación al path
app_path = Path(__file__).parent / "app"
sys.path.append(str(app_path))

# Importar nuestros módulos personalizados
try:
    from production_calculator import ProductionCalculator
    from reference_data import ReferenceData
    from google_drive_reader import download_file_from_drive, extract_file_id_from_url, read_file
except ImportError as e:
    st.error(f"Error al importar módulos: {e}")

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Producción Primarios 727",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Título de la aplicación
st.title("Sistema de Producción Primarios 727")

# URLs de los archivos en Google Drive
INVENTORY_URL = "https://docs.google.com/spreadsheets/d/1Jt7ErfTB5BHKG6H5XFWW-FACaqsiQBLd/edit?usp=sharing&ouid=108358405466089911607&rtpof=true&sd=true"
REQUIREMENTS_URL = "https://drive.google.com/file/d/1TxKmxwy8QnUnTQTee77LgyooR_Fq1AGu/view?usp=drive_link"

# Crear carpeta para archivos temporales
os.makedirs('.temp', exist_ok=True)

# Función para cargar datos de inventario desde Google Drive
@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_inventory_data():
    try:
        inventory_id = extract_file_id_from_url(INVENTORY_URL)
        if not inventory_id:
            st.warning("No se pudo extraer el ID del archivo de inventario.")
            return pd.DataFrame()
        
        # Descargar archivo
        file_path = os.path.join('.temp', 'inventory.xlsx')
        if download_file_from_drive(inventory_id, file_path, force_download=True):
            # Leer el archivo descargado
            df = read_file(file_path)
            return df
        else:
            st.warning("No se pudo descargar el archivo de inventario.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar datos de inventario: {e}")
        return pd.DataFrame()

# Función para cargar datos de requerimientos desde Google Drive
@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_requirements_data():
    try:
        requirements_id = extract_file_id_from_url(REQUIREMENTS_URL)
        if not requirements_id:
            st.warning("No se pudo extraer el ID del archivo de requerimientos.")
            return pd.DataFrame()
        
        # Descargar archivo
        file_path = os.path.join('.temp', 'requirements.xlsx')
        if download_file_from_drive(requirements_id, file_path, force_download=True):
            # Leer el archivo descargado
            df = read_file(file_path)
            return df
        else:
            st.warning("No se pudo descargar el archivo de requerimientos.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar datos de requerimientos: {e}")
        return pd.DataFrame()

# Función para cargar datos de referencia desde el repositorio
@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_reference_data():
    try:
        # Usar el archivo CSV incluido en el repositorio
        ref_data = ReferenceData()
        df = ref_data.get_all_parts()
        return df
    except Exception as e:
        st.error(f"Error al cargar datos de referencia: {e}")
        return pd.DataFrame({
            'part_number': [],
            'std_pack': [],
            'cycle_time': [],
            'color': [],
            'description': [],
            'machine': [],
            'location': [],
            'notes': []
        })

# Barra lateral para navegación
st.sidebar.title("Navegación")
page = st.sidebar.radio("Seleccione una página:", ["Dashboard", "Inventario", "Requerimientos", "Datos de Referencia"])

# Mostrar última actualización
st.sidebar.write("---")
st.sidebar.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# Botón para recargar datos
if st.sidebar.button("🔄 Recargar Datos"):
    st.cache_data.clear()
    st.experimental_rerun()

# Cargar datos
with st.spinner("Cargando datos..."):
    inventory_df = load_inventory_data()
    requirements_df = load_requirements_data()
    reference_df = load_reference_data()

# Inicializar calculadora de producción
calculator = ProductionCalculator(inventory_df, requirements_df, reference_df)

# Verificar si se han cargado los datos correctamente
has_data = not (inventory_df.empty or requirements_df.empty or reference_df.empty)
if not has_data:
    st.warning("No se han podido cargar todos los datos necesarios. Por favor, revisa las conexiones a los archivos o actualiza los datos de referencia.")

# IMPORTAR EL CÓDIGO DE LAS PÁGINAS
# En una aplicación completa, este código se importaría o se incluiría aquí.
# Para simplificar, este ejemplo muestra una versión básica de cada página.

# Dashboard page
if page == "Dashboard":
    st.header("Dashboard de Producción")
    
    if has_data:
        # Ejemplo de dashboard simple
        st.write("### Resumen de Producción")
        
        # Muestra algunos números de parte para seleccionar
        part_numbers = reference_df['part_number'].unique().tolist()
        selected_part = st.selectbox("Seleccione un número de parte:", part_numbers)
        
        if selected_part:
            # Usa el calculador para obtener datos
            production_data = calculator.calculate_production_needs(selected_part)
            
            # Muestra métricas básicas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Inventario Disponible", production_data.get('available_inventory', 0))
            with col2:
                st.metric("Requerimiento", production_data.get('weekly_requirement', 0))
            with col3:
                st.metric("A Producir", production_data.get('pieces_to_produce', 0))
            
            # Muestra contenedores necesarios
            st.write(f"### Contenedores necesarios: {production_data.get('containers_needed', 0)}")
    else:
        st.info("No hay suficientes datos para mostrar el dashboard.")
    
elif page == "Inventario":
    st.header("Gestión de Inventario")
    
    if not inventory_df.empty:
        st.write("### Datos de Inventario")
        st.dataframe(inventory_df, use_container_width=True)
        
        # Muestra un gráfico básico si hay datos
        if 'part_number' in inventory_df.columns and 'quantity' in inventory_df.columns:
            st.write("### Inventario por Número de Parte")
            
            # Agrupa por número de parte
            part_inventory = inventory_df.groupby('part_number')['quantity'].sum().reset_index()
            
            # Crea un gráfico de barras
            fig = px.bar(
                part_inventory,
                x='part_number',
                y='quantity',
                title="Inventario por Número de Parte"
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No se pudieron cargar los datos de inventario. Verifica que el archivo en Google Drive esté disponible.")
        
        # Muestra un enlace al archivo
        st.write("[Ver archivo de inventario en Google Drive]({})".format(INVENTORY_URL))
    
elif page == "Requerimientos":
    st.header("Requerimientos del Cliente")
    
    if not requirements_df.empty:
        st.write("### Datos de Requerimientos")
        st.dataframe(requirements_df, use_container_width=True)
        
        # Muestra un gráfico básico si hay datos
        if 'part_number' in requirements_df.columns and 'weekly_requirement' in requirements_df.columns:
            st.write("### Requerimiento Semanal por Número de Parte")
            
            # Crea un gráfico de barras
            fig = px.bar(
                requirements_df,
                x='part_number',
                y='weekly_requirement',
                title="Requerimiento Semanal por Número de Parte"
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No se pudieron cargar los datos de requerimientos. Verifica que el archivo en Google Drive esté disponible.")
        
        # Muestra un enlace al archivo
        st.write("[Ver archivo de requerimientos en Google Drive]({})".format(REQUIREMENTS_URL))
    
elif page == "Datos de Referencia":
    st.header("Datos de Referencia")
    
    # Instancia de ReferenceData para manejar el CSV
    ref_data_manager = ReferenceData()
    
    # Crear pestañas
    tab1, tab2 = st.tabs(["Ver/Editar Datos", "Agregar Nuevo"])
    
    with tab1:
        if not reference_df.empty:
            st.write("### Datos de Referencia")
            
            # Editor de datos
            edited_df = st.data_editor(reference_df, use_container_width=True, num_rows="dynamic")
            
            # Botón para guardar
            if st.button("Guardar Cambios"):
                # Actualizar datos
                for index, row in edited_df.iterrows():
                    part_number = row['part_number']
                    
                    # Comprobar si existe
                    if part_number in reference_df['part_number'].values:
                        # Actualizar existente
                        ref_data_manager.update_part(
                            part_number,
                            std_pack=row.get('std_pack', 0),
                            cycle_time=row.get('cycle_time', 0),
                            color=row.get('color', ''),
                            description=row.get('description', ''),
                            machine=row.get('machine', ''),
                            location=row.get('location', ''),
                            notes=row.get('notes', '')
                        )
                    else:
                        # Añadir nuevo
                        ref_data_manager.add_part(
                            part_number=part_number,
                            std_pack=row.get('std_pack', 0),
                            cycle_time=row.get('cycle_time', 0),
                            color=row.get('color', ''),
                            description=row.get('description', ''),
                            machine=row.get('machine', ''),
                            location=row.get('location', ''),
                            notes=row.get('notes', '')
                        )
                
                st.success("Datos guardados exitosamente!")
                st.experimental_rerun()  # Recargar para mostrar los cambios
        else:
            st.info("No hay datos de referencia. Agrega datos en la pestaña 'Agregar Nuevo'.")
    
    with tab2:
        st.write("### Agregar Nuevo Número de Parte")
        
        # Formulario para agregar nuevo
        with st.form("add_part_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                part_number = st.text_input("Número de Parte*")
                description = st.text_input("Descripción")
                std_pack = st.number_input("Std Pack*", min_value=1, value=100)
                cycle_time = st.number_input("Tiempo de Ciclo (seg)*", min_value=0.1, value=30.0)
            
            with col2:
                color = st.text_input("Color")
                machine = st.text_input("Máquina")
                location = st.text_input("Ubicación")
                notes = st.text_area("Notas")
            
            submit = st.form_submit_button("Agregar")
            
            if submit and part_number:
                # Validar que no exista
                if part_number in reference_df['part_number'].values:
                    st.error(f"El número de parte {part_number} ya existe!")
                else:
                    # Agregar nuevo
                    ref_data_manager.add_part(
                        part_number=part_number,
                        std_pack=std_pack,
                        cycle_time=cycle_time,
                        color=color,
                        description=description,
                        machine=machine,
                        location=location,
                        notes=notes
                    )
                    st.success(f"Número de parte {part_number} agregado exitosamente!")
                    st.experimental_rerun()  # Recargar para mostrar los cambios

# Pie de página
st.markdown("---")
st.caption("Sistema de Producción Primarios 727 © 2025 | Datos de inventario y requerimientos actualizados desde Google Drive")
