from gpiozero import DistanceSensor
from time import sleep
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685


class AdeeptUltra:

    TRIG_PIN = 23
    ECHO_PIN = 24

    def __init__(self):
        # Capteur ultrason
        self.sensor = DistanceSensor(
            echo=self.ECHO_PIN,
            trigger=self.TRIG_PIN,
            max_distance=2          # Maximum detection distance 2m.
        )

    def checkdist(self):
        return self.sensor.distance * 100

if __name__ == "__main__":
    ultra = AdeeptUltra()
    while True:
        distance = ultra.checkdist() 
        print("%.2f cm" %distance)
        sleep(0.05)