#import serial
from os import system
from subprocess import Popen, PIPE
from time import sleep
import unittest

from os import makedirs
from os.path import dirname, abspath, exists
here = dirname(abspath(__file__))


def msg(text):
    print ">>>>>>>>>>>>>>>", text, "<<<<<<<<<<<<<<<<<"


def systemOut(cmdList, sayCmd=True, giveStatus=False):
    '''Run a command and capture the output.'''
    if sayCmd:
        print "$", " ".join(cmdList)
    process = Popen(cmdList, stdout=PIPE)
    if giveStatus:
        return process.communicate()[0], process.returncode
    return process.communicate()[0]

devices = [x for x in systemOut(["ls", "/dev/"], sayCmd=False).split('\n')
           if len(x) > 0 and "ACM" in x]
if len(devices) == 0:
    raise IOError('No /dev/ttyACM* device found.')
else:
    for i, dev in enumerate(devices):
        if "ACM" in dev:
            port = "/dev/%s" % dev.strip()
del i, dev, devices
msg("port is %s" % port)
board = "arduino:avr:mega"
baudRate = 9600


def stripOutput(stdout):
    ignoreStrings = [
        "Loading configuration",
        "Initializing packages",
        "Preparing boards",
        "Sketch uses",
        "Global variables use",
        ]
    for l in stdout.split('\n'):
        isBad = False
        for bad in ignoreStrings:
            if bad in l or len(l.strip()) == 0:
                isBad = True
        if not isBad:
            print l
    

def verify(sketchName):
    cmd = "arduino --port %s --board %s" % (port, board)
    cmd += " --verify %s/%s/%s.ino"  % (here, sketchName, sketchName)
    
    stdout, status = systemOut(cmd.split(' '), sayCmd=False, giveStatus=True)
    if status:
        raise VerifyError
    else:
        stripOutput(stdout)
        return  status


def upload(sketchName):
    cmd = "arduino --port %s --board %s" % (port, board)
    cmd += " --upload %s/%s/%s.ino" % (here, sketchName, sketchName)
    
    stdout, status = systemOut(cmd.split(' '), sayCmd=False, giveStatus=True)
    if status:
        raise UploadError
    else:
        stripOutput(stdout)
        return  status


def monitor():
    print "To exit the serial monitor, do \"Ctrl+a, k, y\"."
    cmd = "gnome-terminal --disable-factory --command \"screen %s %s\" 2>&1 | grep -v \"format string\"" % (port, baudRate)
    system(cmd)


def printInstructions(instructions):
    prefix = " >>>     "
    lines = instructions.split('\n')
    print "Inspection instructions:"
    for line in lines:
        print "%s %s" % (prefix, line.replace('\n', ''))


def yn(prompt):
    '''stackoverflow.com/questions/3041986
    raw_input returns the empty string for "enter"'''
    yes = set(['yes','y', 'ye'])
    no = set(['no','n'])
    print prompt
    while True:
        choice = raw_input().lower()
        if choice in yes:
            return True
        elif choice in no:
            return False
        else:
            print "Please respond with '[y]es' or '[n]o'."


class InspectionError(RuntimeError):
    pass


class UploadError(RuntimeError):
    pass


class VerifyError(RuntimeError):
    pass


class Sketch:
    '''Contains and places Arduino code for compilation and uploading.'''
    
    def __init__(self):
        self.instructions = None
        self.code = None
        self.madeFiles = False
    
    def getCode(self):
        return self.code
    
    def getInstructions(self):
        return self.instructions
    
    def makeFiles(self):
        sketchDir = here+'/testSketch'
        if not exists(sketchDir): makedirs(sketchDir)
        f = open(sketchDir+'/testSketch.ino', 'w')
        f.write(self.getCode())
        f.close()
    
    def verify(self):
        return verify('testSketch')
            
    def upload(self):
        return upload('testSketch')

    def doTest(self, doMonitor=True):
        self.makeFiles()
        self.verify()
        out = self.upload()
        print "upload out:", out
        if doMonitor:
            printInstructions(self.instructions)
            monitor()
            monitorPassed = yn("Did the test pass inspection?")
            if not monitorPassed:
                raise InspectionError
        

