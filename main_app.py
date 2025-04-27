import tensorflow as tf
import numpy as np
import pandas as pd
import joblib
import time
import json
import os
from mqtt_client import MQTTClient
import threading
import requests
from datetime import datetime
    # Add these imports at the top of your file
from flask import Flask, jsonify, request
from flask_cors import CORS
import threading

# Add this import at the top
# from modules.notification import NotificationManager

class PredictiveMaintenanceApp:
    def __init__(self, models_dir="models", scalers_dir="scalers", web_api_url="http://localhost:5000/api/predictions"):
        self.models_dir = models_dir
        self.scalers_dir = scalers_dir
        self.web_api_url = web_api_url
        self.mqtt_client = MQTTClient(topic="esp8266/sensorData")  # Subscribe to all sensor topics
        self.models = {}
        self.scalers = {}
        self.asset_features = {
            'A1': ['temp_sensor_A1', 'humidity_sensor_A1'],
            'A2': ['waterproof_temp_A2'],
            'A3': ['ultrasonic_distance_A3'],
            'A4': ['flow_rate_A4']
        }
        # self.notification_manager = NotificationManager()  # Initialize notification manager
        self.load_models()

    def load_models(self):
        """Load all trained models and scalers"""
        for asset_id in self.asset_features.keys():
            model_path = os.path.join(self.models_dir, f"model_{asset_id}.h5")
            scaler_path = os.path.join(self.scalers_dir, f"scaler_{asset_id}.pkl")
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                try:
                    self.models[asset_id] = tf.keras.models.load_model(model_path)
                    self.scalers[asset_id] = joblib.load(scaler_path)
                    print(f"Loaded model and scaler for Asset {asset_id}")
                except Exception as e:
                    print(f"Error loading model for Asset {asset_id}: {e}")
            else:
                print(f"Model or scaler for Asset {asset_id} not found")
                
    def preprocess_data(self, data):
        """Preprocess incoming sensor data for prediction"""
        # Handle the new format with sensor types as keys
        if 'DHT11' in data and 'DS18B20' in data:
            # This is the new format with sensor types as keys
            asset_id = None
            feature_values = []
            
            # For A1 (Air temp and humidity from DHT11)
            if ('DHT11' in data and 
                'temperature_C' in data['DHT11'] and 
                'humidity_percent' in data['DHT11']):
                asset_id = 'A1'
                feature_values = [
                    data['DHT11']['temperature_C'],
                    data['DHT11']['humidity_percent']
                ]
            
            # For A2 (Water temperature from DS18B20)
            elif 'DS18B20' in data and 'temperature_C' in data['DS18B20']:
                asset_id = 'A2'
                feature_values = [data['DS18B20']['temperature_C']]
            
            # For A3 (Ultrasonic distance)
            elif 'Ultrasonic' in data and 'distance_cm' in data['Ultrasonic'] and data['Ultrasonic']['distance_cm'] > 0:
                asset_id = 'A3'
                feature_values = [data['Ultrasonic']['distance_cm']]
            
            # For A4 (Flow rate)
            elif 'FlowSensor' in data and 'flowRate_Lmin' in data['FlowSensor'] and data['FlowSensor']['flowRate_Lmin'] > 0:
                asset_id = 'A4'
                feature_values = [data['FlowSensor']['flowRate_Lmin']]
            
            # If we found a valid asset and features, create DataFrame and scale
            if asset_id and feature_values:
                features = self.asset_features[asset_id]
                df = pd.DataFrame([feature_values], columns=features)
                scaled_data = self.scalers[asset_id].transform(df)
                return asset_id, scaled_data
                
        # Handle the previous format with entity and data fields
        elif 'entity' in data and 'data' in data:
            entity = data.get('entity')
            sensor_data = data.get('data')
            
            # Map entity to asset_id if needed
            asset_id = None
            if entity == 'water_plant_sensor_data':
                # Determine asset_id based on available sensors
                if 'Ultrasonic Distance' in sensor_data:
                    asset_id = 'A3'
                elif 'Water Temperature' in sensor_data:
                    asset_id = 'A2'
                elif 'Air Temperature' in sensor_data and 'Humidity' in sensor_data:
                    asset_id = 'A1'
                elif 'Water Flow' in sensor_data:
                    asset_id = 'A4'
        else:
            # Original format handling
            asset_id = data.get('asset_id')
            sensor_data = data
        
        if asset_id not in self.asset_features:
            print(f"Unknown asset ID: {asset_id}")
            return None, None
            
        features = self.asset_features[asset_id]
        
        # Map incoming sensor names to model feature names
        sensor_mapping = {
            'Air Temperature': 'temp_sensor_A1',
            'Humidity': 'humidity_sensor_A1',
            'Water Temperature': 'waterproof_temp_A2',
            'Ultrasonic Distance': 'ultrasonic_distance_A3',
            'Water Flow': 'flow_rate_A4'
        }
        
        # Extract feature values
        feature_values = []
        for feature in features:
            # Try to get the value using the feature name directly
            if feature in sensor_data:
                feature_values.append(sensor_data[feature])
            else:
                # Try to find the feature using the mapping
                found = False
                for sensor_name, model_feature in sensor_mapping.items():
                    if model_feature == feature and sensor_name in sensor_data:
                        feature_values.append(sensor_data[sensor_name])
                        found = True
                        break
                
                if not found:
                    print(f"Missing feature {feature} for asset {asset_id}")
                    return None, None
                
        # Create a DataFrame with the feature values
        df = pd.DataFrame([feature_values], columns=features)
        
        # Scale the features
        scaled_data = self.scalers[asset_id].transform(df)
        
        return asset_id, scaled_data
        

    
    # Add this to your PredictiveMaintenanceApp class
    def start_api_server(self, port=5000):
        """Start a Flask API server to serve predictions"""
        app = Flask(__name__)
        CORS(app, resources={r"/api/*": {"origins": "*"}})  # Enable CORS for API routes
        
        # Get current time for initial timestamps
        current_time = datetime.now().isoformat()
        
        # Store the latest predictions with initialized timestamps
        self.latest_predictions = {
            'A1': {'failure_predicted': 0, 'failure_probability': 0.0, 'timestamp': current_time},
            'A2': {'failure_predicted': 0, 'failure_probability': 0.0, 'timestamp': current_time},
            'A3': {'failure_predicted': 0, 'failure_probability': 0.0, 'timestamp': current_time},
            'A4': {'failure_predicted': 0, 'failure_probability': 0.0, 'timestamp': current_time}
        }
        
        @app.route('/api/predictions', methods=['GET'])
        def get_predictions():
            print("API request received for predictions")
            print("Current predictions:", self.latest_predictions)
            return jsonify(self.latest_predictions)
        
        @app.route('/api/predictions', methods=['POST'])
        def update_prediction():
            data = request.json
            asset_id = data.get('asset_id')
            if asset_id in self.latest_predictions:
                self.latest_predictions[asset_id] = {
                    'failure_predicted': data.get('failure_predicted', 0),
                    'failure_probability': data.get('failure_probability', 0),
                    'timestamp': data.get('timestamp')
                }
                return jsonify({"status": "success"})
            return jsonify({"status": "error", "message": f"Unknown asset ID: {asset_id}"}), 400
        
        # Run the Flask app in a separate thread
        def run_flask():
            app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        print(f"API server started on port {port}")
    
    # Update the make_prediction method to store predictions
    def make_prediction(self, asset_id, scaled_data):
        """Make a prediction using the appropriate model"""
        if asset_id not in self.models:
            print(f"No model available for Asset {asset_id}")
            return None
            
        # Make prediction
        prediction_prob = self.models[asset_id].predict(scaled_data, verbose=0)[0][0]
        prediction = 1 if prediction_prob > 0.3 else 0  # Using threshold of 0.3
        
        # Create timestamp for all predictions, regardless of failure status
        current_time = datetime.now().isoformat()
        
        result = {
            "asset_id": asset_id,
            "failure_probability": float(prediction_prob),
            "failure_predicted": int(prediction),
            "timestamp": current_time
        }
        
        # Update the latest prediction for this asset
        if hasattr(self, 'latest_predictions'):
            self.latest_predictions[asset_id] = {
                'failure_predicted': int(prediction),
                'failure_probability': float(prediction_prob),
                'timestamp': current_time
            }
            print(f"Updated latest prediction for {asset_id}: {self.latest_predictions[asset_id]}")
            
            # Comment out or properly handle notification
            # if hasattr(self, 'notification_manager'):
            #     self.notification_manager.send_email_notification(asset_id, self.latest_predictions[asset_id])
        
        return result
    
    # Update the run method to start the API server but not send predictions
    def run(self):
        """Start the application"""
        # Start the API server
        self.start_api_server()
        
        if self.mqtt_client.connect():
            print("Connected to MQTT broker")
            # Start processing in a separate thread
            processing_thread = threading.Thread(target=self.process_data_loop)
            processing_thread.daemon = True
            processing_thread.start()
            
            try:
                # Keep the main thread alive
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("Application stopped by user")
                self.mqtt_client.disconnect()
        else:
            print("Failed to connect to MQTT broker")

    # Comment out or modify this method to disable sending to web API
    def send_to_web(self, prediction_result):
        """Send prediction results to web API - DISABLED"""
        print("Web API sending is disabled")
        return
            
    def process_data_loop(self):
        """Main loop to process incoming data"""
        while True:
            data = self.mqtt_client.get_data()
            if data:
                print("\n--- New Sensor Data Received ---")
                print(f"Raw data: {data}")
                
                asset_id, scaled_data = self.preprocess_data(data)
                if asset_id and scaled_data is not None:
                    prediction = self.make_prediction(asset_id, scaled_data)
                    if prediction:
                        # Print prediction details to terminal
                        print("\n=== PREDICTION RESULTS ===")
                        print(f"Asset ID: {prediction['asset_id']}")
                        print(f"Failure Probability: {prediction['failure_probability']:.4f}")
                        print(f"Failure Predicted: {'YES' if prediction['failure_predicted'] == 1 else 'NO'}")
                        print(f"Timestamp: {prediction['timestamp']}")
                        print("==========================\n")
                        
                        # Send prediction back to MQTT
                        self.mqtt_client.publish("predictions", prediction)
                        # Don't send prediction to web API
                        # self.send_to_web(prediction)
                else:
                    print(f"Could not process data for prediction")
            time.sleep(0.1)  # Small delay to prevent CPU hogging
            

if __name__ == "__main__":
    app = PredictiveMaintenanceApp()
    app.run()