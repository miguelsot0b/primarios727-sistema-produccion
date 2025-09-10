import pandas as pd
import os
import streamlit as st

class ReferenceData:
    """
    Class to manage reference data for parts
    """
    def __init__(self, file_path='data/reference/reference_data.csv'):
        # Establecer la ruta del archivo
        self.file_path = file_path
        self.in_memory = False
        
        # Verificar si el archivo existe, si no, intentar con el archivo incluido en el repositorio
        if not os.path.exists(self.file_path):
            # Intentar buscar en el directorio raíz del proyecto
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            alt_path = os.path.join(base_path, 'data', 'reference', 'reference_data.csv')
            
            if os.path.exists(alt_path):
                self.file_path = alt_path
            else:
                # Si no se encuentra, usaremos el almacenamiento en memoria
                self.in_memory = True
                self.file_path = None
                
                # Inicializar con un DataFrame vacío en la sesión de Streamlit
                if 'reference_data' not in st.session_state:
                    st.session_state['reference_data'] = pd.DataFrame({
                        'part_number': [],
                        'std_pack': [],
                        'cycle_time': [],
                        'color': [],
                        'description': [],
                        'machine': [],
                        'location': [],
                        'notes': []
                    })
        
        # Cargar datos
        self.data = self._load_data()
        
        # Si no hay datos y estamos usando un archivo, crear uno
        if self.data.empty and not self.in_memory and self.file_path:
            self._create_file()
    
    def _create_file(self):
        """Create a new reference file"""
        # Create directory if needed
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        # Create empty dataframe with correct structure
        df = pd.DataFrame({
            'part_number': [],
            'std_pack': [],
            'cycle_time': [],
            'color': [],
            'description': [],
            'machine': [],
            'location': [],
            'notes': []
        })
        
        # Save to CSV
        df.to_csv(self.file_path, index=False)
        self.data = df
    
    def _load_data(self):
        """Load reference data from file or session state"""
        if self.in_memory:
            # Usar los datos de la sesión de Streamlit
            return st.session_state['reference_data']
        else:
            # Cargar desde archivo
            try:
                # Verificar tipo de archivo
                if self.file_path.endswith('.csv'):
                    return pd.read_csv(self.file_path)
                elif self.file_path.endswith(('.xlsx', '.xls')):
                    return pd.read_excel(self.file_path)
                else:
                    raise ValueError(f"Formato de archivo no soportado: {self.file_path}")
            except Exception as e:
                print(f"Error loading reference data: {e}")
                return pd.DataFrame()
    
    def add_part(self, part_number, std_pack, cycle_time, color='', description='', 
                machine='', location='', notes=''):
        """Add a new part to the reference data"""
        new_part = pd.DataFrame({
            'part_number': [part_number],
            'std_pack': [std_pack],
            'cycle_time': [cycle_time],
            'color': [color],
            'description': [description],
            'machine': [machine],
            'location': [location],
            'notes': [notes]
        })
        
        # Add to existing data
        self.data = pd.concat([self.data, new_part], ignore_index=True)
        
        # Save changes
        self.save()
        return True
    
    def update_part(self, part_number, **kwargs):
        """Update an existing part in the reference data"""
        if part_number not in self.data['part_number'].values:
            return False
        
        # Update fields
        for key, value in kwargs.items():
            if key in self.data.columns:
                self.data.loc[self.data['part_number'] == part_number, key] = value
        
        # Save changes
        self.save()
        return True
    
    def delete_part(self, part_number):
        """Delete a part from the reference data"""
        if part_number not in self.data['part_number'].values:
            return False
        
        # Filter out the part
        self.data = self.data[self.data['part_number'] != part_number]
        
        # Save changes
        self.save()
        return True
    
    def get_part(self, part_number):
        """Get a specific part's data"""
        if part_number not in self.data['part_number'].values:
            return None
        
        return self.data[self.data['part_number'] == part_number].iloc[0].to_dict()
    
    def get_all_parts(self):
        """Get all parts data"""
        return self.data
    
    def save(self):
        """Save changes to the file or session state"""
        try:
            if self.in_memory:
                # Guardar en la sesión de Streamlit
                st.session_state['reference_data'] = self.data
            else:
                # Guardar en el archivo según su formato
                if self.file_path.endswith('.csv'):
                    self.data.to_csv(self.file_path, index=False)
                elif self.file_path.endswith(('.xlsx', '.xls')):
                    self.data.to_excel(self.file_path, index=False)
                else:
                    # Default to CSV
                    self.data.to_csv(self.file_path, index=False)
            return True
        except Exception as e:
            print(f"Error saving reference data: {e}")
            return False
    
    def import_from_dataframe(self, df, replace=False):
        """Import data from a DataFrame"""
        if replace:
            # Replace all data with the new DataFrame
            self.data = df.copy()
        else:
            # Update existing parts and add new ones
            for _, row in df.iterrows():
                part_number = row['part_number']
                
                # Check if part exists
                if part_number in self.data['part_number'].values:
                    # Update existing part
                    for col in df.columns:
                        if col in self.data.columns:
                            self.data.loc[self.data['part_number'] == part_number, col] = row[col]
                else:
                    # Add new part
                    new_row = pd.DataFrame([row])
                    self.data = pd.concat([self.data, new_row], ignore_index=True)
        
        # Save changes
        self.save()
        return True

# Example usage
if __name__ == "__main__":
    # Create reference data manager
    ref_data = ReferenceData()
    
    # Add sample parts
    ref_data.add_part(
        part_number="ABC123",
        std_pack=100,
        cycle_time=30,
        color="Negro",
        description="Moldura lateral",
        machine="Extrusora 1",
        location="Nave A"
    )
    
    ref_data.add_part(
        part_number="XYZ789",
        std_pack=50,
        cycle_time=45,
        color="Gris",
        description="Sello puerta",
        machine="Extrusora 2",
        location="Nave B"
    )
    
    print("Partes creadas con éxito!")
