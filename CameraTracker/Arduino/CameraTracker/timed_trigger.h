// Based on https://learn.adafruit.com/multi-tasking-the-arduino-part-1/all-together-now
class TimedTrigger
{
	// Class Member Variables
	// These are initialized at startup
	long OffTimeBase; // milliseconds of off-time w/o random offset
	long OffTime;     // milliseconds of off-time
	long OnTime;    // milliseconds of on-time
  long RandomOffset;    // milliseconds of max random offset

	// These maintain the current state
	int State;             		// State
	unsigned long previousMillis;  	// will store last time updated
  int enabled = 1; //When disabled, will not switch to on state

  // Constructor - creates a TimedTrigger 
  // and initializes the member variables and state
  public:
  TimedTrigger(long on, long off, long random_offset = 2000)
  {
	  
	OffTimeBase = off;
  OnTime = on;
	RandomOffset = random_offset;
  OffTime = OffTimeBase + random(RandomOffset);
	
	State = LOW; 
	previousMillis = 0;
  }

  bool Update()
  {
    // check to see if it's time to change the state
    unsigned long currentMillis = millis();
     
    if((State == LOW) && enabled && (currentMillis - previousMillis >= OffTime))
    {
    	State = HIGH;  // Turn it on
	    previousMillis = currentMillis;  // Remember the time
    }
    else if ((State == HIGH) && (currentMillis - previousMillis >= OnTime))
    {
      State = LOW;  // turn it off
      OffTime = OffTimeBase + random(RandomOffset);
      previousMillis = currentMillis;   // Remember the time
    }
    return State;
  }

  bool setState(int state)
  {
    // Set State to required state and reset timer
    State = state;
    previousMillis = millis();   // Update time
    return State;
  }

  void Disable()
  {
    enabled = 0;
  }

  void Enable()
  {
    enabled = 1;
  }
};