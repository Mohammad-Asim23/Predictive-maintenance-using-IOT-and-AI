// Water proof temprature measuring sensor

#include <OneWire.h>
#include <DallasTemperature.h>

class myDS18B20 {
private:
  int dataPin;
  OneWire oneWire;
  DallasTemperature sensors;

public:
  myDS18B20(int pin) : dataPin(pin), oneWire(pin), sensors(&oneWire) {}

  void setup() {
    sensors.begin();
  }

  float getValue() {
    sensors.requestTemperatures();
    return sensors.getTempCByIndex(0);
  }
};
