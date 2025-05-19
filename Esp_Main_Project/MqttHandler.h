#ifndef MQTTHANDLER_H
#define MQTTHANDLER_H

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

class MqttHandler {
private:
  const char* ssid;
  const char* password;
  const char* mqttServer;
  const int mqttPort;
  const char* mqttUser;
  const char* mqttPassword;
  const char* mqttTopic;
  String clientId; // Unique client ID

  WiFiClient espClient;
  PubSubClient client;
  unsigned long lastReconnectAttempt = 0; // Track last reconnection attempt
  const long reconnectInterval = 5000; // 5 seconds between reconnection attempts

  void reconnect() {
    // Only attempt reconnection if enough time has passed
    unsigned long now = millis();
    if (now - lastReconnectAttempt < reconnectInterval) {
      return; // Avoid rapid reconnection attempts
    }
    lastReconnectAttempt = now;

    Serial.println("Attempting MQTT connection...");
    if (client.connect(clientId.c_str(), mqttUser, mqttPassword)) {
      Serial.println("Connected to MQTT");
    } else {
      Serial.print("Failed MQTT connection, rc=");
      Serial.print(client.state());
      Serial.println(" will retry later");
    }
  }

public:
  MqttHandler(const char* ssid, const char* password, const char* server, int port, const char* user, const char* pass, const char* topic) 
    : ssid(ssid), password(password), mqttServer(server), mqttPort(port), mqttUser(user), mqttPassword(pass), mqttTopic(topic), client(espClient) {
    // Generate a unique client ID using ESP8266's MAC address
    clientId = "ESP8266Client-" + String(WiFi.macAddress());
  }

  void setup() {
    // Connect to Wi-Fi
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
      delay(1000);
      Serial.println("Connecting to WiFi...");
    }
    Serial.println("Connected to WiFi");

    // Set MQTT server
    client.setServer(mqttServer, mqttPort);
    client.setKeepAlive(60); // Set keep-alive to 60 seconds

    // Connect to MQTT broker
    reconnect();
  }

  void publish(const String& payload) {
    if (client.connected()) {
      Serial.print("Publishing data: ");
      Serial.println(payload);
      client.publish(mqttTopic, payload.c_str());
    } else {
      Serial.println("MQTT not connected, skipping publish");
    }
  }

  void loop() {
    // Check Wi-Fi connection
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("WiFi disconnected, attempting to reconnect...");
      WiFi.begin(ssid, password);
      while (WiFi.status() != WL_CONNECTED) {
        delay(1000);
        Serial.println("Connecting to WiFi...");
      }
      Serial.println("Reconnected to WiFi");
    }

    // Check MQTT connection
    if (!client.connected()) {
      reconnect();
    }
    client.loop(); // Maintain MQTT connection
  }
};

#endif