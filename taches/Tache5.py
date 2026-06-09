from gpiozero import DistanceSensor
from time import sleep
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

Tr = 23
Ec = 24
sensor = DistanceSensor(echo=Ec, trigger=Tr,max_distance=2) # Maximum detection distance 2m.

i2c = busio.I2C(SCL, SDA)
# Create a simple PCA9685 class instance.
pca = PCA9685(i2c, address=0x5f) #default 0x40
pca.frequency = 50

# Get the distance of ultrasonic detection.
def checkdist():
    return (sensor.distance) *100 # Unit: cm

def set_angle(ID, angle):
    servo_angle = servo.Servo(pca.channels[ID], min_pulse=500, max_pulse=2400,actuation_range=180)
    servo_angle.angle = angle

if __name__ == "__main__":
    set_angle(2, 80)  # Positionne le servo de tête à 90° (milieu)
    aller=True
    i = 30
    set_angle(1, i)  #coup
    
    while True:
        
        if aller:
            i += 5
            if i > 150:
                aller = False
        else:
            i -= 5
            if i < 30:
                aller = True
        set_angle(1, i)  #coup

        distance = checkdist() 
        print("%.2f cm" %distance)


        sleep(1)
