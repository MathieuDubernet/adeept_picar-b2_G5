import spidev
import numpy
from numpy import sin, cos, pi

class Adeept_SPI_LedPixel:

    # Définition d'un dictionnaire de couleurs pour les LED, associant les lettres R, G, B et N à leurs valeurs RGB correspondantes.
    colors = {
    "R": [255, 0, 0],
    "G": [0, 255, 0],
    "B": [0, 0, 255],
    "N": [0, 0, 0],
    }

    # Initialisation de la classe Adeept_SPI_LedPixel.
    def __init__(self, count = 14, bright = 255, sequence='GRB', bus = 0, device = 0):
        self.set_led_type(sequence)
        self.set_led_count(count)
        self.set_led_brightness(bright)
        self.led_begin(bus, device)
        self.set_all_led_color(0,0,0)

    def led_begin(self, bus = 0, device = 0):
        """
        Initialise la communication SPI avec les LED WS2812. Configure le bus et le périphérique SPI, et gère les erreurs potentielles liées à la configuration du Raspberry Pi.
        
        Paramètres:
        - bus: Numéro du bus SPI (par défaut 0)
        - device: Numéro du périphérique SPI (par défaut 0)
        """
        self.bus = bus
        self.device = device
        try:
            self.spi = spidev.SpiDev()
            self.spi.open(self.bus, self.device)
            self.spi.mode = 0
            self.led_init_state = 1
        except OSError:
            print("Please check the configuration in /boot/firmware/config.txt.")
            if self.bus == 0:
                print("You can turn on the 'SPI' in 'Interface Options' by using 'sudo raspi-config'.")
                print("Or make sure that 'dtparam=spi=on' is not commented, then reboot the Raspberry Pi. Otherwise spi0 will not be available.")
            else:
                print("Please add 'dtoverlay=spi{}-2cs' at the bottom of the /boot/firmware/config.txt, then reboot the Raspberry Pi. otherwise spi{} will not be available.".format(self.bus, self.bus))
            self.led_init_state = 0


    def led_close(self):
        """
        Ferme la communication SPI et éteint toutes les LED en réglant leur couleur sur noir (0, 0, 0). Utilise la méthode set_all_led_rgb pour éteindre les LED avant de fermer la connexion SPI.
        """
        self.set_all_led_rgb([0,0,0])
        self.spi.close()
    
    def set_led_count(self, count):
        """
        Définit le nombre de LED dans la bande LED WS2812. Initialise les listes led_color et led_original_color en fonction du nombre de LED spécifié, en les remplissant de valeurs initiales (0, 0, 0) pour chaque LED.
        
        Paramètres:
        - count: Nombre de LED dans la bande
        """
        self.led_count = count
        self.led_color = [0,0,0] * self.led_count
        self.led_original_color = [0,0,0] * self.led_count

    def set_led_type(self, rgb_type):
        """
        Définit le type de LED en fonction de la séquence de couleurs spécifiée (RGB, GRB, etc.). Utilise des listes pour déterminer les offsets de couleur rouge, verte et bleue en fonction de la séquence choisie. Si la séquence n'est pas valide, définit les offsets par défaut et retourne -1.
        
        Paramètres:
        - rgb_type: Type de LED ('RGB', 'GRB', 'RBG', 'GBR', 'BRG', 'BGR')
        """
        try:
            led_type = ['RGB','RBG','GRB','GBR','BRG','BGR']
            led_type_offset = [0x06,0x09,0x12,0x21,0x18,0x24]
            index = led_type.index(rgb_type)
            self.led_red_offset = (led_type_offset[index]>>4) & 0x03
            self.led_green_offset = (led_type_offset[index]>>2) & 0x03
            self.led_blue_offset = (led_type_offset[index]>>0) & 0x03
            return index
        except ValueError:
            self.led_red_offset = 1
            self.led_green_offset = 0
            self.led_blue_offset = 2
            return -1
    
    def set_led_brightness(self, brightness):
        """
        Règle la luminosité des LED. Prend une valeur de luminosité en entrée et ajuste les couleurs des LED en fonction de cette luminosité. Utilise la méthode set_led_rgb_data pour mettre à jour les couleurs des LED.
        
        Paramètres:
        - brightness: Valeur de luminosité (0-255)
        """
        self.led_brightness = brightness
        for i in range(self.led_count):
            self.set_led_rgb_data(i, self.led_original_color)

    def set_ledpixel(self, index, r, g, b):
        """
        Définit la couleur d'une LED spécifique en fonction de son index et des valeurs RGB fournies. Ajuste les couleurs en fonction de la luminosité définie et met à jour les listes led_color et led_original_color avec les nouvelles valeurs de couleur pour la LED spécifiée.
        
        Paramètres:
        - index: Index de la LED à configurer
        - r: Valeur rouge (0-255)
        - g: Valeur verte (0-255)
        - b: Valeur bleue (0-255)
        """
        p = [0,0,0]
        p[self.led_red_offset] = round(r * self.led_brightness / 255)
        p[self.led_green_offset] = round(g * self.led_brightness / 255)
        p[self.led_blue_offset] = round(b * self.led_brightness / 255)
        self.led_original_color[index*3+self.led_red_offset] = r
        self.led_original_color[index*3+self.led_green_offset] = g
        self.led_original_color[index*3+self.led_blue_offset] = b
        for i in range(3):
            self.led_color[index*3+i] = p[i]

    def set_led_color_data(self, index, r, g, b):
        """
        Définit la couleur d'une LED spécifique en fonction de son index et des valeurs RGB, sans mettre à jour l'affichage immédiatement. Utilise set_ledpixel mais n'appelle pas show pour afficher les changements.
        
        Paramètres:
        - index: Index de la LED
        - r: Valeur rouge (0-255)
        - g: Valeur verte (0-255)
        - b: Valeur bleue (0-255)
        """
        self.set_ledpixel(index, r, g, b)  

    def set_led_rgb_data(self, index, color):
        """
        Définit la couleur d'une LED spécifique en fonction de son index et d'une liste de valeurs RGB, sans mettre à jour l'affichage immédiatement. Utilise set_ledpixel mais n'appelle pas show.
        
        Paramètres:
        - index: Index de la LED
        - color: Liste [R, G, B] avec valeurs 0-255
        """
        self.set_ledpixel(index, color[0], color[1], color[2])   

    def set_led_rgb(self, index, color):
        """
        Définit la couleur d'une LED spécifique en fonction de son index et d'une liste de valeurs RGB, puis met à jour l'affichage immédiatement. Utilise set_led_rgb_data et appelle show.
        
        Paramètres:
        - index: Index de la LED
        - color: Liste [R, G, B] avec valeurs 0-255
        """
        self.set_led_rgb_data(index, color)   
        self.show() 
    
    def set_all_led_color(self, r, g, b):
        """
        Définit la même couleur pour toutes les LED en fonction des valeurs RGB, puis met à jour l'affichage immédiatement. Utilise set_led_color_data et appelle show pour afficher les changements.
        
        Paramètres:
        - r: Valeur rouge (0-255)
        - g: Valeur verte (0-255)
        - b: Valeur bleue (0-255)
        """
        for i in range(self.led_count):
            self.set_led_color_data(i, r, g, b)
        self.show()

    def set_all_led_rgb(self, color):
        """
        Définit la même couleur pour toutes les LED en fonction d'une liste de valeurs RGB, puis met à jour l'affichage immédiatement. Utilise set_led_rgb_data et appelle show.
        
        Paramètres:
        - color: Liste [R, G, B] avec valeurs 0-255
        """
        for i in range(self.led_count):
            self.set_led_rgb_data(i, color) 
        self.show()

    def write_ws2812_numpy8(self):
        """
        Convertit les données de couleur des LED en un format compatible avec le protocole SPI utilisé par les LED WS2812. Utilise la bibliothèque numpy pour manipuler les données de couleur et préparer les données à envoyer via SPI en fonction des timings spécifiques requis par les LED WS2812 (8 bits par pixel).
        """
        d = numpy.array(self.led_color).ravel()        #Converts data into a one-dimensional array
        tx = numpy.zeros(len(d)*8, dtype=numpy.uint8)  #Each RGB color has 8 bits, each represented by a uint8 type data
        for ibit in range(8):                          #Convert each bit of data to the data that the spi will send
            tx[7-ibit::8]=((d>>ibit)&1)*0x78 + 0x80    #T0H=1,T0L=7, T1H=5,T1L=3   #0b11111000 mean T1(0.78125us), 0b10000000 mean T0(0.15625us)  
        if self.led_init_state != 0:
            if self.bus == 0:
                self.spi.xfer(tx.tolist(), int(8/1.25e-6))         #Send color data at a frequency of 6.4Mhz
            else:
                self.spi.xfer(tx.tolist(), int(8/1.0e-6))          #Send color data at a frequency of 8Mhz

    def write_ws2812_numpy4(self):
        """
        Convertit les données de couleur des LED en un format compatible avec le protocole SPI utilisé par les LED WS2812, en utilisant une approche différente pour représenter les bits de données. Utilise numpy pour préparer les données à envoyer via SPI (4 bits par pixel) avec une représentation différente (T0H=0x06, T0L=0x60, T1H=0x60, T1L=0x06).
        """
        d=numpy.array(self.led_color).ravel()
        tx=numpy.zeros(len(d)*4, dtype=numpy.uint8)
        for ibit in range(4):
            tx[3-ibit::4]=((d>>(2*ibit+1))&1)*0x60 + ((d>>(2*ibit+0))&1)*0x06 + 0x88  
        if self.led_init_state != 0:
            if self.bus == 0:
                self.spi.xfer(tx.tolist(), int(4/1.25e-6))         
            else:
                self.spi.xfer(tx.tolist(), int(4/1.0e-6))       

    def show(self, mode = 1):
        """
        Affiche les couleurs des LED en utilisant la méthode de conversion de données appropriée en fonction du mode spécifié. Appelle soit write_ws2812_numpy8, soit write_ws2812_numpy4 pour envoyer les données de couleur via SPI en fonction du mode sélectionné.
        
        Paramètres:
        - mode: Mode d'affichage (1 pour 8 bits, autre pour 4 bits)
        """
        if mode == 1:
            write_ws2812 = self.write_ws2812_numpy8
        else:
            write_ws2812 = self.write_ws2812_numpy4
        write_ws2812()



       
    """
    Méthode pour définir la couleur d'une LED spécifique en fonction de son index, de la couleur choisie et de la luminosité. Elle vérifie si le numéro de LED est valide (entre 1 et 14) et si la couleur choisie est présente dans le dictionnaire de couleurs. Si les conditions sont remplies, elle ajuste les valeurs RGB en fonction de la luminosité spécifiée et utilise la méthode set_led_rgb pour mettre à jour la couleur de la LED correspondante. Si les conditions ne sont pas remplies, un message d'erreur est affiché pour informer l'utilisateur des entrées invalides.
    arguments:

    - choosenLed: Le numéro de la LED à allumer (entre 1 et 14).
    - choosenColor: La couleur à afficher sur la LED, représentée par une lettre (R, G, B, N).
    - brightness: La luminosité de la LED (entre 0 et 255).

    """
    def set_one_led(self, choosenLed, choosenColor, brightness=255):
        
        if 1 <= choosenLed <= 14 and choosenColor in self.colors:
            scaled_colors = [round(c * brightness / 255) for c in self.colors[choosenColor]]
            self.set_led_rgb(choosenLed - 1, scaled_colors)
            
        else:
            print("\033[1;31m Invalid input. Please enter a number between 1 and 14 for the LED and a color (R, G, B, N).\033[0m")


"""

Fonction principale qui crée une instance de la classe Adeept_SPI_LedPixel
avec 14 LED et une luminosité maximale de 255.
Elle utilise une boucle pour permettre à l'utilisateur de saisir le numéro de la LED,
la couleur et la luminosité souhaités. Les entrées sont vérifiées pour s'assurer qu'elles sont valides,
et si elles le sont, la méthode set_one_led est appelée pour mettre à jour la couleur de la LED correspondante. 
Si l'utilisateur interrompt le programme (par exemple, en appuyant sur Ctrl+C), la méthode led_close est appelée 
pour éteindre les LED et fermer la communication SPI proprement.

"""
if __name__ == '__main__':
    leds = Adeept_SPI_LedPixel(14, 255)   
    try:
        
        value = 1
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
            leds.set_one_led(int(choosenLed), choosenColor, int(choosenBrightness))
    except KeyboardInterrupt:
        leds.led_close()