class TestGunnar(unittest.TestCase):
    '''Upload various sketches. Manually check the behavior.'''

    def test_positionPID(self):
        sk = Sketch()
        sk.code = '''
#include <Wire.h>
#include <Servo.h>
#include <gunnar.h>

Gunnar gunnar;

// Interrupt Service Routines
void doEncoder0()
{
    gunnar.encoder0.update();
}

void doEncoder1()
{
    gunnar.encoder1.update();
}

// Test the motors, encoders, and PID control of position.
void setup() {
    
    Serial.begin(9600);
    gunnar.init();
    
    // Turn on pullup resistors on interrupt lines:
    pinMode(encoder0Int, INPUT_PULLUP);
    pinMode(encoder0Int, INPUT_PULLUP);
    attachInterrupt(0, doEncoder0, CHANGE);
    attachInterrupt(1, doEncoder1, CHANGE);
    
    gunnar.controlledMotors.stop();
}

void sayPosition()
{
    Serial.print("Positions are (");
    Serial.print(gunnar.encoder0.position);
    Serial.print(", ");
    Serial.print(gunnar.encoder1.position);
    Serial.println(") ticks.");
}

void loop()
{
    Serial.println("Begin position PID control test loop.");
    gunnar.controlledMotors.go(100);
    sayPosition();
    gunnar.controlledMotors.go(-200);
    sayPosition();
    gunnar.controlledMotors.go(600);
    sayPosition();
    gunnar.controlledMotors.stop();
    delay(3000);
}'''
        sk.instructions = '''
0. Ensure that green activity switch is on.
1. Motors will run by control to several positions,
   then declare what position they think they're at.
2. Assert that they don't run forever,
   and that the set points are reached expeditiously.
3. If ambitions, measure the distances traveled and assert that they are
   100 cm, -200 cm, and 600 cm.
4. After running to these positions, the motors will stop for 3 seconds.'''
        sk.doTest()
        
    def test_daguMotorBoard(self):
        sk = Sketch()
        sk.code = '''
#include <Servo.h>
#include <gunnar.h>
const int daguPwmPin1 = 11;
const int daguPwmPin2 = 12;

const int daguDirPin1 = 44;
const int daguDirPin2 = 45;

const int daguCurPin1 = A0;
const int daguCurPin2 = A1;

void setup()
{
    Serial.begin(9600);
    Serial.println("dagu motor board test");
    pinMode(daguPwmPin1, OUTPUT);
    pinMode(daguPwmPin2, OUTPUT);
    pinMode(daguDirPin1, OUTPUT);
    pinMode(daguDirPin2, OUTPUT);
    pinMode(daguCurPin1, INPUT);
    pinMode(daguCurPin2, INPUT);
}

void rampUpDown(boolean direction)
{
    
    Serial.print("Writing "); Serial.print(direction);
    Serial.print(" to pin "); Serial.print(daguDirPin1); Serial.println(".");
    Serial.print("Writing "); Serial.print(direction);
    Serial.print(" to pin "); Serial.print(daguDirPin2); Serial.println(".");

    digitalWrite(daguDirPin1, direction);
    digitalWrite(daguDirPin2, direction);
    
    uint8_t speed;

    for(speed=0; speed<255; speed++)
    {
        Serial.print("increasing: ");
        Serial.print(speed);
        Serial.print(" ");
        Serial.print(analogRead(daguCurPin1));
        Serial.print(" ");
        Serial.println(analogRead(daguCurPin2));
        analogWrite(daguPwmPin1, speed);
        analogWrite(daguPwmPin2, speed);
        delay(4);
    }
    
    for(speed=254; speed>=1; speed--)
    {
        Serial.print("decreasing: ");
        Serial.print(speed);
        Serial.print(" ");
        Serial.print(analogRead(daguCurPin1));
        Serial.print(" ");
        Serial.println(analogRead(daguCurPin2));
        analogWrite(daguPwmPin1, speed);
        analogWrite(daguPwmPin2, speed);
        delay(4);
    }  
}

void loop()
{
    rampUpDown(HIGH);
    rampUpDown(LOW);
}'''
        sk.instructions = '''
1. Let motors ramp up, then down twice.
2. Motors should go in opposite directions from each other at the same time.
3. Each motor should go first in one direction, then the other.'''
        sk.doTest()
        
    def test_motorObjectMovement(self):
        sk = Sketch()
        sk.code = r'''
#include <Servo.h>
#include <gunnar.h>

Gunnar gunnar;

void setup()
{
    Serial.begin(9600);
    gunnar.init();
}

void ramp(int start, int end)
{
    int i;
    Serial.print("ramp from ");
    Serial.print(start); Serial.print(" from "); Serial.print(end); Serial.println(".");
    
    if(start < end)
    {
        for(i=start; i<end; i++)
        {
            gunnar.motor1.setSpeed(i);
            gunnar.motor2.setSpeed(i);
            interruptibleDelay(4);
        }
    }
    else
    {
        for(i=start; i>end; i--)
        {
            gunnar.motor1.setSpeed(i);
            gunnar.motor2.setSpeed(i);
            interruptibleDelay(4);
        }
    }
    
}

void loop()
{
    ramp(0, 255);
    delay(500);
    ramp(255, -95);
    delay(500);
    ramp(-95, 0);
    gunnar.motor1.stop();
    gunnar.motor2.stop();
    delay(3000);
}'''
        sk.instructions = '''
1. Motors should ramp to a fast forward speed, then back to 0.
2. Motors should ramp to a slow reverse speed, then back to 0.
3. Repeats after a 3 second delay.'''
        sk.doTest()
        
    def test_encodersNoMotors(self):
        sk = Sketch()
        sk.code = '''
#include <Arduino.h>  // I don't know why this is necessary.
#include <Wire.h>
#include "constants.h"
#include "utils.h"
#include "encoders.h"
#include "motors.h"


// GLOBALS
Encoder encoder0;
Encoder encoder1;

void doEncoder0()
{
    encoder0.update();
}

void doEncoder1()
{
    encoder1.update();
}

const boolean explore = false;
// Test the motors and encoders.
void setup() {
    if(explore) // TODO: This is cruft.
    {
        Serial.begin(9600);
            
        boolean a = LOW;
        boolean b = LOW;
        
        uint8_t newStatus = a + 2*b;
        
        // backward looks like 0, 1, 2, 3
        // forward  looks like 0, 3, 2, 1
        
        int position = 0;
        uint8_t waveStatus = 2;
        
        switch(waveStatus)
        {
            case 0 :
                Serial.println("case 0");
                if(newStatus == 1)
                    position--;
                else
                    position++;
                break;
            case 1 :
                Serial.println("case 1");
                if(newStatus == 2)
                    position--;
                else
                    position++;
                break;
            case 2 :
                Serial.println("case 2");
                if(newStatus == 3)
                    position--;
                else
                    position++;
                break;
            case 3 :
                Serial.println("case 3");
                if(newStatus == 1)
                    position--;
                else
                    position++;
                break;
            default :
                break; // Should never reach here.
        }
        
        Serial.print("newStatus=");
        Serial.println(newStatus);
        Serial.print("position=");
        Serial.println(position);
    }
    else
    {
        Serial.begin(9600);
        
        encoder0.init(encoder0PinA, encoder0PinB, NULL);
        encoder1.init(encoder1PinA, encoder1PinB, NULL);
            
        // Turn on pullup resistors on interrupt lines:
        pinMode(encoder0Int, INPUT_PULLUP);
        pinMode(encoder1Int, INPUT_PULLUP);
        attachInterrupt(0, doEncoder0, CHANGE);
        attachInterrupt(1, doEncoder1, CHANGE);
        
        pinMode(PIN_ACTIVITYSWITCH, INPUT);
    }
}


void loop()
{
    if(explore)
    {
    }
    else
    {
        Serial.print(micros());
        Serial.print(", ");
        Serial.print(encoder0.getSpeed());
        Serial.print(", ");
        Serial.print(encoder1.getSpeed());
        Serial.print(", ");
        Serial.print(encoder0.position);
        Serial.print(", ");
        Serial.print(encoder1.position);
        Serial.print(", ");
        Serial.print(encoder0.trueUpdateDelay);
        Serial.print(", ");
        Serial.print(encoder1.trueUpdateDelay);
        Serial.println("");
        delayMicroseconds(1000000);
    }
}'''
        sk.instructions = '''
1. Push left and right treads independently forward and back.
2. Verify that the proper columns in the serial output go up and then go back down.
3. Make sure they can go into both positive and negative values.'''
        sk.doTest()
                
    def test_servos(self):
        sk = Sketch()
        sk.code = '''
#include <Servo.h> 
#include <gunnar.h>

Servo tiltServo; 
Servo panServo;

int pos = 0;

void setup() 
{ 
  Serial.begin(BAUDRATE);
  Serial.println("SERVO TEST");
  tiltServo.attach(TILTSERVOPIN);
  panServo.attach(PANSERVOPIN);
} 


const int MAXPOS = 120;
const int MINPOS = 40;
void loop() 
{ 
  Serial.println("          [          ]");
  Serial.print("Tilt test: ");
  for(pos = MINPOS; pos < MAXPOS; pos += 1)
  {
    tiltServo.write(pos);
    delay(15);
    if(pos%((MAXPOS-MINPOS)/5) == 0)
      Serial.print("|");
  } 
  for(pos = MAXPOS; pos>=MINPOS+1; pos-=1)
  {                                
    tiltServo.write(pos);
    delay(15);
    if(pos%((MAXPOS-MINPOS)/5) == 0)
        Serial.print("|");
  }
  Serial.println(" done.");

  Serial.println("          [         ]");
  Serial.print("Pan test:  ");
  for(pos = MINPOS; pos < MAXPOS; pos += 1)
  {
    panServo.write(pos);
    delay(25);
    if(pos%((MAXPOS-MINPOS)/5) == 0)
      Serial.print("|");
  } 
  for(pos = MAXPOS; pos>=MINPOS+11; pos-=1)
  {
    panServo.write(pos);
    delay(25);
    if(pos%((MAXPOS-MINPOS)/5) == 0)
      Serial.print("|");
  } 
  Serial.println(" done.");
}'''
        sk.instructions = '''
1. Verify that servos pan when output says they should be, and same for tilting.
2. Verify that movement is centered.'''
        sk.doTest()
        
    def test_servoObjects(self):
        sk = Sketch()
        sk.code = '''
#include <Wire.h>
#include <Servo.h>
#include <gunnar.h>
Gunnar gunnar;

void setup()
{
    Serial.begin(BAUDRATE);
    gunnar.init();
}

void loop() 
{ 
    int8_t angles[] = {-90, 0, 90};
    for(uint8_t i=0; i<3; i++)
    {
        int8_t angle = angles[i];
        Serial.print("angle=");
        Serial.println(angle);
        gunnar.sensors.setPan(angle);
        gunnar.sensors.setTilt(angle);
        delay(3000);
    }
}'''
        sk.instructions = '''
0. Ensure that battery power is available.
1. Servos will go to -90 degrees with calibrated offset, and pause for 3 seconds.
2. Servos will go to 0   degrees with calibrated offset, and pause for 3 seconds.
3. Servos will go to +90 degrees with calibrated offset, and pause for 3 seconds.'''
        sk.doTest()

    def test_servoCenter(self):
        sk = Sketch()
        sk.code = '''
#include <Servo.h> 
#include <gunnar.h>

Servo tiltServo; 
Servo panServo;

void setup() 
{ 
  Serial.begin(BAUDRATE);
  Serial.println("SERVO CENTERING TEST");
  tiltServo.attach(TILTSERVOPIN);
  panServo.attach(PANSERVOPIN);
} 

void loop() 
{ 
    uint8_t angles[] = {0, 90, 180};
    for(uint8_t i=0; i<3; i++)
    {
        uint8_t angle = angles[i];
        Serial.print("angle=");
        Serial.println(angle);
        panServo.write(angle);
        tiltServo.write(angle);
        delay(3000);
    }
}'''
        sk.instructions = '''
0. Ensure that battery power is available.
1. Servos will go to 0   degrees, and pause for 3 seconds.
2. Servos will go to 90  degrees, and pause for 3 seconds.
3. Servos will go to 180 degrees, and pause for 3 seconds.'''
        sk.doTest()
        
    @classmethod
    def tearDownClass(cls):
        sk = Sketch()
        sk.code = '''void setup() {                
  ;
}

void loop() {
  ;
}'''
        sk.doTest(doMonitor=False)
        
if __name__=="__main__":
#     docTestAll()
    unittest.main(verbosity=1000000)
#     t = TestKevrekidis()
#     t.test_chungLu()