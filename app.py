import streamlit as st
import pandas as pd
import numpy as np
import math
import re
from pathlib import Path
from datetime import datetime, timedelta
import time

# --------------------------
# Configuración de página
# --------------------------
st.set_page_config(
    page_title="Prioridad de Embarques - Contenedores",
    layout="wide"
)

# --------------------------
# Constantes
# --------------------------
PRP_URL = "https://drive.google.com/file/d/1TxKmxwy8QnUnTQTee77LgyooR_Fq1AGu/view?usp=drive_link"
LIVE_URL = "https://docs.google.com/spreadsheets/d/1Jt7ErfTB5BHKG6H5XFWW-FACaqsiQBLd/edit?usp=drive_link"
REF_PATH = "data/ref.csv"

# --------------------------
# Utilidades de URL y lectura de archivos
# --------------------------
def to_csv_url(url):
    """Convierte URLs de Google Drive y Sheets a URLs de descarga directa CSV."""
    # Drive file
    drive_match = re.search(r'https://drive\.google\.com/file/d/([^/]+)/view', url)
    if drive_match:
        file_id = drive_match.group(1)
        return f"https://drive.google.com/uc?id={file_id}"
    
    # Google Sheets
    sheets_match = re.search(r'https://docs\.google\.com/spreadsheets/d/([^/]+)/edit', url)
    if sheets_match:
        file_id = sheets_match.group(1)
        # Check if there's a gid parameter
        gid_match = re.search(r'gid=([^&]+)', url)
        gid_param = f"&gid={gid_match.group(1)}" if gid_match else ""
        return f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv{gid_param}"
    
    # Return original if no match
    return url

@st.cache_data(ttl=1800)
def read_csv_url(url, **kwargs):
    """Lee un CSV desde una URL, convirtiendo URLs de Google Drive/Sheets según sea necesario."""
    csv_url = to_csv_url(url)
    try:
        df = pd.read_csv(csv_url, **kwargs)
        return df, datetime.now()
    except Exception as e:
        st.error(f"Error al leer CSV desde URL: {e}")
        return pd.DataFrame(), datetime.now()

@st.cache_data()
def read_local_ref(path=REF_PATH):
    """Lee el archivo de referencia local con validaciones."""
    try:
        if not Path(path).exists():
            st.error(f"Archivo no encontrado: {path}")
            return pd.DataFrame(), datetime.now()
            
        df = pd.read_csv(path)
        
        # Validar columnas requeridas
        required_cols = ['partno', 'stdpack_min', 'stdpack_max', 'customer']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            st.warning(f"Columnas faltantes en archivo de referencia: {', '.join(missing_cols)}")
            if 'partno' in missing_cols:
                return pd.DataFrame(), datetime.now()
        
        return df, datetime.now()
    except Exception as e:
        st.error(f"Error al leer archivo local de referencia: {e}")
        return pd.DataFrame(), datetime.now()

# --------------------------
# Utilidades de procesamiento
# --------------------------
def detect_date_cols(df):
    """Detecta columnas de fecha con formato MM/DD/YYYY."""
    date_cols = []
    for col in df.columns:
        # Check if column name has MM/DD/YYYY format
        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', str(col)):
            date_cols.append(col)
    return date_cols

def to_numeric_series(s):
    """Convierte una serie a numérico, eliminando comas."""
    if s.dtype == 'object':
        return pd.to_numeric(s.astype(str).str.replace(',', ''), errors='coerce')
    return pd.to_numeric(s, errors='coerce')

def map_container_status(status):
    """Mapea el estado del contenedor a categorías estandarizadas."""
    status = str(status).upper()
    if any(keyword in status for keyword in ["CELL", "PISO", "FLOOR", "PROD"]):
        return "EN PISO"
    elif any(keyword in status for keyword in ["QUALITY", "HOLD", "QA", "CALIDAD"]):
        return "CALIDAD"
    elif any(keyword in status for keyword in ["DEFECT", "SCRAP", "SUSPECT", "DEFECTUOSO"]):
        return "POSIBLE DEFECTUOSO"
    else:
        return "OTROS"

def customer_priority(customer):
    """Asigna prioridad numérica al cliente."""
    if not customer or pd.isna(customer):
        return 999  # Lowest priority for missing values
    
    customer = str(customer).upper().strip()
    if "FORD" in customer:
        return 0  # Highest priority
    elif "MAGNA" in customer:
        return 1  # Second highest
    else:
        return 2  # Other customers

