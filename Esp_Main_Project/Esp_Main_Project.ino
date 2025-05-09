#include <ArduinoJson.h>
#include "MqttHandler.h"
#include "myHCSR04.h"
#include "myYFS201C.h"
#include "myDS18B20.h"
#include "myDHT11.h"

// Wi-Fi and MQTT credentials
const char* ssid = "M.Asim";
const char* password = "hmmmmm123";
const char* mqttServer = "broker.emqx.io";
const int mqttPort = 1883;
const char* mqttUser = ""; 
const char* mqttPassword = ""; 
const char* mqttTopic = "esp8266/sensorData";

// Create sensor objects
myHCSR04 ultrasonic(D1, D2);
myYFS201C flowSensor(D5);
myDS18B20 tempSensor(D6);
myDHT11 dhtSensor(D0);

// Instantiate MqttHandler
MqttHandler mqttHandler(ssid, password, mqttServer, mqttPort, mqttUser, mqttPassword, mqttTopic);

// Variables to manage timing
unsigned long previousMillis = 0;
const long interval = 5000; // 5 seconds interval

void setup() {
  Serial.begin(115200);

  // Initialize sensors
  ultrasonic.setup();
  flowSensor.setup();
  tempSensor.setup();
  dhtSensor.setup();

  // Setup MQTT connection
  mqttHandler.setup(); 
}

void loop() {
  // Use the public loop method to keep MQTT connection alive
  mqttHandler.loop();

  unsigned long currentMillis = millis();

  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

    // Create JSON object to store all sensor data
    DynamicJsonDocument doc(512);

    // Read data from all sensors
    float distance = ultrasonic.getValue();
    float flowRate = flowSensor.getValue();
    float ds18b20Temp = tempSensor.getValue();
    float dhtTemp = dhtSensor.getTemperature();
    float dhtHumidity = dhtSensor.getHumidity();

    // Add sensor data to JSON
    if (!isnan(distance)) {
      doc["Ultrasonic"]["distance_cm"] = distance;
    } else {
      doc["Ultrasonic"]["error"] = "Invalid Distance";
    }

    if (!isnan(flowRate)) {
      doc["FlowSensor"]["flowRate_Lmin"] = flowRate;
    } else {
      doc["FlowSensor"]["error"] = "Invalid Flow Rate";
    }

    if (!isnan(ds18b20Temp)) {
      doc["DS18B20"]["temperature_C"] = ds18b20Temp;
    } else {
      doc["DS18B20"]["error"] = "Invalid Temperature";
    }

    if (!isnan(dhtTemp)) {
      doc["DHT11"]["temperature_C"] = dhtTemp;
    } else {
      doc["DHT11"]["temperature_error"] = "Invalid Temperature";
    }

    if (!isnan(dhtHumidity)) {
      doc["DHT11"]["humidity_percent"] = dhtHumidity;
    } else {
      doc["DHT11"]["humidity_error"] = "Invalid Humidity";
    }

    // Serialize JSON to string
    String jsonString;
    serializeJson(doc, jsonString);

    // Publish the JSON data to MQTT broker
    mqttHandler.publish(jsonString);
  }
}

