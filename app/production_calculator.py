import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class ProductionCalculator:
    """
    Class to calculate production requirements based on inventory and customer requirements
    """
    def __init__(self, inventory_df, requirements_df, reference_df):
        self.inventory_df = inventory_df
        self.requirements_df = requirements_df
        self.reference_df = reference_df
    
    def get_available_inventory(self, part_number):
        """
        Get available inventory for a specific part number
        """
        if self.inventory_df.empty or 'part_number' not in self.inventory_df.columns:
            return 0
            
        part_inventory = self.inventory_df[self.inventory_df['part_number'] == part_number]
        
        if part_inventory.empty:
            return 0
            
        # If status column exists, filter by available status
        if 'status' in part_inventory.columns:
            available = part_inventory[part_inventory['status'] == 'Disponible']['quantity'].sum() 
        else:
            # If no status column, assume all inventory is available
            available = part_inventory['quantity'].sum()
            
        return available
        
    def get_weekly_requirement(self, part_number):
        """
        Get weekly requirement for a specific part number
        """
        if self.requirements_df.empty or 'part_number' not in self.requirements_df.columns:
            return 0
            
        part_req = self.requirements_df[self.requirements_df['part_number'] == part_number]
        
        if part_req.empty or 'weekly_requirement' not in part_req.columns:
            return 0
            
        return part_req['weekly_requirement'].sum()
    
    def get_shipping_days(self, part_number):
        """
        Get shipping days for a specific part number
        Returns list of day numbers (1=Monday, 7=Sunday)
        """
        if self.requirements_df.empty or 'part_number' not in self.requirements_df.columns:
            return []
            
        part_req = self.requirements_df[self.requirements_df['part_number'] == part_number]
        
        if part_req.empty or 'shipping_days' not in part_req.columns:
            return []
            
        # Convert to list if it's not already
        days = part_req['shipping_days'].tolist()
        # Flatten the list if it contains lists
        flat_days = []
        for day in days:
            if isinstance(day, list):
                flat_days.extend(day)
            else:
                flat_days.append(day)
                
        return sorted(list(set(flat_days)))  # Return unique sorted days
    
    def get_part_reference(self, part_number):
        """
        Get reference data for a specific part number
        """
        if self.reference_df.empty or 'part_number' not in self.reference_df.columns:
            return None
            
        part_ref = self.reference_df[self.reference_df['part_number'] == part_number]
        
        if part_ref.empty:
            return None
            
        return part_ref.iloc[0].to_dict()
    
    def calculate_production_needs(self, part_number):
        """
        Calculate production needs for a specific part number
        Returns a dictionary with containers needed, pieces to produce, etc.
        """
        # Get reference data
        part_ref = self.get_part_reference(part_number)
        if part_ref is None:
            return {
                'error': 'Part reference data not found',
                'containers_needed': 0,
                'pieces_to_produce': 0,
                'production_time_hours': 0,
                'shifts_needed': 0
            }
            
        # Get std_pack and cycle_time
        std_pack = part_ref.get('std_pack', 0)
        cycle_time = part_ref.get('cycle_time', 0)
        
        if std_pack <= 0:
            return {
                'error': 'Invalid std_pack value',
                'containers_needed': 0,
                'pieces_to_produce': 0,
                'production_time_hours': 0,
                'shifts_needed': 0
            }
        
        # Get available inventory
        available_inventory = self.get_available_inventory(part_number)
        
        # Get weekly requirement
        weekly_req = self.get_weekly_requirement(part_number)
        
        # Calculate pieces to produce
        pieces_to_produce = max(0, weekly_req - available_inventory)
        
        # Calculate containers needed
        containers_needed = np.ceil(pieces_to_produce / std_pack) if std_pack > 0 else 0
        containers_needed = int(containers_needed)  # Convert to integer
        
        # Calculate total pieces (could be more than required due to full containers)
        total_pieces = containers_needed * std_pack
        
        # Calculate production time
        production_time_hours = 0
        if cycle_time > 0:
            production_time_seconds = total_pieces * cycle_time
            production_time_hours = production_time_seconds / 3600
            
        # Calculate shifts needed (assuming 8 hour shifts)
        shifts_needed = production_time_hours / 8 if production_time_hours > 0 else 0
        
        # Get next shipping days
        shipping_days = self.get_shipping_days(part_number)
        
        today = datetime.now()
        today_weekday = today.weekday() + 1  # 1=Monday, 7=Sunday
        
        next_shipping_dates = []
        if shipping_days:
            # Find the next shipping dates (up to 14 days in advance)
            for i in range(14):
                check_date = today + timedelta(days=i)
                check_weekday = check_date.weekday() + 1  # 1=Monday, 7=Sunday
                if check_weekday in shipping_days:
                    next_shipping_dates.append(check_date.strftime('%Y-%m-%d'))
                if len(next_shipping_dates) >= 3:  # Get max 3 next dates
                    break
        
        return {
            'part_number': part_number,
            'available_inventory': available_inventory,
            'weekly_requirement': weekly_req,
            'pieces_to_produce': pieces_to_produce,
            'containers_needed': containers_needed,
            'total_pieces': total_pieces,
            'production_time_hours': production_time_hours,
            'shifts_needed': shifts_needed,
            'shipping_days': shipping_days,
            'next_shipping_dates': next_shipping_dates,
            'std_pack': std_pack,
            'cycle_time': cycle_time
        }

# Example usage
if __name__ == "__main__":
    # Create sample dataframes
    inventory_df = pd.DataFrame({
        'part_number': ['ABC123', 'XYZ789'],
        'quantity': [500, 200],
        'status': ['Disponible', 'Disponible']
    })
    
    requirements_df = pd.DataFrame({
        'part_number': ['ABC123', 'XYZ789'],
        'weekly_requirement': [1000, 400],
        'shipping_days': [[1, 3, 5], [2, 4]]  # Monday, Wednesday, Friday for ABC123; Tuesday, Thursday for XYZ789
    })
    
    reference_df = pd.DataFrame({
        'part_number': ['ABC123', 'XYZ789'],
        'std_pack': [100, 50],
        'cycle_time': [30, 45],  # seconds
        'color': ['Negro', 'Gris'],
        'description': ['Moldura lateral', 'Sello puerta']
    })
    
    # Create calculator
    calculator = ProductionCalculator(inventory_df, requirements_df, reference_df)
    
    # Calculate production needs
    result = calculator.calculate_production_needs('ABC123')
    
    print("Production needs calculation result:")
    for key, value in result.items():
        print(f"{key}: {value}")
