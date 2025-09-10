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
    page_title="Próximos 3 Números de Parte a Producir",
    layout="wide"
)

# --------------------------
# CSS personalizado
# --------------------------
st.markdown("""
<style>
    /* Estilos generales */
    .main-title {
        font-size: 42px !important;
        text-align: center;
        color: #1E3A8A;
        padding: 20px;
        border-bottom: 4px solid #2563EB;
        margin-bottom: 25px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .part-number {
        font-weight: bold;
        color: #1E40AF;
        background-color: #DBEAFE;
        padding: 5px 10px;
        border-radius: 5px;
    }
    
    .container-count {
        font-size: 24px;
        font-weight: bold;
        color: #991B1B;
        background-color: #FEE2E2;
        padding: 5px 15px;
        border-radius: 10px;
        display: inline-block;
        margin: 5px 0;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    
    .priority-box {
        background-color: #F3F4F6;
        border-left: 5px solid #3B82F6;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .priority-1 {
        border-left-color: #DC2626;
    }
    
    .priority-2 {
        border-left-color: #F59E0B;
    }
    
    .priority-3 {
        border-left-color: #10B981;
    }
    
    .info-message {
        background-color: #EFF6FF;
        border: 1px solid #BFDBFE;
        padding: 15px;
        border-radius: 5px;
        margin: 25px 0;
        display: flex;
        align-items: center;
        font-size: 16px;
    }
    
    .icon-container {
        font-size: 24px;
        margin-right: 15px;
    }
    
    /* Mejorar tabla de datos */
    div[data-testid="stDataFrame"] {
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-radius: 10px;
        overflow: hidden;
    }
    
    .stDataFrame table {
        border-collapse: separate;
        border-spacing: 0;
    }
    
    .stDataFrame th {
        background-color: #1E40AF;
        color: white;
        font-weight: bold;
        text-transform: uppercase;
    }
    
    .stDataFrame tbody tr:hover {
        background-color: rgba(219, 234, 254, 0.5);
    }
    
    /* Mejorar sidebar */
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
        padding-top: 20px;
    }
    
    section[data-testid="stSidebar"] button {
        background-color: #2563EB;
        color: white;
        border-radius: 5px;
        padding: 10px 15px;
        font-weight: bold;
        border: none;
        box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2);
        transition: all 0.3s ease;
    }
    
    section[data-testid="stSidebar"] button:hover {
        background-color: #1D4ED8;
        box-shadow: 0 6px 8px rgba(29, 78, 216, 0.3);
    }
</style>
""", unsafe_allow_html=True)

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
            date_demand['Fecha'] = pd.to_datetime(date_col, format='%m/%d/%Y', errors='coerce').date()
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
    
    # Incluir descripción si está disponible
    if 'desc' in ref_df.columns:
        ref_info['Descripcion'] = ref_df['desc']
    else:
        ref_info['Descripcion'] = 'N/A'
        
    # Incluir rate si está disponible
    if 'rate' in ref_df.columns:
        ref_info['Rate'] = ref_df['rate']
    else:
        ref_info['Rate'] = 100  # Default rate si no está disponible
    
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
def compute_shortages(base_df, demand_df, date_range=None):
    """Calcula faltantes y contenedores a producir en orden cronológico para cubrir todos los embarques,
    optimizando la producción para eficiencia."""
    if base_df.empty or demand_df.empty:
        return pd.DataFrame()
    
    # Asegurar que todas las fechas sean del mismo tipo (datetime64[ns])
    demand_df['Fecha'] = pd.to_datetime(demand_df['Fecha'])
    
    # Ordenar por fecha para procesar en orden cronológico
    demand_df = demand_df.sort_values(by='Fecha')
    
    # Crear un diccionario para rastrear el inventario disponible por parte
    # Comenzamos con el inventario actual de cada parte
    current_inventory = {row['Part No']: row['InvFG_pzs'] for _, row in base_df.iterrows()}
    
    # Lista para almacenar los resultados
    shortage_results = []
    
    # Agrupar por número de parte para seguir la demanda acumulada
    part_grouped_demand = {}
    for _, row in demand_df.iterrows():
        part_no = row['Part No']
        date = row['Fecha']
        demand = row['Demanda_pzs']
        
        if part_no not in part_grouped_demand:
            part_grouped_demand[part_no] = []
            
        part_grouped_demand[part_no].append((date, demand))
    
    # Para cada parte, procesar sus embarques en secuencia
    for part_no, demands in part_grouped_demand.items():
        # Si la parte no está en nuestro inventario, continuamos
        if part_no not in current_inventory:
            continue
            
        # Obtener información de la parte desde base_df
        if part_no not in base_df['Part No'].values:
            continue
            
        part_info = base_df[base_df['Part No'] == part_no].iloc[0]
        inventory = current_inventory[part_no]
        pack = part_info['pack']
        
        # Calcular capacidad por turno
        rate = part_info['Rate'] if 'Rate' in part_info else 100
        capacity_pcs = rate / 100 * 22.5
        
        # Manejar casos especiales para pack
        valid_pack = False if pd.isna(pack) else (pack > 0)
        capacity_cont = 0 if not valid_pack else math.floor(capacity_pcs / pack)
        
        # Banderas para optimización
        is_first_shortage = True
        
        # Procesar cada embarque para esta parte
        for date, demand in demands:
            # Calcular faltante
            shortage = max(0, demand - inventory)
            
            # Si hay faltante, necesitamos producir
            if shortage > 0:
                # Calcular contenedores necesarios
                if pd.isna(pack) or pack <= 0:
                    containers = np.nan  # No podemos calcular contenedores sin pack
                else:
                    containers = math.ceil(shortage / pack)
                
                # Crear registro de faltante
                shortage_row = {
                    'Part No': part_no,
                    'Fecha_Embarque': date,
                    'Inventario_Actual': inventory,
                    'Demanda_pzs': demand,
                    'Faltante_pzs': shortage,
                    'pack': pack,
                    'Contenedores_a_producir': containers,
                    'Cliente': part_info['Cliente'],
                    'Descripcion': part_info['Descripcion'] if 'Descripcion' in part_info else 'N/A',
                    'Rate': rate,
                    'Capacidad_turno_cont': capacity_cont,
                    'Es_primer_faltante': is_first_shortage,  # Para priorizar faltantes inmediatos
                    'Siguiente_embarque': not is_first_shortage  # Para saber que es un embarque futuro
                }
                
                shortage_results.append(shortage_row)
                
                # Ya no es el primer faltante para esta parte
                is_first_shortage = False
                
                # Actualizar el inventario después de este embarque (lo dejamos en 0)
                inventory = 0
            else:
                # Actualizar el inventario restante después de este embarque
                inventory = inventory - demand
    
    # Convertir los resultados a DataFrame
    if not shortage_results:
        return pd.DataFrame()
    
    result = pd.DataFrame(shortage_results)
    
    # Agregar capacidad por turno
    if not result.empty:
        # Limitar la producción a la capacidad del turno
        result['Contenedores_a_producir_limitado'] = np.minimum(
            result['Contenedores_a_producir'].fillna(0), 
            result['Capacidad_turno_cont'].fillna(0)
        )
    
    return result

