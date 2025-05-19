import os
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from modules.graph_config import load_config, save_config
import json
from models.user import db
# Make sure this line is correct
from modules.routes.settings_routes import settings
from modules.routes.auth_routes import auth_bp, login_required
from modules.notification import NotificationManager
from flask import request, jsonify
from datetime import datetime
# Add these imports for MQTT
from flask_mqtt import Mqtt
from modules.database import Database

# Create the Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy with the Flask app
db.init_app(app)

# Initialize migration
from flask_migrate import Migrate
migrate = Migrate(app, db)

# Create database tables
with app.app_context():
    # First create all tables
    db.create_all()
    
    # Then check if the is_verified column exists
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [column['name'] for column in inspector.get_columns('user')]
        
        if 'is_verified' not in columns:
            # Add the is_verified column
            db.engine.execute('ALTER TABLE user ADD COLUMN is_verified BOOLEAN DEFAULT FALSE')
    except Exception as e:
        print(f"Note: Could not check for is_verified column: {e}")
        print("This is normal if the database is being created for the first time.")

# Load configuration for MQTT
config = load_config()
mqtt_broker = config.get('mqtt_broker', 'broker.emqx.io')
mqtt_port = config.get('mqtt_port', 8883)
mqtt_topic = config.get('mqtt_topic', 'esp8266/sensorData')

# Configure MQTT
app.config['MQTT_BROKER_URL'] = mqtt_broker
app.config['MQTT_BROKER_PORT'] = mqtt_port

# Initialize MQTT client
mqtt = Mqtt(app)

# Initialize database
database = Database()

# Global variable to store the latest MQTT data
mqtt_data = {}

# Add this after initializing the app and before creating tables
from flask_migrate import Migrate

# Initialize migration
migrate = Migrate(app, db)

# Create database tables
with app.app_context():
    # Check if the is_verified column exists
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    columns = [column['name'] for column in inspector.get_columns('user')]
    
    if 'is_verified' not in columns:
        # Add the is_verified column
        db.engine.execute('ALTER TABLE user ADD COLUMN is_verified BOOLEAN DEFAULT FALSE')
    
    db.create_all()

# Register the blueprints
# And when registering the Blueprint:
app.register_blueprint(settings)
app.register_blueprint(auth_bp)

# Add this import at the top with your other imports
from modules.routes.data_routes import data_routes

# Add this line where you register your other blueprints
app.register_blueprint(data_routes)

# Your existing routes...

# Make sure you have a route for the dashboard
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    config = load_config()
    
    # Initialize demo_data
    demo_data = {}
    
    # If demo mode is enabled, load demo data
    if config.get('read_demo_data', False):
        try:
            csv_path = config.get('csv_file_path')
            print(f"Loading demo data from: {csv_path}")
            
            if os.path.exists(csv_path):
                import pandas as pd
                df = pd.read_csv(csv_path)
                
                # Convert DataFrame to dictionary with lists
                demo_data = df.to_dict(orient='list')
                print(f"Loaded {len(demo_data.get('Timestamp', []))} data points")
                
                # Debug: Print the first few entries of each column
                for key in demo_data:
                    if isinstance(demo_data[key], list) and len(demo_data[key]) > 0:
                        print(f"{key}: {demo_data[key][:3]}...")
            else:
                print(f"Warning: CSV file {csv_path} not found for demo data")
        except Exception as e:
            print(f"Error loading demo data: {e}")
            import traceback
            traceback.print_exc()
    
    # Pass both config and demo_data to the template
    return render_template('dashboard.html', config=config, demo_data=demo_data)

# Add a route to toggle demo mode
@app.route('/toggle-data-mode', methods=['POST'])
def toggle_data_mode():
    data = request.json
    config = load_config()
    config['read_demo_data'] = data.get('read_demo_data', False)
    save_config(config)
    return jsonify({'read_demo_data': config['read_demo_data']})

