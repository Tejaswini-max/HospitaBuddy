import os
import logging
from flask import Flask, render_template, request, jsonify
from utils.excel_parser import load_cssd_data, get_cssd_requirements

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

# Load CSSD planning data from Excel file
try:
    cssd_data = load_cssd_data()
    logging.info("CSSD data loaded successfully")
except Exception as e:
    logging.error(f"Error loading CSSD data: {e}")
    cssd_data = None

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    """Calculate CSSD requirements based on bed count"""
    try:
        bed_count = int(request.form.get('bed_count', 0))
        
        if bed_count <= 0:
            return jsonify({'error': 'Please enter a valid positive number of beds'})
        
        if cssd_data is None:
            return jsonify({'error': 'Error loading CSSD data. Please check the Excel file.'})
        
        # Get requirements based on bed count
        requirements = get_cssd_requirements(cssd_data, bed_count)
        
        if requirements:
            # Log equipment details for debugging
            if 'equipment' in requirements and requirements['equipment']:
                logging.info(f"Equipment count: {len(requirements['equipment'])}")
                for i, item in enumerate(requirements['equipment']):
                    logging.info(f"Equipment {i+1}: {item['name']}, Qty: {item['quantity']}, "
                                 f"Unit Price: {item['unit_price']}, Total Price: {item['total_price']}")
            
            return jsonify(requirements)
        else:
            return jsonify({'error': 'Could not determine requirements for the given bed count'})
            
    except ValueError:
        return jsonify({'error': 'Please enter a valid number of beds'})
    except Exception as e:
        logging.error(f"Error calculating requirements: {e}")
        return jsonify({'error': f'An error occurred: {str(e)}'})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
