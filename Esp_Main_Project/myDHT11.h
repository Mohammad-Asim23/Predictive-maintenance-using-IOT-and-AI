#ifndef MYDHT11_H
#define MYDHT11_H

#include <DHTesp.h>

class myDHT11 {
private:
  int dataPin;
  DHTesp dht;

public:
  myDHT11(int pin) : dataPin(pin) {}

  void setup() {
    dht.setup(dataPin, DHTesp::DHT11);
  }

  float getTemperature() {
    return dht.getTemperature();
  }

  float getHumidity() {
    return dht.getHumidity();
  }
};

#endif
