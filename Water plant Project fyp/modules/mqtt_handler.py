import json
import paho.mqtt.client as mqtt

latest_data = {}

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        latest_data.update(payload)  # Adjust to flatten structure if needed
    except json.JSONDecodeError:
        print("Error decoding MQTT message.")

def setup_mqtt_client(config):
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(config['mqtt_broker'], config['mqtt_port'])
    client.subscribe(config['mqtt_topic'])
    client.loop_start()
    return client

def disconnect_mqtt_client(client):
    client.loop_stop()
    client.disconnect()