# --------------------------
# Carga y procesamiento de datos
# --------------------------
@st.cache_data(ttl=1800)
def load_ref(path=REF_PATH):
    """Carga y procesa el archivo de referencia."""
    df, timestamp = read_local_ref(path)
    
    if df.empty:
        return df, timestamp, []
    
    # Normalizar partno
    if 'partno' in df.columns:
        df['partno'] = df['partno'].astype(str).str.strip()
    
    # Calcular pack por parte
    if all(col in df.columns for col in ['stdpack_min', 'stdpack_max']):
        # Usar stdpack_max si es válido, sino stdpack_min
        df['pack'] = np.where(
            (df['stdpack_max'].notna()) & (df['stdpack_max'] > 0),
            df['stdpack_max'],
            np.where(
                (df['stdpack_min'].notna()) & (df['stdpack_min'] > 0),
                df['stdpack_min'],
                np.nan
            )
        )
        
        # Marcar partes con pack faltante
        df['pack_faltante'] = df['pack'].isna()
    else:
        df['pack'] = np.nan
        df['pack_faltante'] = True
    
    # Obtener lista única de partes
    parts_ref = df['partno'].unique().tolist() if 'partno' in df.columns else []
    
    return df, timestamp, parts_ref

@st.cache_data(ttl=1800)
def load_prp(url=PRP_URL):
    """Carga y procesa el archivo PRP."""
    df, timestamp = read_csv_url(url)
    
    if df.empty:
        return df, timestamp, []
    
    # Normalizar nombres de columnas
    df.columns = [str(col).strip() for col in df.columns]
    
    # Filtrar por "Customer Releases" de manera robusta
    demand_col = next((col for col in df.columns if 'demand type' in str(col).lower()), None)
    if demand_col:
        df = df[df[demand_col].astype(str).str.lower().str.strip() == "customer releases"]
    
    # Detectar columnas de fecha y convertir a numérico
    date_cols = detect_date_cols(df)
    for col in date_cols:
        df[col] = to_numeric_series(df[col])
    
    # Convertir columnas de inventario a numérico
    inv_cols = [col for col in df.columns if any(keyword in str(col).lower() for keyword in 
                ['inv fg', 'non useable inventory'])]
    for col in inv_cols:
        df[col] = to_numeric_series(df[col])
    
    # Normalizar Part No
    part_col = next((col for col in df.columns if 'part no' in str(col).lower()), None)
    if part_col:
        df[part_col] = df[part_col].astype(str).str.strip()
    
    # Detectar columna de cliente
    customer_col = next((col for col in df.columns if 'primary customer' in str(col).lower()), None)
    
    return df, timestamp, date_cols

@st.cache_data(ttl=1800)
def load_live(url=LIVE_URL):
    """Carga y procesa el archivo live inventory."""
    df, timestamp = read_csv_url(url)
    
    if df.empty:
        return df, timestamp
    
    # Normalizar nombres de columnas
    df.columns = [str(col).strip() for col in df.columns]
    
    # Detectar columna de Part No
    part_col = next((col for col in df.columns if 'part no' in str(col).lower() or 'part number' in str(col).lower()), None)
    if part_col:
        df[part_col] = df[part_col].astype(str).str.strip()
    else:
        st.warning("No se encontró columna de Part No en Live Inventory")
        
    # Detectar columna de cantidad
    qty_cols = ['Quantity', 'Qty', 'Part Count']
    qty_col = next((col for col in df.columns if any(q.lower() in str(col).lower() for q in qty_cols)), None)
    if qty_col:
        df[qty_col] = to_numeric_series(df[qty_col])
    else:
        st.warning("No se encontró columna de cantidad en Live Inventory")
    
    # Detectar columna de Container Status
    status_col = next((col for col in df.columns if 'container status' in str(col).lower() or 'status' in str(col).lower()), None)
    if status_col:
        df['Status_Mapped'] = df[status_col].apply(map_container_status)
    else:
        st.warning("No se encontró columna de Container Status en Live Inventory")
        df['Status_Mapped'] = "OTROS"
    
    return df, timestamp

