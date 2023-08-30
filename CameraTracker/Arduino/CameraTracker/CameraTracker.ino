//  Based on Nilheim Mechatronics Simplified Eye Mechanism Code

//  Make sure you have the Adafruit servo driver library installed >>>>> https://github.com/adafruit/Adafruit-PWM-Servo-Driver-Library
//  Manual controls for the eye mechanism
//  X-axis joystick pin: A1->A0
//  Y-axis joystick pin: A0->A1
//  Trim potentiometer pin: A2
//  Button pin: 2

// App control requires the SerialTransfer library
#include "SerialTransfer.h"
#include "timed_trigger.h"

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

SerialTransfer myTransfer;
TimedTrigger blink_trigger(2500, 100);

struct EyeData
{
  float cam_x;
  float cam_y;
  float eye_x;
  float eye_y;
  uint8_t blink; // Use uint8_t for the boolean
} eyeData;
 

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define SERVOMIN  140 // this is the 'minimum' pulse length count (out of 4096)
#define SERVOMAX  520 // this is the 'maximum' pulse length count (out of 4096)

// pwm.setPWM(0, 0, 350); // X axis
// pwm.setPWM(1, 0, 350); // Y axis
// pwm.setPWM(2, 0, 400); // Upper left lid
// pwm.setPWM(3, 0, 240); // Lower left lid
// pwm.setPWM(4, 0, 240); // Upper right lid
// pwm.setPWM(5, 0, 400); // Lower right lid
// pwm.setPWM(6, 0, 350); // Neck X axis
// pwm.setPWM(7, 0, 350); // Neck Y axis

int xval = 512;
int yval = 512;

int lexpulse;
int leypulse;

int uplidpulse;
int lolidpulse;
int altuplidpulse;
int altlolidpulse;

int uplidpulse_prev;
int lolidpulse_prev;
int altuplidpulse_prev;
int altlolidpulse_prev;

int trimval;

// neck axis with smoothing
int neck_cur_x = 350;
int neck_cur_y = 350;
int neck_next_x = 350;
int neck_next_y = 350;
float neck_x_smoothing = 0.95;
float neck_y_smoothing = 0.95;

int xval_next = 512;
int yval_next = 512;
float xval_smoothing = 0.2;
float yval_smoothing = 0.2;

const int analogInPin = A0;
int sensorValue = 0;
int outputValue = 0;
int switchval = 0;

const int SwitchPin = 2;
void setup() {
  Serial.begin(115200);
  myTransfer.begin(Serial);
  Serial.println("Animatronics Eye Mechanism online.");
  pinMode(analogInPin, INPUT);
  pinMode(SwitchPin, INPUT_PULLUP);
  Wire.begin();
  pwm.begin();
  
  pwm.setPWMFreq(60);  // Analog servos run at ~60 Hz updates

  delay(10);
}

// a function which smooth data
int smooth(int new_data, int prev_data, float smoothing_factor) {
  return smoothing_factor * prev_data + (1 - smoothing_factor) * new_data;
}

// you can use this function if you'd like to set the pulse length in seconds
// e.g. setServoPulse(0, 0.001) is a ~1 millisecond pulse width. its not precise!
void setServoPulse(uint8_t n, double pulse) {
  double pulselength;
  
  pulselength = 1000000;   // 1,000,000 us per second
  pulselength /= 60;   // 60 Hz
  Serial.print(pulselength); Serial.println(" us per period"); 
  pulselength /= 4096;  // 12 bits of resolution
  Serial.print(pulselength); Serial.println(" us per bit"); 
  pulse *= 1000000;  // convert to us
  pulse /= pulselength;
  Serial.println(pulse);

}

