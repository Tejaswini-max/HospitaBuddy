import os
import pandas as pd
import numpy as np
import logging
from pathlib import Path

def load_cssd_data():
    """
    Load CSSD planning data from the Excel file.
    Returns a dictionary with data from both sheets.
    """
    try:
        # Path to the Excel file in static/data
        excel_file = Path(__file__).parent.parent / "static" / "data" / "cssd_planning.xlsx"
        
        # Log the file path for debugging
        logging.info(f"Attempting to load Excel file from: {excel_file}")
        
        # Analyze Excel file structure first
        xls = pd.ExcelFile(excel_file, engine='openpyxl')
        logging.info(f"Excel file contains sheets: {xls.sheet_names}")
        
        # Read the first sheet (has both CSSD area and equipment data)
        sheet_df = pd.read_excel(excel_file, sheet_name=0, header=None, engine='openpyxl')
        
        # Find the row with "Hospital Bed Size" which contains bed ranges as column headers
        bed_size_row_idx = None
        for idx, row in sheet_df.iterrows():
            for col_idx, cell_value in enumerate(row):
                if isinstance(cell_value, str) and "Hospital Bed Size" in cell_value:
                    bed_size_row_idx = idx
                    break
            if bed_size_row_idx is not None:
                break
        
        if bed_size_row_idx is None:
            logging.error("Could not find 'Hospital Bed Size' row in Excel file")
            return create_mock_data()
            
        # Get the row with bed ranges (they are column headers)
        bed_ranges_row = sheet_df.iloc[bed_size_row_idx]
        
        # Find row with CSSD area requirements
        cssd_area_row = None
        for idx in range(bed_size_row_idx + 1, len(sheet_df)):
            row = sheet_df.iloc[idx]
            if isinstance(row[0], str) and "CSSD area Required" in row[0]:
                cssd_area_row = row
                break
                
        if cssd_area_row is None:
            logging.error("Could not find CSSD area requirements row in Excel file")
            return create_mock_data()
        
        # Find rows with autoclave details
        cylindrical_autoclave_row_idx = None
        rectangular_autoclave_row_idx = None
        bed_ranges_col = 0  # Default column index for bed ranges
        
        for idx in range(bed_size_row_idx + 1, len(sheet_df)):
            row = sheet_df.iloc[idx]
            if isinstance(row[0], str):
                if "Cyliendrical Autoclave" in row[0]:
                    cylindrical_autoclave_row_idx = idx
                elif "Reactangular Autoclave" in row[0]:
                    rectangular_autoclave_row_idx = idx
        
        # Find budget rows
        budget_min_row = None
        budget_max_row = None
        
        # Look for budget rows - specifically "Expected Tentative Budget"
        for idx in range(len(sheet_df)):
            if isinstance(sheet_df.iloc[idx, 0], str):
                if "Expected Tentative Budget" in sheet_df.iloc[idx, 0]:
                    budget_min_row = idx  # Budget row with "Minimum" values
                    budget_max_row = idx + 1  # Budget row with "Maximum" values
                    break
        
        logging.info(f"Found budget rows: min={budget_min_row}, max={budget_max_row}")
        
        # Process CSSD area data
        area_data = []
        autoclave_data = []
        
        # Find equipment rows
        equipment_rows = {}
        equipment_types = [
            "Cyliendrical Autoclave", "Reactangular Autoclave", "Vertical Autoclave", 
            "Flash Autoclave", "ETO", "Heat Sealing Machine", "ETO Packing Table",
            "Washer Disinfector", "Ultrasonic Cleaner", "Hot Air Ovan", 
            "Pass Box", "Storage Rack", "Open Trolly", "Close Trolly", "Work Table"
        ]
        
        # Create mapping for partial matches (typos in Excel) to standardized names
        equipment_mapping = {
            "Cyliendrical": "Cylindrical Autoclave",
            "Reactangular": "Rectangular Autoclave", 
            "Vertical Auto": "Vertical Autoclave",
            "Flash Auto": "Flash Autoclave",
            "ETO": "ETO Sterilizer",
            "Heat Seal": "Heat Sealing Machine",
            "Washer": "Washer Disinfector",
            "Ultrasonic": "Ultrasonic Cleaner",
            "Hot Air": "Hot Air Oven",
            "Pass Box": "Pass Box",
            "Storage": "Storage Rack",
            "Open Trolly": "Open Trolley",
            "Close Trolly": "Closed Trolley",
            "Work Table": "Work Table"
        }
        
        # Find row indices for all equipment types
        for idx in range(bed_size_row_idx + 1, len(sheet_df)):
            cell_value = sheet_df.iloc[idx, 0]
            if isinstance(cell_value, str):
                for equip_key, equip_standard_name in equipment_mapping.items():
                    if equip_key in cell_value:
                        equipment_rows[equip_standard_name] = idx
                        break
        
        logging.info(f"Found equipment rows: {equipment_rows}")
        
        # Start from column 2 (index 2) which has the first bed range
        # Skip "Parameter" in column 1
        for col_idx in range(2, len(bed_ranges_row)):
            bed_range = bed_ranges_row[col_idx]
            
            # Skip if not a valid bed range
            if not isinstance(bed_range, str) or not "-" in bed_range:
                continue
                
            try:
                # Extract min and max beds from range (e.g., "0-20" -> 0, 20)
                min_beds, max_beds = map(int, bed_range.split('-'))
                
                # Get CSSD area for this range
                cssd_area = cssd_area_row[col_idx]
                if pd.isna(cssd_area):
                    cssd_area = "Not specified"
                    
                # Process autoclave information
                autoclave_model = "Not specified"
                autoclave_qty = 0
                
                # Check cylindrical autoclave
                if cylindrical_autoclave_row_idx is not None:
                    cylindrical_spec = sheet_df.iloc[cylindrical_autoclave_row_idx][col_idx]
                    cylindrical_qty = sheet_df.iloc[cylindrical_autoclave_row_idx + 1][col_idx]
                    
                    if not pd.isna(cylindrical_spec) and not pd.isna(cylindrical_qty) and cylindrical_qty > 0:
                        autoclave_model = f"Cylindrical: {cylindrical_spec}"
                        autoclave_qty = cylindrical_qty
                
                # If no cylindrical, check rectangular autoclave
                if (autoclave_qty == 0 or pd.isna(autoclave_qty)) and rectangular_autoclave_row_idx is not None:
                    rectangular_spec = sheet_df.iloc[rectangular_autoclave_row_idx][col_idx]
                    rectangular_qty = sheet_df.iloc[rectangular_autoclave_row_idx + 1][col_idx]
                    
                    if not pd.isna(rectangular_spec) and not pd.isna(rectangular_qty) and rectangular_qty > 0:
                        if rectangular_spec != "Not Recommended":
                            autoclave_model = f"Rectangular: {rectangular_spec}"
                            autoclave_qty = rectangular_qty
                
                # Process all equipment for this bed range
                equipment_list = []
                
                for equip_type, row_idx in equipment_rows.items():
                    try:
                        # Equipment specification is in the main row
                        spec = sheet_df.iloc[row_idx][col_idx]
                        # Quantity is typically in the next row (QTY)
                        qty_idx = row_idx + 1
                        qty = sheet_df.iloc[qty_idx][col_idx] if qty_idx < len(sheet_df) else None
                        
                        # Skip if no spec or zero quantity
                        if pd.isna(spec) or pd.isna(qty) or str(spec).strip() == "0" or (isinstance(qty, (int, float)) and qty <= 0):
                            continue
                            
                        # Check for rate/price - typically two rows after the spec row
                        price_idx = row_idx + 2
                        unit_price = sheet_df.iloc[price_idx][col_idx] if price_idx < len(sheet_df) else None
                        
                        # Calculate total price if unit price exists
                        total_price = None
                        if not pd.isna(unit_price) and isinstance(unit_price, (int, float)) and isinstance(qty, (int, float)):
                            total_price = unit_price * qty
                        
                        equipment_list.append({
                            'name': equip_type,
                            'specification': str(spec),
                            'quantity': int(qty) if isinstance(qty, (int, float)) else str(qty),
                            'unit_price': int(unit_price) if isinstance(unit_price, (int, float)) else "Not specified",
                            'total_price': int(total_price) if isinstance(total_price, (int, float)) else "Not specified"
                        })
                    except Exception as e:
                        logging.warning(f"Error processing equipment {equip_type} for range {bed_range}: {e}")
                
                # Get budget information for this bed range if available
                min_budget = None
                max_budget = None
                
                if budget_min_row is not None and budget_max_row is not None:
                    try:
                        min_budget = sheet_df.iloc[budget_min_row][col_idx]
                        max_budget = sheet_df.iloc[budget_max_row][col_idx]
                        logging.info(f"Found budget for range {bed_range}: min={min_budget}, max={max_budget}")
                    except Exception as e:
                        logging.warning(f"Error getting budget for range {bed_range}: {e}")
                
                # Add to area data with equipment information and budget
                area_data.append({
                    'min_beds': min_beds,
                    'max_beds': max_beds,
                    'original_range': bed_range,
                    'data': {'Area (sq ft)': cssd_area},
                    'equipment': equipment_list,  # Add the list of equipment
                    'official_min_budget': int(min_budget) if isinstance(min_budget, (int, float)) and not pd.isna(min_budget) else None,
                    'official_max_budget': int(max_budget) if isinstance(max_budget, (int, float)) and not pd.isna(max_budget) else None
                })
                
                # Add to autoclave data
                autoclave_data.append({
                    'min_beds': min_beds,
                    'max_beds': max_beds,
                    'original_range': bed_range,
                    'data': {
                        'Autoclave Model': autoclave_model,
                        'Quantity': autoclave_qty
                    }
                })
                
            except Exception as e:
                logging.warning(f"Error processing bed range {bed_range}: {e}")
        
        # If we couldn't extract any data, use fallback data
        if not area_data:
            logging.warning("Could not extract CSSD area data from Excel, using fallback data")
            area_data = [
                {'min_beds': 0, 'max_beds': 20, 'original_range': '0-20', 
                 'data': {'Area (sq ft)': 150}},
                {'min_beds': 20, 'max_beds': 30, 'original_range': '20-30', 
                 'data': {'Area (sq ft)': 200}},
                {'min_beds': 30, 'max_beds': 50, 'original_range': '30-50', 
                 'data': {'Area (sq ft)': 350}},
                {'min_beds': 50, 'max_beds': 70, 'original_range': '50-70', 
                 'data': {'Area (sq ft)': 500}},
                {'min_beds': 70, 'max_beds': 100, 'original_range': '70-100', 
                 'data': {'Area (sq ft)': 700}},
                {'min_beds': 100, 'max_beds': 150, 'original_range': '100-150', 
                 'data': {'Area (sq ft)': 1000}},
                {'min_beds': 150, 'max_beds': 200, 'original_range': '150-200', 
                 'data': {'Area (sq ft)': 1500}},
                {'min_beds': 200, 'max_beds': 300, 'original_range': '200-300', 
                 'data': {'Area (sq ft)': 2000}},
                {'min_beds': 300, 'max_beds': 500, 'original_range': '300-500', 
                 'data': {'Area (sq ft)': 3500}},
                {'min_beds': 500, 'max_beds': 800, 'original_range': '500-800', 
                 'data': {'Area (sq ft)': 5000}},
                {'min_beds': 800, 'max_beds': 1000, 'original_range': '800-1000', 
                 'data': {'Area (sq ft)': 7000}},
                {'min_beds': 1000, 'max_beds': 1500, 'original_range': '1000-1500', 
                 'data': {'Area (sq ft)': 9000}},
                {'min_beds': 1500, 'max_beds': 2000, 'original_range': '1500-2000', 
                 'data': {'Area (sq ft)': 12000}}
            ]
            
        if not autoclave_data:
            logging.warning("Could not extract autoclave data from Excel, using fallback data")
            autoclave_data = [
                {'min_beds': 0, 'max_beds': 20, 'original_range': '0-20', 
                 'data': {'Autoclave Model': 'Cylindrical: 16×24 Single Door', 'Quantity': 1}},
                {'min_beds': 20, 'max_beds': 30, 'original_range': '20-30', 
                 'data': {'Autoclave Model': 'Cylindrical: 20×36 Single Door', 'Quantity': 1}},
                {'min_beds': 30, 'max_beds': 50, 'original_range': '30-50', 
                 'data': {'Autoclave Model': 'Cylindrical: 20×48 Double Door', 'Quantity': 1}},
                {'min_beds': 50, 'max_beds': 70, 'original_range': '50-70', 
                 'data': {'Autoclave Model': 'Cylindrical: 20×48 Double Door', 'Quantity': 2}},
                {'min_beds': 70, 'max_beds': 100, 'original_range': '70-100', 
                 'data': {'Autoclave Model': 'Cylindrical: 20×48 Double Door', 'Quantity': 2}},
                {'min_beds': 100, 'max_beds': 150, 'original_range': '100-150', 
                 'data': {'Autoclave Model': 'Rectangular: 2×2×4 Double Door', 'Quantity': 1}},
                {'min_beds': 150, 'max_beds': 200, 'original_range': '150-200', 
                 'data': {'Autoclave Model': 'Rectangular: 2×2×4 Double Door', 'Quantity': 2}},
                {'min_beds': 200, 'max_beds': 500, 'original_range': '200-500', 
                 'data': {'Autoclave Model': 'Rectangular: 2×2×4 Double Door', 'Quantity': 3}}
            ]
        
        logging.info(f"Processed data: {len(area_data)} area ranges, {len(autoclave_data)} autoclave ranges")
        
        # Return the processed data
        return {
            'sheet1': area_data,
            'sheet2': autoclave_data
        }
        
    except Exception as e:
        logging.error(f"Error loading Excel file: {e}")
        # For development/testing, return mock data if file can't be loaded
        return create_mock_data()

