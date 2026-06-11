#Mesurer l’état des 3 capteurs IR réflectifs
import time
from gpiozero import InputDevice

class Adeept_infrared:
    # Définition des broches GPIO pour les capteurs IR réflectifs
    line_pin_left = 22
    line_pin_middle = 27
    line_pin_right = 17

    # Initialisation des capteurs IR réflectifs
    def __init__(self):
        self.left = InputDevice(pin=self.line_pin_left)
        self.middle = InputDevice(pin=self.line_pin_middle)
        self.right = InputDevice(pin=self.line_pin_right)

    """
    Fonction permettant de déterminer l'état des trois capteurs IR réflectifs (gauche, milieu, droite) et de retourner ces états sous forme de liste.
    """
    def read(self):
        """Retourne [gauche, milieu, droite] sous forme de booléens."""
        status_right = self.right.value
        status_middle = self.middle.value
        status_left = self.left.value
        return [status_left, status_middle, status_right]

# Exécution de la fonction read pour afficher les états des capteurs IR réflectifs
if __name__ == '__main__':
    infrared = Adeept_infrared()
    try:
      while 1:
        print(infrared.read())
        time.sleep(0.3)
    except KeyboardInterrupt:
        pass
