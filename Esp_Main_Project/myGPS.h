// GPS module for location

#include <TinyGPS++.h>
#include <SoftwareSerial.h>

class myGPS {
private:
  int rxPin, txPin;
  SoftwareSerial ss;
  TinyGPSPlus gps;

public:
  myGPS(int rx, int tx) : rxPin(rx), txPin(tx), ss(rx, tx) {}

  void setup() {
    ss.begin(9600);
  }

  String getLocation() {
    while (ss.available() > 0) {
      gps.encode(ss.read());
    }

    if (gps.location.isValid()) {
      String lat = String(gps.location.lat(), 6);
      String lng = String(gps.location.lng(), 6);
      return lat + ", " + lng;
    } else {
      return "INVALID";
    }
  }

  String getDateTime() {
    if (gps.date.isValid() && gps.time.isValid()) {
      int hour = gps.time.hour() + 5;
      if (hour >= 24) hour -= 24;
      if (hour < 0) hour += 24;

      bool isPM = hour >= 12;
      if (hour > 12) hour -= 12;
      if (hour == 0) hour = 12;

      String ampm = isPM ? "PM" : "AM";
      String dateTime = String(gps.date.month()) + "/" + String(gps.date.day()) + "/" + String(gps.date.year()) + " " +
                        String(hour) + ":" + String(gps.time.minute()) + ":" + String(gps.time.second()) + " " + ampm;
      return dateTime;
    } else {
      return "INVALID";
    }
  }
};
