import time
import smbus
from Tache3 import ServoController


class ADS7830(object):
    def __init__(self, controller):
        # Commande de base pour l'ADS7830
        self.cmd = 0x84

        # Ouverture du bus I2C principal du Raspberry Pi
        self.bus = smbus.SMBus(1)

        # Adresse I2C de l'ADS7830
        self.address = 0x48

        # Référence vers le contrôleur de servos
        self.controller = controller

    def analogRead(self, chn):
        """
        Lit la valeur analogique d'un canal de l'ADS7830.
        Retourne une valeur entre 0 et 255 (ADC 8 bits).
        """
        value = self.bus.read_byte_data(
            self.address,
            self.cmd | (((chn << 2 | chn >> 1) & 0x07) << 4)
        )
        return value

    def calculatePercentageLight(self, adc_value):
        """
        Convertit la valeur brute ADC en pourcentage de luminosité.
        0   -> 0%
        255 -> 100%
        """
        percentage = (adc_value / 255) * 100
        return percentage

    def turnWheelsToLight(self):
        """
        Lit la luminosité sur le canal 1, calcule un angle,
        puis oriente les roues vers cette direction.
        """
        adc_value = self.analogRead(1)
        percentage = self.calculatePercentageLight(adc_value)

        # Conversion du pourcentage en angle servo.
        # Ici on mappe la lumière vers une plage d'angle utile.
        value = (90 + 70) * (percentage / 100) + 50 + 10 # On ajoute 50 parce que notre angle centré est 140 et pas 90
        # Arrondi à la dizaine pour éviter trop de petites variations
        angle = 280 - int(round(value / 10) * 10) # 280 = 90*2 + 50*2

        # Commande du servo des roues sur le canal 0
        self.controller.setAngle(0, angle)

        return angle


if __name__ == "__main__":
    controller = ServoController()
    adc = ADS7830(controller)

    try:
        while True:
            # Lit la lumière, oriente les roues, puis affiche l'angle appliqué
            print("angle : ", adc.turnWheelsToLight())
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur.")
    finally:
        # Libération propre des ressources matérielles
        controller.cleanup()
        print("Nettoyage des ressources...")