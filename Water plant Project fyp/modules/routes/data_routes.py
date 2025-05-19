from flask import Blueprint, request, jsonify
from datetime import datetime
from modules.database import Database

data_routes = Blueprint('data', __name__)

@data_routes.route('/api/save-sensor-data', methods=['POST'])
def save_sensor_data():
    """Save sensor data from MQTT to database"""
    try:
        data = request.json
        db = Database()
        
        # Current timestamp
        timestamp = datetime.now().isoformat()
        
        # Process and save each sensor reading
        if 'Ultrasonic' in data and 'distance_cm' in data['Ultrasonic']:
            db.add_sensor_reading(
                timestamp=timestamp,
                asset_id='A3',
                sensor_type='Ultrasonic',
                sensor_name='distance_cm',
                value=data['Ultrasonic']['distance_cm'],
                unit='cm'
            )
        
        if 'FlowSensor' in data and 'flowRate_Lmin' in data['FlowSensor']:
            db.add_sensor_reading(
                timestamp=timestamp,
                asset_id='A4',
                sensor_type='FlowSensor',
                sensor_name='flowRate_Lmin',
                value=data['FlowSensor']['flowRate_Lmin'],
                unit='L/min'
            )
        
        if 'DS18B20' in data and 'temperature_C' in data['DS18B20']:
            db.add_sensor_reading(
                timestamp=timestamp,
                asset_id='A2',
                sensor_type='DS18B20',
                sensor_name='temperature_C',
                value=data['DS18B20']['temperature_C'],
                unit='°C'
            )
        
        if 'DHT11' in data:
            if 'temperature_C' in data['DHT11']:
                db.add_sensor_reading(
                    timestamp=timestamp,
                    asset_id='A1',
                    sensor_type='DHT11',
                    sensor_name='temperature_C',
                    value=data['DHT11']['temperature_C'],
                    unit='°C'
                )
            
            if 'humidity_percent' in data['DHT11']:
                db.add_sensor_reading(
                    timestamp=timestamp,
                    asset_id='A1',
                    sensor_type='DHT11',
                    sensor_name='humidity_percent',
                    value=data['DHT11']['humidity_percent'],
                    unit='%'
                )
        
        db.close()
        return jsonify({"success": True, "message": "Sensor data saved successfully"})
    
    except Exception as e:
        print(f"Error saving sensor data: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@data_routes.route('/api/save-prediction', methods=['POST'])
def save_prediction():
    """Save prediction data from API to database"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['asset_id', 'failure_predicted', 'failure_probability']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400
        
        # Get timestamp from request or use current time
        timestamp = data.get('timestamp', datetime.now().isoformat())
        
        # Save to database
        db = Database()
        result = db.add_prediction(
            asset_id=data['asset_id'],
            timestamp=timestamp,
            failure_predicted=data['failure_predicted'],
            failure_probability=data['failure_probability']
        )
        db.close()
        
        if result:
            return jsonify({
                "success": True,
                "message": f"Prediction saved for asset {data['asset_id']}"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Database error while saving prediction"
            }), 500
            
    except Exception as e:
        print(f"Error saving prediction data: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@data_routes.route('/api/check-data', methods=['GET'])
def check_data():
    """Check recent data in the database"""
    try:
        db = Database()
        recent_sensors = db.get_recent_sensor_readings(10)
        recent_predictions = db.get_recent_predictions(10)
        db.close()
        
        return jsonify({
            "success": True,
            "recent_sensors": recent_sensors,
            "recent_predictions": recent_predictions
        })
        
    except Exception as e:
        print(f"Error checking database data: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Add these routes to your data_routes.py file

@data_routes.route('/api/sensor-history/<asset_id>', methods=['GET'])
def get_sensor_history(asset_id):
    """Get sensor history for a specific asset"""
    try:
        db = Database()
        
        # Handle the special case for A1 which has both temperature and humidity
        if asset_id == 'A1-temp':
            data = db.get_sensor_data_by_sensor(asset_id='A1', sensor_name='temperature_C')
        elif asset_id == 'A1-humidity':
            data = db.get_sensor_data_by_sensor(asset_id='A1', sensor_name='humidity_percent')
        else:
            data = db.get_sensor_data_by_asset(asset_id)
        
        db.close()
        
        return jsonify({
            "success": True,
            "data": data
        })
    
    except Exception as e:
        print(f"Error getting sensor history: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@data_routes.route('/api/prediction-history/<asset_id>', methods=['GET'])
def get_prediction_history(asset_id):
    """Get prediction history for a specific asset"""
    try:
        db = Database()
        data = db.get_predictions_by_asset(asset_id)
        db.close()
        
        return jsonify({
            "success": True,
            "data": data
        })
    
    except Exception as e:
        print(f"Error getting prediction history: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@data_routes.route('/api/stats/failures', methods=['GET'])
def get_failure_stats():
    """Get failure statistics for all assets"""
    try:
        db = Database()
        stats = db.get_failure_stats()
        db.close()
        
        return jsonify(stats)
    
    except Exception as e:
        print(f"Error getting failure stats: {e}")
        return jsonify({"error": str(e)}), 500