@st.cache_data(ttl=1800)
def build_priority(shortage_df):
    """Construye la tabla priorizada para cubrir embarques de manera eficiente:
    1. Primero cubrir los faltantes inmediatos
    2. Seguir con el mismo número de parte hasta cubrir el siguiente embarque
    3. Luego pasar a otras partes por orden de cliente y fecha"""
    if shortage_df.empty:
        return pd.DataFrame()
    
    # Crear columna de prioridad de cliente
    shortage_df['cliente_priority'] = shortage_df['Cliente'].apply(customer_priority)
    
    # Agregar columna de continuidad para mantener la misma parte
    # Agrupar por número de parte para crear un ID único de prioridad por parte
    part_priority = {}
    for i, part in enumerate(shortage_df['Part No'].unique()):
        part_priority[part] = i
    
    shortage_df['part_priority'] = shortage_df['Part No'].map(part_priority)
    
    # Primero los faltantes inmediatos (para embarque actual)
    # Luego ordenar para completar la misma parte (eficiencia)
    # Después por cliente y fecha para otros embarques
    if 'Es_primer_faltante' in shortage_df.columns:
        priority_df = shortage_df.sort_values(
            by=['Es_primer_faltante', 'part_priority', 'cliente_priority', 'Fecha_Embarque'],
            ascending=[False, True, True, True]
        )
    else:
        # Fallback a la ordenación básica si no tenemos la columna de optimización
        priority_df = shortage_df.sort_values(
            by=['cliente_priority', 'Fecha_Embarque', 'Part No'],
            ascending=[True, True, True]
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
    # Título con diseño mejorado
    st.markdown('<h1 class="main-title">📦 PRÓXIMOS 3 NÚMEROS DE PARTE A PRODUCIR 📦</h1>', unsafe_allow_html=True)
    
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
    
    # Sidebar con diseño mejorado
    st.sidebar.markdown("### 🕒 Información del Sistema")
    
    # Mostrar fecha y hora actual con mejor formato
    current_time = datetime.now().strftime('%d-%m-%Y %H:%M')
    st.sidebar.markdown(f"**Última actualización:**")
    st.sidebar.markdown(f"<div style='background-color: #DBEAFE; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;'>{current_time}</div>", unsafe_allow_html=True)
    
    # Separador visual
    st.sidebar.markdown("<hr>", unsafe_allow_html=True)
    
    # Logo o imagen (opcional)
    st.sidebar.markdown("### 🏭 Sistema de Producción")
    
    # Botón para actualizar datos con mejor estilo
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 Actualizar Datos Ahora"):
        st.cache_data.clear()
        st.experimental_rerun()
    
    # Procesar datos si están disponibles
    if not ref_df.empty and not prp_df.empty and date_cols:
        base_df, demand_df, nonusable_df = process_data(ref_df, prp_df, live_df, date_cols, parts_ref)
        
        if not base_df.empty and not demand_df.empty:
            # Convertir fechas
            demand_df['Fecha'] = pd.to_datetime(demand_df['Fecha'])
            
            # Definimos un horizonte de planeación fijo (60 días)
            dias_horizonte = 60
            
            # Mensaje simple
            st.sidebar.info("Plan de contenedores en orden cronológico")
            
            # Calcular faltantes para todos los embarques
            shortages_df = compute_shortages(base_df, demand_df)
            
            if not shortages_df.empty:
                # Construir prioridad
                priority_df = build_priority(shortages_df)
                
                # Dashboard simplificado
                # Eliminamos el encabezado del plan de producción ya que solo mostraremos los 5 próximos
                
                # Columnas a mostrar en el dashboard simplificado (con información para entender la secuencia)
                display_cols = [
                    'Part No', 
                    'Descripcion',
                    'Fecha_Embarque',  # Incluimos fecha para entender cuándo se necesita
                    'Contenedores_a_producir_limitado'  # Limitado por capacidad
                ]
                
                # Filtrar solo las filas con contenedores a producir
                display_df = priority_df[priority_df['Contenedores_a_producir_limitado'] > 0][display_cols].copy()
                
                # Formatear fechas para mejor visualización
                display_df['Fecha_Embarque'] = display_df['Fecha_Embarque'].dt.strftime('%d-%m-%Y')
                
                # Renombrar columnas para mejor visualización
                display_df.columns = [
                    'Número de Parte', 
                    'Descripción',
                    'Embarque',
                    'Contenedores a Producir'
                ]
                
                # Función para color de semáforo simplificado
                def highlight_row(row):
                    contenedores = row['Contenedores a Producir']
                    if pd.isna(contenedores):
                        return [''] * 3  # Solo tenemos 3 columnas ahora
                    
                    if contenedores == 0:
                        color = '#90EE90'  # Verde claro
                    else:
                        color = '#FFCCCC'  # Rojo claro
                    
                    return [f'background-color: {color}; font-weight: bold'] * 3
                
                # Aplicar estilo
                styled_df = display_df.style.apply(highlight_row, axis=1)
                
                # Mostrar solo los próximos 3 números de parte
                st.markdown("### 🚨 Prioridad de Producción 🚨")
                
                # Agrupar por número de parte y sumar los contenedores
                grouped_df = display_df.groupby(['Número de Parte', 'Descripción']).agg({
                    'Contenedores a Producir': 'sum'
                }).reset_index()
                
                # Ordenar por mayor número de contenedores primero
                grouped_df = grouped_df.sort_values('Contenedores a Producir', ascending=False)
                
                # Limitamos a los primeros 3 números de parte
                limited_df = grouped_df.head(3).copy()
                
                # Crear métricas para mostrar los datos de manera más visual
                if not limited_df.empty:
                    col1, col2, col3 = st.columns(3)
                    
                    # Mostrar cada parte en una columna con estilo
                    for idx, (_, row) in enumerate(limited_df.iterrows()):
                        with [col1, col2, col3][min(idx, 2)]:
                            part_no = row['Número de Parte']
                            description = row['Descripción']
                            containers = int(row['Contenedores a Producir'])
                            
                            st.markdown(f"""
                            <div class='priority-box priority-{idx+1}'>
                                <h3>Prioridad #{idx+1}</h3>
                                <p><span class='part-number'>{part_no}</span></p>
                                <p>{description}</p>
                                <div class='container-count'>📦 {containers} Contenedores</div>
                            </div>
                            """, unsafe_allow_html=True)
                
                # Mostrar también la tabla para tener los datos estructurados
                st.markdown("### 📋 Detalle de Producción")
                st.dataframe(limited_df[['Número de Parte', 'Descripción', 'Contenedores a Producir']].style.apply(highlight_row, axis=1), hide_index=True)
                
                # Instrucciones para operadores con iconos
                st.markdown("### 🔄 Secuencia de Producción")
                
                # Mensaje con iconos para operadores
                secuencia_texto = []
                
                for i, (_, row) in enumerate(limited_df.iterrows(), 1):
                    if i > 3:  # Limitar a solo 3 números de parte
                        break
                        
                    current_part = row['Número de Parte']
                    icon = "🔴" if i == 1 else "🟡" if i == 2 else "🟢"
                    
                    secuencia_texto.append(f"""
                    <div class='priority-box priority-{i}'>
                        <h4>{icon} Paso {i}</h4>
                        <p>Producir <span class='container-count'>{int(row['Contenedores a Producir'])}</span> contenedores de 
                        <span class='part-number'>{current_part}</span></p>
                        <p><em>{row['Descripción']}</em></p>
                    </div>
                    """)
                
                if secuencia_texto:
                    for texto in secuencia_texto:
                        st.markdown(texto, unsafe_allow_html=True)
                    
                    # Nota sobre actualización automática con icono
                    st.markdown("""
                    <div class='info-message'>
                        <div class='icon-container'>ℹ️</div>
                        <div>
                            <strong>Nota:</strong> Los datos se actualizan automáticamente cada 30 minutos. 
                            Use el botón <strong>🔄 Actualizar Datos Ahora</strong> en el panel lateral para forzar una actualización inmediata.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("No hay contenedores para producir.")
                
                # Botón de descarga
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="Descargar plan (CSV)",
                    data=csv,
                    file_name="plan_produccion.csv",
                    mime="text/csv"
                )
                
                # Información adicional colapsable
                with st.expander("Ver inventario en piso (No-Usable)"):
                    if not nonusable_df.empty:
                        nonusable_display = nonusable_df[['Part No', 'EN PISO', 'En piso (cont)']]
                        nonusable_display.columns = ['Número de Parte', 'Piezas en Piso', 'Contenedores en Piso']
                        st.dataframe(nonusable_display)
                    else:
                        st.info("No hay información de inventario en piso disponible.")
            else:
                st.warning("No se encontraron requerimientos para producir.")
        else:
            st.error("No se pudieron procesar los datos correctamente.")
    else:
        st.error("Faltan datos críticos para el procesamiento.")

# Pie de página con información de versión
def footer():
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style='position: fixed; bottom: 0; left: 0; right: 0; background-color: #F8FAFC; padding: 10px; text-align: center; border-top: 1px solid #E2E8F0; font-size: 12px; color: #64748B;'>
        Sistema de Producción v1.2 | © 2025 | Última actualización: 10-09-2025
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
    footer()