int control_counter = 0;
int control_counter_threshold = 10;
bool blink = false;
void loop() {
  if(myTransfer.available())
  {
    // Read the received bytes into the struct
    myTransfer.rxObj(eyeData);
    
    // Print the received values
    // Serial.print("cam_x: "); Serial.print(eyeData.cam_x, 4);
    // Serial.print("cam_y: "); Serial.print(eyeData.cam_y, 4);
    // Serial.print("eye_x: "); Serial.print(eyeData.eye_x, 4);
    // Serial.print("eye_y: "); Serial.print(eyeData.eye_y, 4);
    // Serial.print("blink: "); Serial.println(eyeData.blink ? "true" : "false");
    
    xval_next = eyeData.eye_x;
    yval_next = 1023 - eyeData.eye_y;
    
    xval = smooth(xval_next, xval, xval_smoothing); // smoothen the eye movement
    yval = smooth(yval_next, yval, yval_smoothing);
    // Serial.print("xval_next: "); Serial.print(xval_next);
    // Serial.print(" xval: "); Serial.println(xval);
    
    // switchval = eyeData.blink;
    switchval = HIGH;
    trimval = 520; //analogRead(A2);
    
    //reset control counter
    control_counter = 0;
  } 
  else {
    if(myTransfer.status < 0)
    {
      Serial.print("ERROR: ");
      Serial.println(myTransfer.status);
      Serial.println("Using manual control.");
    }
    control_counter++;
    if (control_counter > control_counter_threshold) { 
      // if no data received for a while, switch to manual control
      xval = analogRead(A1);
      yval = analogRead(A0);
      switchval = digitalRead(SwitchPin);
      //switchval = LOW;    
      trimval = 520; //analogRead(A2);
    }
  }
  
  lexpulse = map(xval, 0,1023, 220, 440);
  leypulse = map(yval, 0,1023, 250, 450);
  
  uplidpulse_prev = uplidpulse;
  lolidpulse_prev = lolidpulse;
  altuplidpulse_prev = altuplidpulse;
  altlolidpulse_prev = altlolidpulse;

  // trimval=map(trimval, 320, 580, -40, 40);
  // trimval=0;
  uplidpulse = map(yval, 0, 1023, 400, 280);
  // uplidpulse -= (trimval-40);
  uplidpulse = constrain(uplidpulse, 280, 400);
  altuplidpulse = 680-uplidpulse;

  lolidpulse = map(yval, 0, 1023, 400, 280);
  // lolidpulse += (trimval/2);
  lolidpulse = constrain(lolidpulse, 280, 400);      
  altlolidpulse = 680-lolidpulse;

  // uplidpulse = smooth(uplidpulse, uplidpulse_prev, 0.5);
  // lolidpulse = smooth(lolidpulse, lolidpulse_prev, 0.5);
  // altuplidpulse = smooth(altuplidpulse, altuplidpulse_prev, 0.5);
  // altlolidpulse = smooth(altlolidpulse, altlolidpulse_prev, 0.5);
  
  Serial.print("xval: "); Serial.print(xval);
  Serial.print(" yval: "); Serial.print(yval);
  Serial.print(" lex: "); Serial.print(lexpulse);
  Serial.print(" ley: "); Serial.print(leypulse);
  Serial.print(" uplid: "); Serial.print(uplidpulse);
  Serial.print(" lolid: "); Serial.print(lolidpulse);
  Serial.print(" altupli: "); Serial.print(altuplidpulse);
  Serial.print(" altloli: "); Serial.println(altlolidpulse);

  pwm.setPWM(0, 0, lexpulse);
  pwm.setPWM(1, 0, leypulse);
  
  // Timed blink
  blink = blink_trigger.Update();
  if (!blink) {
    switchval = LOW;
  }
  // switchval = LOW;
  if (switchval == LOW) {
  pwm.setPWM(2, 0, 400);
  pwm.setPWM(3, 0, 280);
  pwm.setPWM(4, 0, 280);
  pwm.setPWM(5, 0, 400);
  }
  else if (switchval == HIGH) {
  pwm.setPWM(2, 0, uplidpulse);
  pwm.setPWM(3, 0, lolidpulse);
  pwm.setPWM(4, 0, altuplidpulse);
  pwm.setPWM(5, 0, altlolidpulse);
  }

  // Neck axis smoothing
  neck_next_x = map(xval, 0,1023, 250, 450);
  neck_next_y = map(yval, 1023, 0, 320, 380);
  double error_x = neck_next_x - neck_cur_x; // Calculate the error term
  double error_y = neck_next_y - neck_cur_y; // Calculate the error term
  double correction_factor = 1.0; // Set the correction factor

  neck_cur_x = neck_x_smoothing * neck_cur_x + (1 - neck_x_smoothing) * (neck_next_x + correction_factor * error_x);
  neck_cur_y = neck_y_smoothing * neck_cur_y + (1 - neck_y_smoothing) * (neck_next_y + correction_factor * error_y);  
  pwm.setPWM(6, 0, neck_cur_x);
  pwm.setPWM(7, 0, neck_cur_y);
  
  // Serial.print(xval);
  // Serial.print(", ");
  // Serial.println(yval);
  
  delay(5);
}