@st.cache_data(ttl=1800)
def process_data(ref_df, prp_df, live_df, date_cols, parts_ref):
    """Procesa y combina los datos de ref, prp y live."""
    if ref_df.empty or prp_df.empty:
        return pd.DataFrame(), pd.DataFrame(), []
    
    # Identificar columnas clave en PRP
    part_col_prp = next((col for col in prp_df.columns if 'part no' in str(col).lower()), None)
    inv_fg_col = next((col for col in prp_df.columns if 'inv fg' in str(col).lower()), None)
    non_useable_col = next((col for col in prp_df.columns if 'non useable inventory' in str(col).lower()), None)
    customer_col_prp = next((col for col in prp_df.columns if 'primary customer' in str(col).lower()), None)
    
    if not all([part_col_prp, inv_fg_col, date_cols]):
        st.error("Faltan columnas críticas en PRP (Part No, Inv FG, fechas)")
        return pd.DataFrame(), pd.DataFrame(), []
    
    # Filtrar PRP a partes en ref
    prp_filtered = prp_df[prp_df[part_col_prp].str.upper().isin([p.upper() for p in parts_ref])].copy()
    if prp_filtered.empty:
        st.warning("No se encontraron partes de referencia en PRP")
        return pd.DataFrame(), pd.DataFrame(), []
    
    # Agregar por parte
    invfg_by_part = prp_filtered.groupby(part_col_prp)[inv_fg_col].first().reset_index()
    invfg_by_part.columns = ['Part No', 'InvFG_pzs']
    
    # Procesar demanda por día y parte
    demand_by_date = []
    for date_col in date_cols:
        if date_col in prp_filtered.columns:
            date_demand = prp_filtered.groupby(part_col_prp)[date_col].sum().reset_index()
            date_demand['Fecha'] = pd.to_datetime(date_col, format='%m/%d/%Y', errors='coerce')
            date_demand.columns = ['Part No', 'Demanda_pzs', 'Fecha']
            demand_by_date.append(date_demand)
    
    if not demand_by_date:
        st.warning("No se encontraron datos de demanda por fecha")
        return pd.DataFrame(), pd.DataFrame(), []
    
    demand_df = pd.concat(demand_by_date)
    
    # Procesar cliente desde PRP
    if customer_col_prp:
        customer_by_part = prp_filtered.groupby(part_col_prp)[customer_col_prp].apply(
            lambda x: x.mode()[0] if not x.mode().empty else None
        ).reset_index()
        customer_by_part.columns = ['Part No', 'Cliente_prp']
    else:
        customer_by_part = pd.DataFrame({'Part No': prp_filtered[part_col_prp].unique(), 'Cliente_prp': None})
    
    # Crear base de datos con inventario, demanda y cliente
    base = invfg_by_part.merge(customer_by_part, on='Part No', how='left')
    
    # Agregar información de pack desde ref
    ref_info = ref_df[['partno', 'pack', 'pack_faltante', 'customer']].rename(
        columns={'partno': 'Part No', 'customer': 'Customer_ref'}
    )
    base = base.merge(ref_info, on='Part No', how='left')
    
    # Definir cliente final (PRP o referencia)
    base['Cliente'] = base['Cliente_prp'].combine_first(base['Customer_ref'])
    
    # Procesar live inventory si existe
    nonusable_df = pd.DataFrame()
    if not live_df.empty:
        part_col_live = next((col for col in live_df.columns if 'part no' in str(col).lower() or 'part number' in str(col).lower()), None)
        qty_col = next((col for col in live_df.columns if any(q.lower() in str(col).lower() for q in ['quantity', 'qty', 'part count'])), None)
        
        if part_col_live and qty_col and 'Status_Mapped' in live_df.columns:
            # Sumar por parte y categoría
            live_summary = live_df.groupby([part_col_live, 'Status_Mapped'])[qty_col].sum().reset_index()
            live_summary.columns = ['Part No', 'Categoria', 'Cantidad_pzs']
            
            # Pivotar para obtener columnas por categoría
            nonusable_df = live_summary.pivot_table(
                index='Part No',
                columns='Categoria',
                values='Cantidad_pzs',
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            
            # Asegurar todas las categorías estén presentes
            for cat in ['EN PISO', 'CALIDAD', 'POSIBLE DEFECTUOSO', 'OTROS']:
                if cat not in nonusable_df.columns:
                    nonusable_df[cat] = 0
            
            # Calcular contenedores en piso
            nonusable_df = nonusable_df.merge(base[['Part No', 'pack']], on='Part No', how='left')
            nonusable_df['En piso (cont)'] = np.floor(nonusable_df['EN PISO'] / nonusable_df['pack']).fillna(0)
            
            # Calcular suma total y comparar con PRP si está disponible
            nonusable_df['Suma_live'] = nonusable_df['EN PISO'] + nonusable_df['CALIDAD'] + \
                                      nonusable_df['POSIBLE DEFECTUOSO'] + nonusable_df['OTROS']
            
            if non_useable_col:
                nonusable_prp = prp_filtered.groupby(part_col_prp)[non_useable_col].first().reset_index()
                nonusable_prp.columns = ['Part No', 'NonUsable_prp']
                nonusable_df = nonusable_df.merge(nonusable_prp, on='Part No', how='left')
                nonusable_df['Δ'] = nonusable_df['NonUsable_prp'] - nonusable_df['Suma_live']
    
    return base, demand_df, nonusable_df

@st.cache_data(ttl=1800)
def compute_shortages(base_df, demand_df, date_range):
    """Calcula faltantes y contenedores a producir."""
    if base_df.empty or demand_df.empty or not date_range:
        return pd.DataFrame()
    
    # Filtrar por rango de fechas
    start_date, end_date = date_range
    demand_filtered = demand_df[(demand_df['Fecha'] >= start_date) & (demand_df['Fecha'] <= end_date)]
    
    if demand_filtered.empty:
        return pd.DataFrame()
    
    # Merge base con demanda
    result = demand_filtered.merge(base_df, on='Part No', how='left')
    
    # Calcular faltante
    result['Faltante_pzs'] = np.maximum(0, result['Demanda_pzs'] - result['InvFG_pzs'])
    
    # Calcular contenedores a producir
    def safe_ceil_division(x, y):
        if pd.isna(y) or y == 0:
            return np.nan
        return math.ceil(x / y) if x > 0 else 0
    
    result['Contenedores_a_producir'] = result.apply(
        lambda row: safe_ceil_division(row['Faltante_pzs'], row['pack']),
        axis=1
    )
    
    # Identificar partes con faltantes
    part_has_shortage = result[result['Faltante_pzs'] > 0].groupby('Part No')['Fecha'].min().reset_index()
    part_has_shortage.columns = ['Part No', 'Primera_fecha_faltante']
    
    # Merge back
    result = result.merge(part_has_shortage, on='Part No', how='left')
    result['tiene_faltante'] = result['Primera_fecha_faltante'].notna()
    
    return result

@st.cache_data(ttl=1800)
def build_priority(shortage_df):
    """Construye la tabla priorizada."""
    if shortage_df.empty:
        return pd.DataFrame()
    
    # Crear columna de prioridad de cliente
    shortage_df['cliente_priority'] = shortage_df['Cliente'].apply(customer_priority)
    
    # Ordenar por prioridad
    priority_df = shortage_df.sort_values(
        by=['tiene_faltante', 'cliente_priority', 'Contenedores_a_producir', 'Fecha'],
        ascending=[False, True, False, True]
    )
    
    return priority_df

def render_sequence(priority_df, date):
    """Genera secuencia de producción por día."""
    if priority_df.empty:
        return "No hay datos para este día."
    
    day_df = priority_df[priority_df['Fecha'] == date].copy()
    if day_df.empty:
        return "No hay datos para este día."
    
    # Ordenar para secuencia: primero FORD, luego por contenedores descendente
    day_df['es_ford'] = day_df['Cliente'].str.contains('FORD', case=False, na=False)
    day_df = day_df.sort_values(by=['es_ford', 'Contenedores_a_producir'], ascending=[False, False])
    
    # Generar secuencia
    sequence = []
    for _, row in day_df.iterrows():
        if row['Contenedores_a_producir'] > 0:
            sequence.append(
                f"{int(row['Contenedores_a_producir'])} contenedores de {row['Part No']} ({row['Cliente']})"
            )
    
    if not sequence:
        return "No hay contenedores a producir para este día."
    
    return " → ".join(sequence)

# --------------------------
# UI
# --------------------------
def main():
    st.title("Prioridad de Embarques - Contenedores")
    
    # Sidebar
    st.sidebar.header("Configuración")
    
    # Botón de refrescar
    if st.sidebar.button("Refrescar ahora"):
        st.cache_data.clear()
        st.experimental_rerun()
    
    # Cargar datos
    ref_df, ref_timestamp, parts_ref = load_ref()
    prp_df, prp_timestamp, date_cols = load_prp()
    live_df, live_timestamp = load_live()
    
    # Mostrar timestamps de actualización
    st.sidebar.subheader("Última actualización")
    st.sidebar.info(f"Referencia: {ref_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    st.sidebar.info(f"PRP: {prp_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    st.sidebar.info(f"Live Inventory: {live_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Configuración de semáforo
    semaforo_threshold = st.sidebar.number_input(
        "Umbral de semáforo (contenedores para rojo)",
        min_value=1,
        value=3,
        step=1
    )
    
    # Procesar datos si están disponibles
    if not ref_df.empty and not prp_df.empty and date_cols:
        base_df, demand_df, nonusable_df = process_data(ref_df, prp_df, live_df, date_cols, parts_ref)
        
        if not base_df.empty and not demand_df.empty:
            # Selector de rango de fechas
            fechas_disponibles = sorted(demand_df['Fecha'].unique())
            if fechas_disponibles:
                fecha_inicio_default = fechas_disponibles[0]
                fecha_fin_default = fecha_inicio_default + timedelta(days=13)
                
                date_range = st.sidebar.date_input(
                    "Rango de fechas",
                    [fecha_inicio_default, min(fecha_fin_default, fechas_disponibles[-1])],
                    min_value=fechas_disponibles[0],
                    max_value=fechas_disponibles[-1]
                )
                
                # Validar rango de fechas
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start_date, end_date = date_range
                    
                    # Calcular faltantes
                    shortages_df = compute_shortages(base_df, demand_df, (start_date, end_date))
                    
                    if not shortages_df.empty:
                        # Construir prioridad
                        priority_df = build_priority(shortages_df)
                        
                        # Mostrar tabla de prioridad
                        st.subheader("Tabla de prioridad de embarques")
                        
                        # Columnas a mostrar
                        display_cols = [
                            'Fecha', 'Part No', 'Cliente', 'InvFG_pzs', 'Demanda_pzs',
                            'Faltante_pzs', 'pack', 'Contenedores_a_producir'
                        ]
                        
                        # Función para color de semáforo
                        def highlight_row(row):
                            contenedores = row['Contenedores_a_producir']
                            if pd.isna(contenedores):
                                return [''] * len(display_cols)
                            
                            if contenedores == 0:
                                color = 'green'
                            elif contenedores < semaforo_threshold:
                                color = 'yellow'
                            else:
                                color = 'red'
                            
                            return [f'background-color: {color}; opacity: 0.3'] * len(display_cols)
                        
                        # Aplicar estilo
                        display_df = priority_df[display_cols].copy()
                        display_df['Fecha'] = display_df['Fecha'].dt.strftime('%Y-%m-%d')
                        
                        # Formatear tabla
                        styled_df = display_df.style.apply(highlight_row, axis=1)
                        st.dataframe(styled_df)
                        
                        # Secuencia por día
                        st.subheader("Secuencia para el piso")
                        unique_dates = sorted(priority_df['Fecha'].unique())
                        
                        for date in unique_dates:
                            with st.expander(f"**{date.strftime('%Y-%m-%d')}**"):
                                st.markdown(render_sequence(priority_df, date))
                        
                        # Desglose de Non-Usable
                        if not nonusable_df.empty:
                            st.subheader("Desglose de No-Usable")
                            
                            nonusable_display = nonusable_df[[
                                'Part No', 'EN PISO', 'En piso (cont)', 'CALIDAD', 
                                'POSIBLE DEFECTUOSO', 'OTROS'
                            ]]
                            
                            if 'NonUsable_prp' in nonusable_df.columns:
                                nonusable_display = nonusable_display.merge(
                                    nonusable_df[['Part No', 'NonUsable_prp', 'Suma_live', 'Δ']],
                                    on='Part No',
                                    how='left'
                                )
                            
                            st.dataframe(nonusable_display)
                        
                        # Botón de descarga
                        csv = priority_df.to_csv(index=False)
                        st.download_button(
                            label="Descargar plan (CSV)",
                            data=csv,
                            file_name="plan_embarques.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("No se encontraron datos para el rango de fechas seleccionado.")
                else:
                    st.warning("Por favor selecciona un rango de fechas válido.")
            else:
                st.warning("No se encontraron fechas en los datos de demanda.")
        else:
            st.error("No se pudieron procesar los datos correctamente.")
    else:
        st.error("Faltan datos críticos para el procesamiento.")

if __name__ == "__main__":
    main()
