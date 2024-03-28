#include "SerialTransfer.h"

SerialTransfer myTransfer;

struct EyeData
{
  float cam_x;
  float cam_y;
  float eye_x;
  float eye_y;
  float blink;
  float mouth;
} eyeData;

struct ConfigData
{
  float auto_blink;
  float cam_x_p;
  float cam_x_i;
  float cam_x_d;
  float cam_y_p;
  float cam_y_i;
  float cam_y_d;
  float eye_x_p;
  float eye_x_i;
  float eye_x_d;
  float eye_y_p;
  float eye_y_i;
  float eye_y_d;
  float eye_open;
} configData;



void setup()
{
  Serial.begin(115200);
  myTransfer.begin(Serial);
}

void loop()
{
  if(myTransfer.available())
  {
    if (myTransfer.currentPacketID() == 0) {
      // Read the received bytes into the struct
      myTransfer.rxObj(eyeData);
      
      // Print the received values
      Serial.print("cam_x: "); Serial.println(eyeData.cam_x, 4);
      Serial.print("cam_y: "); Serial.println(eyeData.cam_y, 4);
      Serial.print("eye_x: "); Serial.println(eyeData.eye_x, 4);
      Serial.print("eye_y: "); Serial.println(eyeData.eye_y, 4);
      Serial.print("blink: "); Serial.println(eyeData.blink, 4);
      Serial.print("mouth: "); Serial.println(eyeData.mouth, 4);
      
      // Send a response back to Python
      Serial.println("Data received!");
    }
    else if (myTransfer.currentPacketID() == 1) {
      // Read the received bytes into the struct
      myTransfer.rxObj(configData);
      
      // Print the received values
      Serial.print("auto_blink: "); Serial.println(configData.auto_blink, 4);
      
      // Send a response back to Python
      Serial.println("Data received!");
    }
    else {
      Serial.println("ERROR: Packet ID not recognized!");
    }
  }

  
  if(myTransfer.status < 0)
  {
    Serial.print("ERROR: ");
    Serial.println(myTransfer.status);
  }
}
