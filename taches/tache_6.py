#Mesurer l’état des 3 capteurs IR réflectifs
import time
from gpiozero import InputDevice

# Définition des broches GPIO pour les capteurs IR réflectifs
line_pin_left = 22
line_pin_middle = 27
line_pin_right = 17

# Initialisation des capteurs IR réflectifs
left = InputDevice(pin=line_pin_left)
middle = InputDevice(pin=line_pin_middle)
right = InputDevice(pin=line_pin_right)

"""
Fonction permettant de déterminer l'état des trois capteurs IR réflectifs (gauche, milieu, droite) et de retourner ces états sous forme de liste.
Returns:
Une liste contenant les états des capteurs dans l'ordre [gauche, milieu, droite], où chaque état est soit 0 (capteur non activé) soit 1 (capteur activé).

"""

def run():
    status_right = right.value
    status_middle = middle.value
    status_left = left.value
    return [status_left, status_middle, status_right]

# Exécution de la fonction run pour afficher les états des capteurs IR réflectifs
if __name__ == '__main__':
    try:
      while 1:
        print(run())
        time.sleep(0.3)
    except KeyboardInterrupt:
        pass


