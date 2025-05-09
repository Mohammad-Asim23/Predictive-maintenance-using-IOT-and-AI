#ifndef MYHCSR04_H
#define MYHCSR04_H

#include <Arduino.h>

class myHCSR04 {
private:
  int trigPin;  // Pin to trigger the ultrasonic burst
  int echoPin;  // Pin to read the echo signal

public:
  // Constructor to initialize trigPin and echoPin
  myHCSR04(int trig, int echo) : trigPin(trig), echoPin(echo) {}

  // Set up the pins for the sensor
  void setup() {
    pinMode(trigPin, OUTPUT);
    pinMode(echoPin, INPUT);
  }

  // Get the distance measurement in centimeters
  float getValue() {
    long duration;    // Variable to store the pulse duration
    float distanceCm; // Variable to store the calculated distance

    // Clear the trigPin to ensure a clean pulse
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);

    // Trigger the sensor with a 10 microsecond pulse
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);

    // Measure the duration of the echo pulse
    duration = pulseIn(echoPin, HIGH, 30000); // 30ms timeout for max range (~5 meters)

    if (duration == 0) {
      Serial.println("Error: Echo signal not received within timeout.");
      // If no echo is received within the timeout, return -1
      return -1;
    }

    // Calculate the distance in centimeters
    distanceCm = duration * 0.034 / 2;

    // Ensure the distance is within the sensor's valid range (2cm to 400cm)
    if (distanceCm < 2 || distanceCm > 400) {
      Serial.println("Error: Object out of range (2cm - 400cm).");
      // Return -1 if the measured distance is out of range
      return -1;
    }

    // Return the valid distance measurement
    Serial.print(distanceCm);
    return distanceCm;
  }
};

#endif