def process_sheet_data(df):
    """
    Process the dataframe to extract bed ranges and associated data.
    Converts string ranges like "0-20" to numeric boundaries.
    """
    processed_rows = []
    
    # Log the DataFrame columns to help debug
    logging.info(f"DataFrame columns: {df.columns.tolist()}")
    
    # Remove any completely empty rows
    df = df.dropna(how='all')
    
    # First, attempt to identify the column headers
    if df.empty:
        logging.warning("DataFrame is empty")
        return processed_rows
    
    # Iterate through rows, skipping header rows if needed
    for idx, row in df.iterrows():
        # Skip entirely NaN rows
        if row.isna().all():
            continue
            
        # Extract the first column value which should contain bed range
        try:
            # Convert to string and clean up
            bed_range = str(row.iloc[0]).strip()
            logging.debug(f"Processing bed range: '{bed_range}'")
            
            # Skip if it's clearly a header or empty
            if bed_range.lower() in ['nan', 'none', '', 'beds', 'bed range', 'bed count'] or pd.isna(row.iloc[0]):
                logging.debug(f"Skipping header or empty row: {bed_range}")
                continue
                
            # Handle various range formats (0-20, 20-30, etc.)
            if '-' in bed_range:
                # Extract numbers from the range (handles formatting like "0 - 20 beds")
                parts = [p.strip() for p in bed_range.split('-')]
                min_beds = int(''.join(filter(str.isdigit, parts[0])))
                max_beds = int(''.join(filter(str.isdigit, parts[1])))
            elif '+' in bed_range:
                min_beds = int(''.join(filter(str.isdigit, bed_range)))
                max_beds = float('inf')  # Infinity for ranges like "300+"
            else:
                # Try to extract just the digits
                digits = ''.join(filter(str.isdigit, bed_range))
                if digits:
                    min_beds = max_beds = int(digits)
                else:
                    logging.warning(f"Could not extract digits from: '{bed_range}'")
                    continue
                    
            # Create a processed row with range boundaries and other data
            # Skip the first column (which is the bed range)
            data_dict = {}
            for i, col_name in enumerate(df.columns[1:], 1):
                if i < len(row) and not pd.isna(row.iloc[i]):
                    data_dict[col_name] = row.iloc[i]
            
            processed_row = {
                'min_beds': min_beds,
                'max_beds': max_beds,
                'original_range': bed_range,
                'data': data_dict
            }
            
            logging.debug(f"Processed row: {processed_row}")
            processed_rows.append(processed_row)
            
        except Exception as e:
            if hasattr(row, 'iloc') and len(row) > 0:
                logging.warning(f"Could not process row with value '{row.iloc[0]}': {e}")
            else:
                logging.warning(f"Could not process row: {e}")
    
    logging.info(f"Processed {len(processed_rows)} rows successfully")
    return processed_rows

