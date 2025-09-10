import pandas as pd
import streamlit as st
import os
from io import BytesIO
import requests
import time

# Función para extraer el ID de archivo de una URL de Google Drive
def extract_file_id_from_url(url):
    """
    Extrae el ID de archivo de una URL de Google Drive
    
    Args:
        url (str): URL del archivo de Google Drive o Google Sheets
        
    Returns:
        str: ID del archivo o None si no se puede extraer
    """
    # Format: https://drive.google.com/file/d/{FILE_ID}/view...
    if '/file/d/' in url:
        file_id = url.split('/file/d/')[1].split('/')[0]
        return file_id
    # Format: https://docs.google.com/spreadsheets/d/{FILE_ID}/edit...
    elif '/spreadsheets/d/' in url:
        file_id = url.split('/spreadsheets/d/')[1].split('/')[0]
        return file_id
    else:
        return None

# Función para descargar un archivo desde Google Drive
def download_file_from_drive(file_id, destination_path, force_download=False):
    """
    Descarga un archivo desde Google Drive y lo guarda localmente
    
    Args:
        file_id (str): ID del archivo en Google Drive
        destination_path (str): Ruta donde guardar el archivo
        force_download (bool): Si True, descarga incluso si el archivo ya existe
        
    Returns:
        bool: True si se descargó correctamente, False en caso contrario
    """
    try:
        # Si el archivo ya existe y no se fuerza la descarga, no hacer nada
        if os.path.exists(destination_path) and not force_download:
            return True
            
        # Asegurarse de que la carpeta destino exista
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        # URL para la API de exportación de Google Drive
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        # Crea una sesión para manejar la descarga
        session = requests.Session()
        response = session.get(url, stream=True)
        
        # Comprueba si el archivo es grande y requiere confirmación
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={value}"
                response = session.get(url, stream=True)
        
        # Guarda el contenido en el archivo destino
        with open(destination_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=32768):
                if chunk:
                    f.write(chunk)
                    
        return True
        
    except Exception as e:
        st.error(f"Error al descargar archivo de Google Drive: {e}")
        return False
        
# Función para leer un archivo Excel o CSV
def read_file(file_path, file_type=None):
    """
    Lee un archivo Excel o CSV y lo devuelve como DataFrame
    
    Args:
        file_path (str): Ruta del archivo a leer
        file_type (str): Tipo de archivo ('excel' o 'csv'). Si es None, se detecta por la extensión
        
    Returns:
        DataFrame: DataFrame de pandas con los datos del archivo
    """
    try:
        if not os.path.exists(file_path):
            return pd.DataFrame()
            
        # Determinar el tipo de archivo por la extensión si no se especificó
        if file_type is None:
            if file_path.endswith('.csv'):
                file_type = 'csv'
            elif file_path.endswith(('.xlsx', '.xls')):
                file_type = 'excel'
            else:
                raise ValueError(f"Tipo de archivo no soportado: {file_path}")
        
        # Leer el archivo según su tipo
        if file_type == 'csv':
            return pd.read_csv(file_path)
        elif file_type == 'excel':
            return pd.read_excel(file_path)
        else:
            raise ValueError(f"Tipo de archivo no soportado: {file_type}")
            
    except Exception as e:
        st.error(f"Error al leer archivo {file_path}: {e}")
        return pd.DataFrame()

# Función para extraer el ID de archivo de una URL de Google Drive
def extract_file_id_from_url(url):
    """
    Extrae el ID de archivo de una URL de Google Drive
    
    Args:
        url (str): URL del archivo de Google Drive o Google Sheets
        
    Returns:
        str: ID del archivo o None si no se puede extraer
    """
    # Format: https://drive.google.com/file/d/{FILE_ID}/view...
    if '/file/d/' in url:
        file_id = url.split('/file/d/')[1].split('/')[0]
        return file_id
    # Format: https://docs.google.com/spreadsheets/d/{FILE_ID}/edit...
    elif '/spreadsheets/d/' in url:
        file_id = url.split('/spreadsheets/d/')[1].split('/')[0]
        return file_id
    else:
        return None

# Ejemplo de uso
if __name__ == "__main__":
    # URL del archivo de inventario (Google Sheet)
    inventory_url = "https://docs.google.com/spreadsheets/d/1Jt7ErfTB5BHKG6H5XFWW-FACaqsiQBLd/edit?usp=sharing&ouid=108358405466089911607&rtpof=true&sd=true"
    inventory_id = extract_file_id_from_url(inventory_url)
    
    if inventory_id:
        print(f"ID de inventario: {inventory_id}")
        try:
            # Crear carpeta temporal si no existe
            os.makedirs("temp", exist_ok=True)
            
            # Descargar el archivo
            file_path = "temp/inventory.xlsx"
            if download_file_from_drive(inventory_id, file_path, force_download=True):
                # Leer el archivo descargado
                df = read_file(file_path, file_type="excel")
                print("Datos cargados correctamente:")
                print(df.head())
            else:
                print("Error al descargar el archivo")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("No se pudo extraer el ID del archivo.")
