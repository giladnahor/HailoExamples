#include "SerialTransfer.h"

SerialTransfer myTransfer;

struct EyeData
{
  float cam_x;
  float cam_y;
  float eye_x;
  float eye_y;
  uint8_t blink; // Use uint8_t for the boolean
} eyeData;

void setup()
{
  Serial.begin(115200);
  myTransfer.begin(Serial);
}

void loop()
{
  if(myTransfer.available())
  {
    // Read the received bytes into the struct
    myTransfer.rxObj(eyeData);
    
    // Print the received values
    Serial.print("cam_x: "); Serial.println(eyeData.cam_x, 4);
    Serial.print("cam_y: "); Serial.println(eyeData.cam_y, 4);
    Serial.print("eye_x: "); Serial.println(eyeData.eye_x, 4);
    Serial.print("eye_y: "); Serial.println(eyeData.eye_y, 4);
    Serial.print("blink: "); Serial.println(eyeData.blink ? "true" : "false");
    
    // Send a response back to Python
    Serial.println("Data received!");
  }
  
  if(myTransfer.status < 0)
  {
    Serial.print("ERROR: ");
    Serial.println(myTransfer.status);
  }
}