def get_cssd_requirements(data, bed_count):
    """
    Get CSSD requirements based on the bed count.
    Returns a dictionary with the requirements.
    """
    # Find the matching range in sheet1
    area_info = None
    for row in data['sheet1']:
        if row['min_beds'] <= bed_count <= row['max_beds']:
            area_info = row
            break
    
    # Find the matching range in sheet2
    autoclave_info = None
    for row in data['sheet2']:
        if row['min_beds'] <= bed_count <= row['max_beds']:
            autoclave_info = row
            break
    
    # Combine the results
    if area_info or autoclave_info:
        requirements = {
            'bed_count': bed_count,
            'bed_range': area_info['original_range'] if area_info else 'Unknown',
            'cssd_area': area_info['data'].get('Area (sq ft)') if area_info else 'Not specified',
            'autoclave_model': autoclave_info['data'].get('Autoclave Model') if autoclave_info else 'Not specified',
            'autoclave_quantity': autoclave_info['data'].get('Quantity') if autoclave_info else 'Not specified',
            'equipment': [], # This will hold all equipment details
            'official_budget': {
                'min': area_info.get('official_min_budget', 'Not specified') if area_info else 'Not specified',
                'max': area_info.get('official_max_budget', 'Not specified') if area_info else 'Not specified'
            }
        }
        
        # Add all equipment information if available
        if area_info and 'equipment' in area_info:
            requirements['equipment'] = area_info['equipment']
            
        return requirements
    
    return None

