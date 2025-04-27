import paho.mqtt.client as mqtt
import json
import time
import threading
import queue

class MQTTClient:
    def __init__(self, broker="broker.emqx.io", port=1883, topic="esp8266/sensorData"):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.connected = False
        self.data_queue = queue.Queue()
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to MQTT broker at {self.broker}:{self.port}")
            self.client.subscribe(self.topic)
            self.connected = True
        else:
            print(f"Failed to connect to MQTT broker, return code: {rc}")
            
    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode()
            data = json.loads(payload)
            self.data_queue.put(data)
            print(f"Received data: {data}")
        except Exception as e:
            print(f"Error processing message: {e}")
            
    def connect(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            # Wait for connection to establish
            timeout = 5
            start_time = time.time()
            while not self.connected and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                print("Connection timeout")
                return False
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
            
    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        print("Disconnected from MQTT broker")
        
    def publish(self, topic, message):
        if isinstance(message, dict):
            message = json.dumps(message)
        self.client.publish(topic, message)
        
    def get_data(self, timeout=1):
        try:
            return self.data_queue.get(timeout=timeout)
        except queue.Empty:
            return None

# Example usage
if __name__ == "__main__":
    # Test the MQTT client
    client = MQTTClient()
    if client.connect():
        print("Connected to MQTT broker")
        
        # Publish a test message
        test_data = {
            "asset_id": "A1",
            "temp_sensor_A1": 25.5,
            "humidity_sensor_A1": 45.2,
            "timestamp": time.time()
        }
        client.publish("sensors/data", test_data)
        
        try:
            # Keep the connection open until manually interrupted
            print("Listening for messages... Press Ctrl+C to exit")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Interrupted by user")
        finally:
            client.disconnect()
    else:
        print("Failed to connect to MQTT broker")