@app.route('/add_gauge', methods=['POST'])
def add_gauge():
    try:
        title = request.form.get('title')
        value_key = request.form.get('value_key')
        min_val = float(request.form.get('min_val'))
        max_val = float(request.form.get('max_val'))
        color = request.form.get('color')
        
        # Get the warning and danger thresholds and colors
        warning_threshold = float(request.form.get('warning_threshold'))
        danger_threshold = float(request.form.get('danger_threshold'))
        warning_color = request.form.get('warning_color')
        danger_color = request.form.get('danger_color')
        
        # Load the current config
        config = load_config()
        
        # Create the new gauge configuration
        new_gauge = {
            'type': 'Gauge',
            'title': title,
            'value_key': value_key,
            'min_val': min_val,
            'max_val': max_val,
            'color': color,
            'warning_threshold': warning_threshold,
            'danger_threshold': danger_threshold,
            'warning_color': warning_color,
            'danger_color': danger_color
        }
        
        # Add the new gauge to the config
        if 'gauges' not in config:
            config['gauges'] = []
        
        config['gauges'].append(new_gauge)
        
        # Save the updated config
        save_config(config)
        
        return jsonify({'success': True, 'message': 'Gauge added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error adding gauge: {str(e)}'}), 400

@app.route('/edit_gauge', methods=['POST'])
def edit_gauge():
    try:
        gauge_index = int(request.form.get('gauge_index'))
        title = request.form.get('title')
        value_key = request.form.get('value_key')
        min_val = float(request.form.get('min_val'))
        max_val = float(request.form.get('max_val'))
        color = request.form.get('color')
        
        # Get the warning and danger thresholds and colors
        warning_threshold = float(request.form.get('warning_threshold'))
        danger_threshold = float(request.form.get('danger_threshold'))
        warning_color = request.form.get('warning_color')
        danger_color = request.form.get('danger_color')
        
        # Load the current config
        config = load_config()
        
        # Update the gauge configuration
        config['gauges'][gauge_index] = {
            'type': 'Gauge',
            'title': title,
            'value_key': value_key,
            'min_val': min_val,
            'max_val': max_val,
            'color': color,
            'warning_threshold': warning_threshold,
            'danger_threshold': danger_threshold,
            'warning_color': warning_color,
            'danger_color': danger_color
        }
        
        # Save the updated config
        save_config(config)
        
        return jsonify({'success': True, 'message': 'Gauge updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error updating gauge: {str(e)}'}), 400


@app.route('/delete_gauge', methods=['POST'])
def delete_gauge():
    try:
        gauge_index = int(request.form.get('gauge_index'))
        
        # Load the current config
        config = load_config()
        
        # Check if the gauge index is valid
        if gauge_index < 0 or gauge_index >= len(config['gauges']):
            return jsonify({'success': False, 'message': 'Invalid gauge index'}), 400
        
        # Remove the gauge from the config
        del config['gauges'][gauge_index]
        
        # Save the updated config
        save_config(config)
        
        return jsonify({'success': True, 'message': 'Gauge deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting gauge: {str(e)}'}), 400

# Redirect root to dashboard or login page based on authentication
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('auth.login'))

@app.route('/data-view')
def data_view():
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth.login'))
    
    # Add your data view logic here
    return render_template('data_view.html', active_page='data_view')
# Add these routes for the history page
@app.route('/history')
@login_required
def history():
    return render_template('history.html', active_page='history')

@app.route('/api/sensor/latest', methods=['GET'])
@login_required
def get_latest_sensor_data():
    return jsonify(mqtt_data)

