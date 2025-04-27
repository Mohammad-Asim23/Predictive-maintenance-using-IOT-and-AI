# dashboard_routes.py
import pandas as pd
import os
import time
import json
from flask import Blueprint, render_template, jsonify, request, current_app,  redirect, url_for, render_template, request
import paho.mqtt.client as mqtt
from threading import Thread, Lock
from modules.graph_config import load_config, save_config
from modules.routes.auth_routes import login_required

dashboard_bp = Blueprint('dashboard', __name__)

# Shared data for storing the latest values from the data source
latest_data = {}
data_lock = Lock()  # To ensure thread safety for shared `latest_data`

# Flag to control the data source
is_demo_mode = True
demo_thread = None

# MQTT Client setup
mqtt_client = mqtt.Client()

def on_message(client, userdata, msg):
    try:
        print(f"MQTT Message Received on topic {msg.topic}")
        print(f"Raw payload: {msg.payload}")
        with data_lock:
            latest_data.update(json.loads(msg.payload))
            print(f"Updated latest_data: {latest_data}")
    except Exception as e:
        print(f"Error processing MQTT message: {e}")
        print(f"Payload that caused error: {msg.payload}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected to MQTT broker! Subscribing to {client._topic}")
        client.subscribe(client._topic)
    else:
        print(f"MQTT connection failed with code {rc}")

# Initialize MQTT with settings from config.json
def init_mqtt(config):
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client._topic = config['mqtt_topic']
    mqtt_client.connect(config['mqtt_broker'], config['mqtt_port'])
    mqtt_client.loop_start()

# Function to read data from CSV in demo mode
def read_demo_data(csv_path, interval):
    global is_demo_mode
    try:
        while is_demo_mode:
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                if not is_demo_mode:
                    break
                with data_lock:
                    latest_data.update(row.to_dict())
                time.sleep(interval)
    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_path}")
    except Exception as e:
        print(f"Error reading demo data: {e}")

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    config = load_config()  # Load the configuration from `config.json`
    demo_data = []

    if config['read_demo_data']:
        # Read the demo data from CSV
        csv_path = config.get('csv_file_path', 'water_plant_sensor_data.csv')
        try:
            df = pd.read_csv(csv_path)
            df['Timestamp'] = df['Timestamp'].astype(str)
            demo_data = df.to_dict(orient='list')  # Convert columns to lists for easy rendering
            
        except FileNotFoundError:
            print(f"Error: CSV file not found at {csv_path}")
        except Exception as e:
            print(f"Error reading CSV: {e}")

    return render_template(
        'dashboard.html',
        config=config,
        demo_data=demo_data
    )



@dashboard_bp.route('/toggle-data-mode', methods=['POST'])
def toggle_data_mode():
    global is_demo_mode, demo_thread

    mode = request.json.get('mode', 'demo')  # Expecting 'demo' or 'real'
    config_file_path = os.path.join(current_app.root_path, 'config.json')

    # Update the `read_demo_data` flag in the config
    with open(config_file_path, 'r') as f:
        config = json.load(f)

    if mode == 'demo':
        is_demo_mode = True
        config['read_demo_data'] = True

        # Stop MQTT if it's running
        mqtt_client.loop_stop()

        # Start demo thread
        if demo_thread and demo_thread.is_alive():
            print("Demo thread already running")
        else:
            csv_path = config.get('csv_file_path', 'demo_data.csv')
            update_interval = config.get('update_interval', 1)
            demo_thread = Thread(target=read_demo_data, args=(csv_path, update_interval))
            demo_thread.daemon = True
            demo_thread.start()
    else:
        is_demo_mode = False
        config['read_demo_data'] = False

        # Stop the demo thread gracefully
        if demo_thread and demo_thread.is_alive():
            demo_thread.join(timeout=2)

        # Start MQTT
        mqtt_config = {
            'mqtt_broker': config['mqtt_broker'],
            'mqtt_port': config['mqtt_port'],
            'mqtt_topic': config['mqtt_topic']
        }
        init_mqtt(mqtt_config)

    # Save updated config back to file
    with open(config_file_path, 'w') as f:
        json.dump(config, f, indent=4)

    return jsonify({"status": "success", "mode": mode})

@dashboard_bp.route('/data')
def get_data():
    with data_lock:
        return jsonify(latest_data)

@dashboard_bp.route('/update-config', methods=['POST'])
def update_config():
    data = request.json
    config_path = 'config.json'
    
    try:
        # Load the current configuration
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Perform actions based on the request
        if data['action'] == 'add':
            config['gauges'].append(data['gauge'])
        elif data['action'] == 'edit':
            config['gauges'][data['index']] = data['gauge']
        elif data['action'] == 'delete':
            # Delete the gauge by index
            index = data['index']
            if 0 <= index < len(config['gauges']):
                config['gauges'].pop(index)
            else:
                return jsonify({'error': 'Invalid index'}), 400

        # Save the updated configuration back to the file
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
