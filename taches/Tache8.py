import time
import smbus
from Tache3 import ServoController

class ADS7830(object):
    def __init__(self, controller):
        self.cmd = 0x84
        self.bus=smbus.SMBus(1)
        self.address = 0x48
        self.controller = controller
        
        
    def analogRead(self, chn):
        value = self.bus.read_byte_data(self.address, self.cmd|(((chn<<2 | chn>>1)&0x07)<<4))
        return value
    
    def calculatePercentageLight(self, adc_value):
        percentage = (adc_value / 255) * 100
        return percentage

    def turnWheelsToLight(self):
        adc_value = self.analogRead(1)
        percentage = self.calculatePercentageLight(adc_value)
        
        value = (90+70) * (percentage/100) + 10 # On ajoute 50 parce que notre angle centré est 140 et pas 90
        angle = 180-int(round(value / 10) * 10) # (90+50)*2
        
        self.controller.setAngle(0, angle) # CH0 pour les roues
        
        return angle



if __name__ == "__main__":
    controller = ServoController()
    adc = ADS7830(controller)

    try:
        while True:
            print("angle : ", adc.turnWheelsToLight())
            time.sleep(0.1)
            pass

    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur.")
    finally:
        controller.cleanup()
        print("Nettoyage des ressources...")