@app.route('/api/history/sensor/<asset_id>', methods=['GET'])
@login_required
def get_sensor_history(asset_id):
    limit = request.args.get('limit', 50, type=int)
    sensor_type = request.args.get('type', None)
    
    # Create a new database instance for this request
    database = Database()
    
    try:
        # Connect to database in this thread
        database.connect()
        
        # For A1 (Air Temp & Humidity), we need to handle differently
        if asset_id == 'A1':
            if sensor_type == 'temperature':
                # Get temperature data
                database.cursor.execute(
                    'SELECT timestamp, value, "C" as unit FROM air_temperature WHERE asset_id = ? ORDER BY timestamp DESC LIMIT ?',
                    (asset_id, limit)
                )
                temp_data = [dict(row) for row in database.cursor.fetchall()]
                return jsonify(temp_data)
            elif sensor_type == 'humidity':
                # Get humidity data
                database.cursor.execute(
                    'SELECT timestamp, value, "%" as unit FROM air_humidity WHERE asset_id = ? ORDER BY timestamp DESC LIMIT ?',
                    (asset_id, limit)
                )
                humidity_data = [dict(row) for row in database.cursor.fetchall()]
                return jsonify(humidity_data)
            else:
                # Default to temperature if no type specified
                database.cursor.execute(
                    'SELECT timestamp, value, "C" as unit FROM air_temperature WHERE asset_id = ? ORDER BY timestamp DESC LIMIT ?',
                    (asset_id, limit)
                )
                temp_data = [dict(row) for row in database.cursor.fetchall()]
                return jsonify(temp_data)
        else:
            # For other assets, query the general sensor_data table
            database.cursor.execute(
                'SELECT timestamp, value, unit FROM sensor_data WHERE asset_id = ? ORDER BY timestamp DESC LIMIT ?',
                (asset_id, limit)
            )
            data = [dict(row) for row in database.cursor.fetchall()]
            return jsonify(data)
    except Exception as e:
        print(f"[API] Error fetching sensor history: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/history/predictions/<asset_id>')
@login_required
def get_prediction_history(asset_id):
    try:
        limit = request.args.get('limit', 50, type=int)
        # Create a new database instance for this request
        db = Database()
        db.connect()
        try:
            data = db.get_predictions_by_asset(asset_id, limit)
            print(f"Prediction data for {asset_id}: {len(data)} records")
            return jsonify(data)
        finally:
            db.close()
    except Exception as e:
        print(f"Error in get_prediction_history: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats/failures')
@login_required
def get_failure_stats():
    try:
        db_instance = Database()
        # Change this line to match your actual method name
        data = db_instance.get_failure_count()
        return jsonify(data)
    except Exception as e:
        print(f"Error in get_failure_stats: {str(e)}")
        return jsonify({"error": str(e)}), 500

from modules.notification import NotificationManager

# Initialize notification manager
notification_manager = NotificationManager()

# Add this route to your Flask app
@app.route('/send-notification', methods=['POST'])
def send_notification():
    data = request.json
    asset_id = data.get('asset_id')
    prediction = data.get('prediction')
    status = data.get('status')
    
   
    
    if not asset_id or not prediction:
        print("  - Missing required data")
        return jsonify({'sent': False, 'reason': 'Missing required data'})
    
    # Check if notification should be sent based on cooldown and settings
    should_send, notification_type = notification_manager.should_send_notification(asset_id, prediction)
    
    if should_send:
        # Send the email notification
        sent = notification_manager.send_email_notification(asset_id, prediction, notification_type)
        if sent:
            print(f"  - Email notification sent successfully")
            return jsonify({'sent': True})
        else:
            print(f"  - Failed to send email notification")
            return jsonify({'sent': False, 'reason': 'Email sending failed'})
    else:
        print(f"  - Notification not sent (cooldown or disabled)")
        return jsonify({'sent': False, 'reason': 'Notification on cooldown or disabled'})

# Add this import at the top of your file
from modules.database import Database

# Initialize the database
db = Database()

# Update your MQTT message handler to store data in the database
@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    try:
        # Parse the MQTT message
        payload = message.payload.decode()
        print(f"[MQTT] Received message on topic {message.topic}: {payload}")
        
        # Parse JSON data
        data = json.loads(payload)
        
        # Store the latest data
        global mqtt_data
        mqtt_data = data
        
        # Initialize database
        db = Database()
        db.connect()
        timestamp = datetime.now().isoformat()
        
        try:
            # Process each sensor type and store valid readings
            if 'DHT11' in data:
                # Check if temperature is valid
                if 'temperature' in data['DHT11'] and 'temperature_error' not in data['DHT11']:
                    temp_data = {
                        'timestamp': timestamp,
                        'asset_id': 'A1',
                        'sensor_type': 'DHT11',
                        'sensor_name': 'temperature',
                        'value': float(data['DHT11']['temperature']),
                        'unit': '°C'
                    }
                    result = db.store_sensor_data(temp_data)
                    print(f"[MQTT] Temperature data stored: {temp_data}, Result: {result}")
                    
                    # Generate prediction for temperature
                    failure_prob = predict_failure(temp_data['value'], 'temperature')
                    pred_result = db.store_prediction({
                        'timestamp': timestamp,
                        'asset_id': 'A1',
                        'failure_probability': failure_prob,
                        'failure_predicted': 1 if failure_prob > 0.7 else 0
                    })
                    print(f"[MQTT] Temperature prediction stored: {failure_prob}, Result: {pred_result}")
                
                # Check if humidity is valid
                if 'humidity' in data['DHT11'] and 'humidity_error' not in data['DHT11']:
                    humidity_data = {
                        'timestamp': timestamp,
                        'asset_id': 'A1',
                        'sensor_type': 'DHT11',
                        'sensor_name': 'humidity',
                        'value': float(data['DHT11']['humidity']),
                        'unit': '%'
                    }
                    result = db.store_sensor_data(humidity_data)
                    print(f"[MQTT] Humidity data stored: {humidity_data}, Result: {result}")
            
            if 'DS18B20' in data and 'temperature_C' in data['DS18B20']:
                temp_value = data['DS18B20']['temperature_C']
                if temp_value != -127:  # Valid temperature
                    sensor_data = {
                        'timestamp': timestamp,
                        'asset_id': 'A2',
                        'sensor_type': 'DS18B20',
                        'sensor_name': 'temperature',
                        'value': float(temp_value),
                        'unit': '°C'
                    }
                    result = db.store_sensor_data(sensor_data)
                    print(f"[MQTT] DS18B20 temperature data stored: {sensor_data}, Result: {result}")
                    
                    # Generate prediction for water temperature
                    failure_prob = predict_failure(sensor_data['value'], 'water_temperature')
                    pred_result = db.store_prediction({
                        'timestamp': timestamp,
                        'asset_id': 'A2',
                        'failure_probability': failure_prob,
                        'failure_predicted': 1 if failure_prob > 0.7 else 0
                    })
                    print(f"[MQTT] Water temperature prediction stored: {failure_prob}, Result: {pred_result}")
            
            # Add handling for other sensors like ultrasonic and flow rate if needed
            
        finally:
            # Close the database connection
            db.close()
            
    except json.JSONDecodeError:
        print(f"[MQTT] Error decoding JSON from message: {payload}")
    except Exception as e:
        print(f"[MQTT] Error processing message: {str(e)}")
        import traceback
        traceback.print_exc()

# Update the prediction function to handle different sensor types
def predict_failure(value, sensor_type):
    """
    Implement your failure prediction logic here
    For now, using a simple threshold-based prediction
    """
    if sensor_type == 'temperature':
        # Temperature too high or too low is bad
        if value > 35 or value < 10:
            return 0.8
        elif value > 30 or value < 15:
            return 0.5
        return 0.1
    
    elif sensor_type == 'water_temperature':
        # Water temperature should be in a specific range
        if value > 40 or value < 5:
            return 0.9
        elif value > 35 or value < 10:
            return 0.6
        return 0.2
    
    elif sensor_type == 'distance':
        # Distance too low means water level too high (flood risk)
        # Distance too high means water level too low (drought risk)
        if value < 5 or value > 100:
            return 0.85
        elif value < 10 or value > 80:
            return 0.6
        return 0.15
    
    elif sensor_type == 'flow_rate':
        # Flow rate too low means blockage or pump failure
        if value < 0.5:
            return 0.75
        elif value < 1.0:
            return 0.4
        return 0.1
    
    # Default case
    return 0.2

# MQTT connection callback
@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[MQTT] Connected successfully to broker {mqtt_broker}")
        mqtt.subscribe(mqtt_topic)
        print(f"[MQTT] Subscribed to topic: {mqtt_topic}")
    else:
        print(f"[MQTT] Failed to connect to broker, return code: {rc}")

# Update your prediction API route to store predictions
@app.route('/api/predictions', methods=['GET'])
def get_predictions():
    # Mock predictions for now - replace with your actual prediction logic
    predictions = {
        'A1': {'failure_probability': 0.05, 'failure_predicted': 0, 'timestamp': datetime.now().isoformat()},
        'A2': {'failure_probability': 0.15, 'failure_predicted': 0, 'timestamp': datetime.now().isoformat()},
        'A3': {'failure_probability': 0.02, 'failure_predicted': 0, 'timestamp': datetime.now().isoformat()},
        'A4': {'failure_probability': 0.08, 'failure_predicted': 0, 'timestamp': datetime.now().isoformat()}
    }
    
    # Store predictions in the database
    for asset_id, prediction in predictions.items():
        prediction_data = {
            'asset_id': asset_id,
            'failure_probability': prediction.get('failure_probability', 0),
            'failure_predicted': prediction.get('failure_predicted', 0),
            'timestamp': prediction.get('timestamp', datetime.now().isoformat())
        }
        database.store_prediction(prediction_data)
    
    return jsonify(predictions)

# Add this route to generate test data
@app.route('/api/generate-test-data')
def generate_test_data():
    try:
        db_instance = Database()
        from datetime import datetime, timedelta
        import random

        assets = ['A1', 'A2', 'A3', 'A4']
        sensors = {
            'A1': {'type': 'DHT22', 'name': 'temperature', 'unit': '°C'},
            'A2': {'type': 'DS18B20', 'name': 'temperature', 'unit': '°C'},
            'A3': {'type': 'HC-SR04', 'name': 'distance', 'unit': 'cm'},
            'A4': {'type': 'YF-S201', 'name': 'flowRate', 'unit': 'L/min'}
        }

        now = datetime.now()

        # Clear existing test data
        db_instance.connect()
        db_instance.cursor.execute("DELETE FROM sensor_data")
        db_instance.cursor.execute("DELETE FROM predictions")
        db_instance.conn.commit()

        # --- Keep the connection open for all inserts ---
        for asset_id in assets:
            # Generate sensor data
            for i in range(50):
                timestamp = (now - timedelta(hours=i)).isoformat()
                value = random.uniform(20, 30)
                db_instance.cursor.execute(
                    'INSERT INTO sensor_data (timestamp, asset_id, sensor_type, sensor_name, value, unit) VALUES (?, ?, ?, ?, ?, ?)',
                    (
                        timestamp,
                        asset_id,
                        sensors[asset_id]['type'],
                        sensors[asset_id]['name'],
                        value,
                        sensors[asset_id]['unit']
                    )
                )
            # Generate prediction data
            for i in range(50):
                timestamp = (now - timedelta(hours=i)).isoformat()
                failure_probability = random.uniform(0, 0.3)
                failure_predicted = 1 if failure_probability > 0.2 else 0
                db_instance.cursor.execute(
                    'INSERT INTO predictions (timestamp, asset_id, failure_probability, failure_predicted) VALUES (?, ?, ?, ?)',
                    (
                        timestamp,
                        asset_id,
                        failure_probability,
                        failure_predicted
                    )
                )
        db_instance.conn.commit()
        db_instance.close()
        # --- End of fix ---

        # Verify data was inserted
        db_instance = Database()
        db_instance.connect()
        db_instance.cursor.execute("SELECT COUNT(*) as count FROM sensor_data")
        sensor_count = db_instance.cursor.fetchone()['count']
        db_instance.cursor.execute("SELECT COUNT(*) as count FROM predictions")
        prediction_count = db_instance.cursor.fetchone()['count']
        db_instance.close()

        return jsonify({
            'success': True,
            'message': f'Test data generated successfully. Added {sensor_count} sensor records and {prediction_count} prediction records.'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error generating test data: {str(e)}'}), 500

@app.route('/api/debug/database')
@app.route('/api/debug/database', methods=['GET'])
@login_required
def debug_database():
    try:
        db_type = request.args.get('type', 'all')
        limit = request.args.get('limit', 20, type=int)
        
        # Create a new database instance for this request
        db = Database()
        db.connect()
        
        result = {
            'success': True,
            'data': {}
        }
        
        try:
            if db_type == 'all' or db_type == 'sensor':
                # Get sensor data
                db.cursor.execute(
                    'SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT ?',
                    (limit,)
                )
                result['data']['sensor_data'] = [dict(row) for row in db.cursor.fetchall()]
                
                # Get air temperature data
                db.cursor.execute(
                    'SELECT * FROM air_temperature ORDER BY timestamp DESC LIMIT ?',
                    (limit,)
                )
                result['data']['air_temperature'] = [dict(row) for row in db.cursor.fetchall()]
                
                # Get air humidity data
                db.cursor.execute(
                    'SELECT * FROM air_humidity ORDER BY timestamp DESC LIMIT ?',
                    (limit,)
                )
                result['data']['air_humidity'] = [dict(row) for row in db.cursor.fetchall()]
            
            if db_type == 'all' or db_type == 'prediction':
                # Get prediction data
                db.cursor.execute(
                    'SELECT * FROM predictions ORDER BY timestamp DESC LIMIT ?',
                    (limit,)
                )
                result['data']['predictions'] = [dict(row) for row in db.cursor.fetchall()]
            
            return jsonify(result)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in debug_database: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-mqtt-message')
@login_required
def test_mqtt_message():
    try:
        # Create a test message similar to what your ESP8266 would send
        test_data = {
            "DHT11": {
                "temperature": 25.5,
                "humidity": 60.2
            },
            "DS18B20": {
                "temperature_C": 22.3
            }
        }
        
        # Manually call the MQTT handler with this data
        payload = json.dumps(test_data).encode()
        
        # Create a mock message object
        class MockMessage:
            def __init__(self, topic, payload):
                self.topic = topic
                self.payload = payload
                
        mock_message = MockMessage(mqtt_topic, payload)
        
        # Call the handler directly
        handle_mqtt_message(None, None, mock_message)
        
        # Check if data was inserted by querying the database
        db = Database()
        db.connect()
        
        try:
            # Check for temperature data
            db.cursor.execute(
                'SELECT * FROM air_temperature ORDER BY timestamp DESC LIMIT 1'
            )
            temp_data = db.cursor.fetchone()
            
            # Check for humidity data
            db.cursor.execute(
                'SELECT * FROM air_humidity ORDER BY timestamp DESC LIMIT 1'
            )
            humidity_data = db.cursor.fetchone()
            
            # Check for predictions
            db.cursor.execute(
                'SELECT * FROM predictions ORDER BY timestamp DESC LIMIT 2'
            )
            predictions = [dict(row) for row in db.cursor.fetchall()]
            
            return jsonify({
                'success': True,
                'message': 'Test MQTT message processed',
                'data': {
                    'test_message': test_data,
                    'temperature': dict(temp_data) if temp_data else None,
                    'humidity': dict(humidity_data) if humidity_data else None,
                    'predictions': predictions
                }
            })
        finally:
            db.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error testing MQTT message: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=4000)