def create_mock_data():
    """
    Create a mock data structure for testing when the Excel file is not available.
    This should only be used during development.
    """
    logging.warning("Using mock CSSD data for development purposes")
    
    # Mock structure that mirrors what we'd get from the Excel file
    mock_data = {
        'sheet1': [
            {'min_beds': 0, 'max_beds': 20, 'original_range': '0-20', 
             'data': {'Area (sq ft)': 500, 'Notes': 'Small hospital'}},
            {'min_beds': 21, 'max_beds': 50, 'original_range': '21-50', 
             'data': {'Area (sq ft)': 800, 'Notes': 'Medium hospital'}},
            {'min_beds': 51, 'max_beds': 100, 'original_range': '51-100', 
             'data': {'Area (sq ft)': 1200, 'Notes': 'Large hospital'}},
            {'min_beds': 101, 'max_beds': 200, 'original_range': '101-200', 
             'data': {'Area (sq ft)': 1800, 'Notes': 'Very large hospital'}},
            {'min_beds': 201, 'max_beds': float('inf'), 'original_range': '201+', 
             'data': {'Area (sq ft)': 2500, 'Notes': 'Major hospital'}}
        ],
        'sheet2': [
            {'min_beds': 0, 'max_beds': 20, 'original_range': '0-20', 
             'data': {'Autoclave Model': 'AC-Small', 'Quantity': 1}},
            {'min_beds': 21, 'max_beds': 50, 'original_range': '21-50', 
             'data': {'Autoclave Model': 'AC-Medium', 'Quantity': 1}},
            {'min_beds': 51, 'max_beds': 100, 'original_range': '51-100', 
             'data': {'Autoclave Model': 'AC-Large', 'Quantity': 2}},
            {'min_beds': 101, 'max_beds': 200, 'original_range': '101-200', 
             'data': {'Autoclave Model': 'AC-XLarge', 'Quantity': 2}},
            {'min_beds': 201, 'max_beds': float('inf'), 'original_range': '201+', 
             'data': {'Autoclave Model': 'AC-XLarge', 'Quantity': 3}}
        ]
    }
    
    return mock_data
