import spidev
import threading  
import numpy
from numpy import sin, cos, pi
import time
class Adeept_SPI_LedPixel(threading.Thread):

    # Définition d'un dictionnaire de couleurs pour les LED, associant les lettres R, G, B et N à leurs valeurs RGB correspondantes.
    colors = {
    "R": [255, 0, 0],
    "G": [0, 255, 0],
    "B": [0, 0, 255],
    "N": [0, 0, 0],
    }

    # Initialisation de la classe Adeept_SPI_LedPixel, qui hérite de threading.Thread pour permettre l'exécution en parallèle.
    def __init__(self, count = 14, bright = 255, sequence='GRB', bus = 0, device = 0, *args, **kwargs):
        self.set_led_type(sequence)
        self.set_led_count(count)
        self.set_led_brightness(bright)
        self.led_begin(bus, device)
        self.lightMode = 'none'
        self.colorBreathR = 0
        self.colorBreathG = 0
        self.colorBreathB = 0
        self.breathSteps = 10
        #self.spi_gpio_info()
        self.set_all_led_color(0,0,0)
        super(Adeept_SPI_LedPixel, self).__init__(*args, **kwargs)
        self.__flag = threading.Event()
        self.__flag.clear()
    # Méthode pour initialiser la communication SPI avec les LED WS2812. Elle configure le bus et le périphérique SPI, et gère les erreurs potentielles liées à la configuration du Raspberry Pi.
    def led_begin(self, bus = 0, device = 0):
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

    # Méthode pour vérifier l'état de l'initialisation SPI. Elle retourne la variable led_init_state, qui indique si l'initialisation a réussi ou échoué.        
    def check_spi_state(self):
        return self.led_init_state
    
    # Méthode pour afficher les informations sur les broches GPIO utilisées pour la communication SPI en fonction du bus sélectionné. Elle fournit des détails sur les broches MOSI, MISO, SCLK et CE pour chaque bus SPI disponible.    
    def spi_gpio_info(self):
        if self.bus == 0:
            print("SPI0-MOSI: GPIO10(WS2812-PIN)  SPI0-MISO: GPIO9  SPI0-SCLK: GPIO11  SPI0-CE0: GPIO8  SPI0-CE1: GPIO7")
        elif self.bus == 1:
            print("SPI1-MOSI: GPIO20(WS2812-PIN)   SPI1-MISO: GPIO19  SPI1-SCLK: GPIO21  SPI1-CE0: GPIO18  SPI1-CE1: GPIO17  SPI0-CE1: GPIO16")
        elif self.bus == 2:
            print("SPI2-MOSI: GPIO41(WS2812-PIN)   SPI2-MISO: GPIO40  SPI2-SCLK: GPIO42  SPI2-CE0: GPIO43  SPI2-CE1: GPIO44  SPI2-CE1: GPIO45")
        elif self.bus == 3:
            print("SPI3-MOSI: GPIO2(WS2812-PIN)  SPI3-MISO: GPIO1  SPI3-SCLK: GPIO3  SPI3-CE0: GPIO0  SPI3-CE1: GPIO24")
        elif self.bus == 4:
            print("SPI4-MOSI: GPIO6(WS2812-PIN)  SPI4-MISO: GPIO5  SPI4-SCLK: GPIO7  SPI4-CE0: GPIO4  SPI4-CE1: GPIO25")
        elif self.bus == 5:
            print("SPI5-MOSI: GPIO14(WS2812-PIN)  SPI5-MISO: GPIO13  SPI5-SCLK: GPIO15  SPI5-CE0: GPIO12  SPI5-CE1: GPIO26")
        elif self.bus == 6:
            print("SPI6-MOSI: GPIO20(WS2812-PIN)  SPI6-MISO: GPIO19  SPI6-SCLK: GPIO21  SPI6-CE0: GPIO18  SPI6-CE1: GPIO27")
    
    # Méthode pour fermer la communication SPI et éteindre toutes les LED en réglant leur couleur sur noir (0, 0, 0). Elle utilise la méthode set_all_led_rgb pour éteindre les LED avant de fermer la connexion SPI.
    def led_close(self):
        self.set_all_led_rgb([0,0,0])
        self.spi.close()
    
    # Méthode pour définir le nombre de LED dans la bande LED WS2812. Elle initialise les listes led_color et led_original_color en fonction du nombre de LED spécifié, en les remplissant de valeurs initiales (0, 0, 0) pour chaque LED.
    def set_led_count(self, count):
        self.led_count = count
        self.led_color = [0,0,0] * self.led_count
        self.led_original_color = [0,0,0] * self.led_count

    # Méthode pour définir le type de LED en fonction de la séquence de couleurs spécifiée (par exemple, RGB, GRB, etc.). Elle utilise des listes pour déterminer les offsets de couleur rouge, verte et bleue en fonction de la séquence choisie. Si la séquence n'est pas valide, elle définit les offsets par défaut et retourne -1.
    def set_led_type(self, rgb_type):
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
    
    # Méthode pour régler la luminosité des LED. Elle prend une valeur de luminosité en entrée et ajuste les couleurs des LED en fonction de cette luminosité. Elle utilise la méthode set_led_rgb_data pour mettre à jour les couleurs des LED en fonction de la luminosité spécifiée.
    def set_led_brightness(self, brightness):
        self.led_brightness = brightness
        for i in range(self.led_count):
            self.set_led_rgb_data(i, self.led_original_color)

     # Méthode pour définir la couleur d'une LED spécifique en fonction de son index et des valeurs RGB fournies. Elle ajuste les couleurs en fonction de la luminosité définie et met à jour les listes led_color et led_original_color avec les nouvelles valeurs de couleur pour la LED spécifiée.       
    def set_ledpixel(self, index, r, g, b):
        p = [0,0,0]
        p[self.led_red_offset] = round(r * self.led_brightness / 255)
        p[self.led_green_offset] = round(g * self.led_brightness / 255)
        p[self.led_blue_offset] = round(b * self.led_brightness / 255)
        self.led_original_color[index*3+self.led_red_offset] = r
        self.led_original_color[index*3+self.led_green_offset] = g
        self.led_original_color[index*3+self.led_blue_offset] = b
        for i in range(3):
            self.led_color[index*3+i] = p[i]

    # Méthode pour définir la couleur d'une LED spécifique en fonction de son index et des valeurs RGB fournies, sans mettre à jour l'affichage immédiatement. Elle utilise la méthode set_ledpixel pour mettre à jour les couleurs des LED, mais n'appelle pas la méthode show pour afficher les changements.
    def set_led_color_data(self, index, r, g, b):
        self.set_ledpixel(index, r, g, b)  

    # Méthode pour définir la couleur d'une LED spécifique en fonction de son index et d'une liste de valeurs RGB, sans mettre à jour l'affichage immédiatement. Elle utilise la méthode set_ledpixel pour mettre à jour les couleurs des LED, mais n'appelle pas la méthode show pour afficher les changements.    
    def set_led_rgb_data(self, index, color):
        self.set_ledpixel(index, color[0], color[1], color[2])   

    # Méthode pour définir la couleur d'une LED spécifique en fonction de son index et des valeurs RGB fournies, puis mettre à jour l'affichage immédiatement. Elle utilise la méthode set_ledpixel pour mettre à jour les couleurs des LED, puis appelle la méthode show pour afficher les changements.    
    def set_led_color(self, index, r, g, b):
        self.set_ledpixel(index, r, g, b)
        self.show() 

    # Méthode pour définir la couleur d'une LED spécifique en fonction de son index et d'une liste de valeurs RGB, puis mettre à jour l'affichage immédiatement. Elle utilise la méthode set_ledpixel pour mettre à jour les couleurs des LED, puis appelle la méthode show pour afficher les changements.    
    def set_led_rgb(self, index, color):
        self.set_led_rgb_data(index, color)   
        self.show() 
    
    # Méthode pour définir la même couleur pour toutes les LED en fonction des valeurs RGB fournies, sans mettre à jour l'affichage immédiatement. Elle utilise la méthode set_led_color_data pour mettre à jour les couleurs de toutes les LED, mais n'appelle pas la méthode show pour afficher les changements.
    def set_all_led_color_data(self, r, g, b):
        for i in range(self.led_count):
            self.set_led_color_data(i, r, g, b)

    # Méthode pour définir la même couleur pour toutes les LED en fonction d'une liste de valeurs RGB, sans mettre à jour l'affichage immédiatement. Elle utilise la méthode set_led_rgb_data pour mettre à jour les couleurs de toutes les LED, mais n'appelle pas la méthode show pour afficher les changements.        
    def set_all_led_rgb_data(self, color):
        for i in range(self.led_count):
            self.set_led_rgb_data(i, color)  

    # Méthode pour définir la même couleur pour toutes les LED en fonction des valeurs RGB fournies, puis mettre à jour l'affichage immédiatement. Elle utilise la méthode set_led_color_data pour mettre à jour les couleurs de toutes les LED, puis appelle la méthode show pour afficher les changements.    
    def set_all_led_color(self, r, g, b):
        for i in range(self.led_count):
            self.set_led_color_data(i, r, g, b)
        self.show()

    # Méthode pour définir la même couleur pour toutes les LED en fonction d'une liste de valeurs RGB, puis mettre à jour l'affichage immédiatement. Elle utilise la méthode set_led_rgb_data pour mettre à jour les couleurs de toutes les LED, puis appelle la méthode show pour afficher les changements.    
    def set_all_led_rgb(self, color):
        for i in range(self.led_count):
            self.set_led_rgb_data(i, color) 
        self.show()

    # Méthode pour convertir les données de couleur des LED en un format compatible avec le protocole de communication SPI utilisé par les LED WS2812. Elle utilise la bibliothèque numpy pour manipuler les données de couleur et préparer les données à envoyer via SPI en fonction des timings spécifiques requis par les LED WS2812.
    def write_ws2812_numpy8(self):
        d = numpy.array(self.led_color).ravel()        #Converts data into a one-dimensional array
        tx = numpy.zeros(len(d)*8, dtype=numpy.uint8)  #Each RGB color has 8 bits, each represented by a uint8 type data
        for ibit in range(8):                          #Convert each bit of data to the data that the spi will send
            tx[7-ibit::8]=((d>>ibit)&1)*0x78 + 0x80    #T0H=1,T0L=7, T1H=5,T1L=3   #0b11111000 mean T1(0.78125us), 0b10000000 mean T0(0.15625us)  
        if self.led_init_state != 0:
            if self.bus == 0:
                self.spi.xfer(tx.tolist(), int(8/1.25e-6))         #Send color data at a frequency of 6.4Mhz
            else:
                self.spi.xfer(tx.tolist(), int(8/1.0e-6))          #Send color data at a frequency of 8Mhz

    # Méthode pour convertir les données de couleur des LED en un format compatible avec le protocole de communication SPI utilisé par les LED WS2812, en utilisant une approche différente pour représenter les bits de données. Elle utilise la bibliothèque numpy pour manipuler les données de couleur et préparer les données à envoyer via SPI en fonction des timings spécifiques requis par les LED WS2812, en utilisant une représentation différente pour les bits de données (T0H=0x06, T0L=0x60, T1H=0x60, T1L=0x06).    
    def write_ws2812_numpy4(self):
        d=numpy.array(self.led_color).ravel()
        tx=numpy.zeros(len(d)*4, dtype=numpy.uint8)
        for ibit in range(4):
            tx[3-ibit::4]=((d>>(2*ibit+1))&1)*0x60 + ((d>>(2*ibit+0))&1)*0x06 + 0x88  
        if self.led_init_state != 0:
            if self.bus == 0:
                self.spi.xfer(tx.tolist(), int(4/1.25e-6))         
            else:
                self.spi.xfer(tx.tolist(), int(4/1.0e-6))       

    # Méthode pour afficher les couleurs des LED en utilisant la méthode de conversion de données appropriée en fonction du mode spécifié. Elle appelle soit la méthode write_ws2812_numpy8, soit la méthode write_ws2812_numpy4 pour envoyer les données de couleur via SPI en fonction du mode sélectionné.    
    def show(self, mode = 1):
        if mode == 1:
            write_ws2812 = self.write_ws2812_numpy8
        else:
            write_ws2812 = self.write_ws2812_numpy4
        write_ws2812()

    # Méthode pour mettre en pause l'exécution du thread en utilisant un événement de synchronisation. Elle utilise la méthode clear de l'événement pour bloquer le thread jusqu'à ce qu'il soit repris.    
    def wheel(self, pos):
        if pos < 85:
            return [(255 - pos * 3), (pos * 3), 0]
        elif pos < 170:
            pos = pos - 85
            return [0, (255 - pos * 3), (pos * 3)]
        else:
            pos = pos - 170
            return [(pos * 3), 0, (255 - pos * 3)]
    
    # Méthode pour convertir les valeurs de couleur en format HSV (Hue, Saturation, Value) en format RGB (Red, Green, Blue). Elle prend en entrée les valeurs de teinte (h), de saturation (s) et de valeur (v), et retourne une liste contenant les valeurs RGB correspondantes. La conversion est effectuée en fonction des différentes plages de teinte et des calculs nécessaires pour déterminer les composantes RGB en fonction de la saturation et de la valeur.
    def hsv2rgb(self, h, s, v):
        h = h % 360
        rgb_max = round(v * 2.55)
        rgb_min = round(rgb_max * (100 - s) / 100)
        i = round(h / 60)
        diff = round(h % 60)
        rgb_adj = round((rgb_max - rgb_min) * diff / 60)
        if i == 0:
            r = rgb_max
            g = rgb_min + rgb_adj
            b = rgb_min
        elif i == 1:
            r = rgb_max - rgb_adj
            g = rgb_max
            b = rgb_min
        elif i == 2:
            r = rgb_min
            g = rgb_max
            b = rgb_min + rgb_adj
        elif i == 3:
            r = rgb_min
            g = rgb_max - rgb_adj
            b = rgb_max
        elif i == 4:
            r = rgb_min + rgb_adj
            g = rgb_min
            b = rgb_max
        else:
            r = rgb_max
            g = rgb_min
            b = rgb_max - rgb_adj
        return [r, g, b]
    
    # Méthode pour mettre en pause l'exécution du thread en utilisant un événement de synchronisation. Elle utilise la méthode clear de l'événement pour bloquer le thread jusqu'à ce qu'il soit repris.
    def police(self):
        self.lightMode = 'police'
        self.resume()
    # Méthode pour mettre en pause l'exécution du thread en utilisant un événement de synchronisation. Elle utilise la méthode clear de l'événement pour bloquer le thread jusqu'à ce qu'il soit repris.    
    def breath(self, R_input, G_input, B_input):
        self.lightMode = 'breath'
        self.colorBreathR = R_input
        self.colorBreathG = G_input
        self.colorBreathB = B_input
        self.resume()    

    # Méthode pour mettre en pause l'exécution du thread en utilisant un événement de synchronisation. Elle utilise la méthode clear de l'événement pour bloquer le thread jusqu'à ce qu'il soit repris.        
    def resume(self):
        self.__flag.set()

    # Méthode pour mettre en pause l'exécution du thread en utilisant un événement de synchronisation. Elle utilise la méthode clear de l'événement pour bloquer le thread jusqu'à ce qu'il soit repris.    
    def breathProcessing(self):
        while self.lightMode == 'breath':
            for i in range(0,self.breathSteps):
                if self.lightMode != 'breath':
                    break
                self.set_all_led_color(self.colorBreathR*i/self.breathSteps, self.colorBreathG*i/self.breathSteps, self.colorBreathB*i/self.breathSteps)
                #self.show()
                time.sleep(0.03)
            for i in range(0,self.breathSteps):
                if self.lightMode != 'breath':
                    break
                self.set_all_led_color(self.colorBreathR-(self.colorBreathR*i/self.breathSteps), self.colorBreathG-(self.colorBreathG*i/self.breathSteps), self.colorBreathB-(self.colorBreathB*i/self.breathSteps))
                #self.show()
                time.sleep(0.03)

    # Méthode pour mettre en pause l'exécution du thread en utilisant un événement de synchronisation. Elle utilise la méthode clear de l'événement pour bloquer le thread jusqu'à ce qu'il soit repris.
    def policeProcessing(self):
        while self.lightMode == 'police':
            for i in range(0,3):
                self.set_all_led_color_data(0,0,255)
                self.show()
                time.sleep(0.05)
                self.set_all_led_color_data(0,0,0)
                self.show()
                time.sleep(0.05)
            if self.lightMode != 'police':
                break
            time.sleep(0.1)
            for i in range(0,3):
                self.set_all_led_color_data(255,0,0)
                self.show()
                time.sleep(0.05)
                self.set_all_led_color_data(0,0,0)
                self.show()
                time.sleep(0.05)
            time.sleep(0.1)
            
    # Méthode pour gérer les changements de mode d'éclairage en fonction de la valeur de lightMode. Elle appelle les méthodes correspondantes pour le mode "police" et le mode "breath", ou met en pause l'exécution si le mode est "none".        
    def lightChange(self):
        if self.lightMode == 'none':
            self.pause()
        elif self.lightMode == 'police':
            self.policeProcessing()
        elif self.lightMode == 'breath':
            self.breathProcessing()    

    # Méthode pour mettre en pause l'exécution du thread en utilisant un événement de synchronisation. Elle utilise la méthode clear de l'événement pour bloquer le thread jusqu'à ce qu'il soit repris.
    def run(self):
        while 1:
            self.__flag.wait()
            self.lightChange()
            pass
        
       
    """
    Méthode pour définir la couleur d'une LED spécifique en fonction de son index, de la couleur choisie et de la luminosité. Elle vérifie si le numéro de LED est valide (entre 1 et 14) et si la couleur choisie est présente dans le dictionnaire de couleurs. Si les conditions sont remplies, elle ajuste les valeurs RGB en fonction de la luminosité spécifiée et utilise la méthode set_led_rgb pour mettre à jour la couleur de la LED correspondante. Si les conditions ne sont pas remplies, un message d'erreur est affiché pour informer l'utilisateur des entrées invalides.
    arguments:

    - choosenLed: Le numéro de la LED à allumer (entre 1 et 14).
    - choosenColor: La couleur à afficher sur la LED, représentée par une lettre (R, G, B, N).
    - brightness: La luminosité de la LED (entre 0 et 255).

    """
    def set_one_led(self, choosenLed, choosenColor, brightness=255):
        if 1 <= choosenLed <= 14 and choosenColor in self.colors:
            scaled_colors = [round(c * brightness / 255) for c in self.colors.get(choosenColor)]
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
