// Based on https://learn.adafruit.com/multi-tasking-the-arduino-part-1/all-together-now
class TimedTrigger
{
	// Class Member Variables
	// These are initialized at startup
	long OnTimeBase; // milliseconds of on-time w/o random offset
	long OnTime;     // milliseconds of on-time
	long OffTime;    // milliseconds of off-time
  long RandomOffset;    // milliseconds of off-time

	// These maintain the current state
	int State;             		// State
	unsigned long previousMillis;  	// will store last time updated

  // Constructor - creates a TimedTrigger 
  // and initializes the member variables and state
  public:
  TimedTrigger(long on, long off, long random_offset = 2000)
  {
	  
	OnTimeBase = on;
  OffTime = off;
	RandomOffset = random_offset;
  OnTime = OnTimeBase + random(RandomOffset);
	
	State = LOW; 
	previousMillis = 0;
  }

  bool Update()
  {
    // check to see if it's time to change the state
    unsigned long currentMillis = millis();
     
    if((State == HIGH) && (currentMillis - previousMillis >= OnTime))
    {
    	State = LOW;  // Turn it off
      OnTime = OnTimeBase + random(RandomOffset);
	    previousMillis = currentMillis;  // Remember the time
    }
    else if ((State == LOW) && (currentMillis - previousMillis >= OffTime))
    {
      State = HIGH;  // turn it on
      previousMillis = currentMillis;   // Remember the time
    }
    return State;
  }
};