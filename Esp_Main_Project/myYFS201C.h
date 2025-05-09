#ifndef MY_YFS201C_H
#define MY_YFS201C_H

#include <Arduino.h>

class myYFS201C {
private:
  int flowPin;
  volatile int flowCount;

  static myYFS201C* instance; // Static instance pointer

  // Static ISR function to handle interrupt
  static void ICACHE_RAM_ATTR flowISR() {
    instance->flowCount++;
  }

public:
  myYFS201C(int pin) : flowPin(pin), flowCount(0) {
    instance = this; // Initialize static instance pointer
  }

  void setup() {
    pinMode(flowPin, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(flowPin), flowISR, RISING);
  }

  float getValue() {
    float flowRate = (flowCount / 7.5); // Example conversion, adjust as needed
    flowCount = 0; // Reset count
    return flowRate;
  }
};

// Define the static instance pointer
myYFS201C* myYFS201C::instance = nullptr;

#endif
