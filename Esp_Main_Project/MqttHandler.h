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

  WiFiClient espClient;
  PubSubClient client;

public:
  MqttHandler(const char* ssid, const char* password, const char* server, int port, const char* user, const char* pass, const char* topic) 
    : ssid(ssid), password(password), mqttServer(server), mqttPort(port), mqttUser(user), mqttPassword(pass), mqttTopic(topic), client(espClient) {}

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

    // Connect to MQTT broker
    reconnect();
  }

  void reconnect() {
    while (!client.connected()) {
      Serial.println("Connecting to MQTT...");
      if (client.connect("ESP8266Client", mqttUser, mqttPassword)) {
        Serial.println("Connected to MQTT");
      } else {
        Serial.print("Failed MQTT connection, rc=");
        Serial.print(client.state());
        Serial.println(" retrying in 5 seconds");
        delay(5000);
      }
    }
  }

  void publish(const String& payload) {
    if (!client.connected()) {
      reconnect();
    }
    Serial.print("Publishing data: ");
    Serial.println(payload);
    client.publish(mqttTopic, payload.c_str());
  }

  // Add this method to expose client.loop() functionality
  void loop() {
    client.loop();
  }
};

#endif
