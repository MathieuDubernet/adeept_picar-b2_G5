import time
from rpi_ws281x import *
import argparse

# Configuration de la bande LED :
LED_COUNT      = 14      # Nombre de pixels LED.
LED_PIN        = 12      # Broche GPIO reliée aux pixels (12 utilise le PWM matériel).
#LED_PIN        = 10     # Broche GPIO reliée aux pixels (10 utilise le SPI /dev/spidev0.0).
LED_FREQ_HZ    = 800000  # Fréquence du signal LED en hertz (généralement 800 kHz).
LED_DMA        = 10      # Canal DMA utilisé pour générer le signal (essayer 10).
LED_BRIGHTNESS = 100     # 0 = le plus sombre, 255 = le plus lumineux.
LED_INVERT     = False   # True pour inverser le signal (adaptation de niveau par transistor NPN).
LED_CHANNEL    = 0       # Mettre à 1 pour les GPIO 13, 19, 41, 45 ou 53.
colors = {
    "R": [255, 0, 0],
    "G": [0, 255, 0],
    "B": [0, 0, 255],
    "N": [0, 0, 0],
}

def setup():
  global strip
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--clear', action='store_true', help='clear the display on exit')
  args = parser.parse_args()

  # Création de l'objet NeoPixel avec la configuration appropriée.
  strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
  # Initialisation de la bibliothèque (à appeler une seule fois avant toute autre fonction).
  strip.begin()
  # strip.setBrightness(10) # 0~255, règle la luminosité de la LED RVB WS2812.

# Définition des fonctions qui animent les LED de différentes manières.
def colorWipe( R, G, B):
    """Balaye une couleur sur tout l'affichage, un pixel à la fois."""
    color = Color(R,G,B)
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()

# 
"""
Définition de la fonction qui pilote la LED choisie de la manière choisie.

Arguments:
name  – first namon, must be int
d     – to return Person as `dict` (default=False)

"""
def run(choosenLed, choosenColor, brightness=255):
    if 1 <= choosenLed <= 14 and choosenColor in colors:
        scaled_colors = [round(c * brightness / 255) for c in colors.get(choosenColor)]
        strip.setPixelColor(choosenLed -1, Color(*scaled_colors)) 
        strip.show() 
    else:
        print("\033[1;31m Invalid input. Please enter a number between 1 and 14 for the LED and a color (R, G, B, N).\033[0m")


def check_rpi_model():
    _, result = run_command("cat /proc/device-tree/model |awk '{print $3}'")
    result = result.strip()
    if result == '3':
        return 3
    elif result == '4':
        return 4
    elif result == '5':
        return 5
    else:
        return None

def run_command(cmd=""):
    import subprocess
    p = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    result = p.stdout.read().decode('utf-8')
    status = p.poll()
    return status, result
    
if __name__ == '__main__':
    try:
      value = 1
      rpi_model = check_rpi_model()
      if rpi_model == 5:
        print("\033[1;33m WS2812 officially does not support Raspberry Pi 5 for the time being, and the WS2812 LED cannot be used on Raspberry Pi 5.\033[0m")
        value = 0
      else:
        setup()
      while value!= 0:
       
        print("\033[1;34m Please enter the LED number (1-14) ")
        choosenLed = input()
        if not str(choosenLed).isdigit(): 
            print("\033[1;31m Invalid LED number. Please enter a number between 1 and 14.\033[0m")
            continue
        elif int(choosenLed) < 1 or int(choosenLed) > 14:
            print("\033[1;31m Invalid LED number. Please enter a number between 1 and 14.\033[0m")
            continue
        
        print("\033[1;34m Please enter the color (R, G, B, N) ")
        choosenColor = input().upper()
        print("\033[1;34m Please enter the brightness (0-255) ")
        choosenBrightness = input()
        if not str(choosenBrightness).isdigit(): 
            print("\033[1;31m Invalid brightness. Please enter a number between 0 and 255.\033[0m")
            continue
        elif int(choosenBrightness) < 0 or int(choosenBrightness) > 255:
            print("\033[1;31m Invalid brightness. Please enter a number between 0 and 255.\033[0m")
            continue
        run(int(choosenLed), choosenColor, int(choosenBrightness))
    except KeyboardInterrupt:
      colorWipe(0, 0, 0)