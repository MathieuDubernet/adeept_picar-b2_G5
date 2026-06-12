from gpiozero import PWMOutputDevice as PWM
from gpiozero import LED

class Adeept_LED_Control:

    def __init__(self):
        """
        Initialise les numéros de broches GPIO du contrôleur de LEDs :
        les 6 canaux RGB PWM (gauche/droite × R/G/B) et les 3 LEDs simples.
        Les objets matériels ne sont pas encore créés ici (voir setup()).
        """
        self.Left_R  = 19
        self.Left_G  = 0
        self.Left_B  = 13
        self.Right_R = 1
        self.Right_G = 5
        self.Right_B = 6
        self.LED1_PIN = 9
        self.LED2_PIN = 25
        self.LED3_PIN = 11

    colors = [0xFF0000, 0x00FF00, 0x0000FF, 0xFFFF00,
            0xFF00FF, 0x00FFFF, 0x6F00D2, 0xFF5809]

    def setup(self):
        """
        Construit les objets matériels à partir des broches définies dans
        __init__ : les 6 sorties RGB PWM (initial_value=1.0 = éteint, car
        la logique est inversée) à 2000 Hz, puis les 3 LEDs simples ON/OFF.
        À appeler une fois avant toute commande de LED.
        """
        self.L_R = PWM(pin=self.Left_R,  initial_value=1.0, frequency=2000)
        self.L_G = PWM(pin=self.Left_G,  initial_value=1.0, frequency=2000)
        self.L_B = PWM(pin=self.Left_B,  initial_value=1.0, frequency=2000)
        self.R_R = PWM(pin=self.Right_R, initial_value=1.0, frequency=2000)
        self.R_G = PWM(pin=self.Right_G, initial_value=1.0, frequency=2000)
        self.R_B = PWM(pin=self.Right_B, initial_value=1.0, frequency=2000)

        # LEDs simples ON/OFF
        self.led1 = LED(self.LED1_PIN)
        self.led2 = LED(self.LED2_PIN)
        self.led3 = LED(self.LED3_PIN)


    def map_val(self, x, in_min, in_max, out_min, out_max):
        """
        Convertit une valeur d'un intervalle source vers un intervalle cible
        (interpolation linéaire), par ex. de [0-255] vers [0.0-1.0].

        Paramètres:
        - x: valeur à convertir
        - in_min, in_max: bornes de l'intervalle source
        - out_min, out_max: bornes de l'intervalle cible
        """
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min



    def setAllRGBColor(self, R, G, B):
        """
        Applique une même couleur aux 6 LEDs RGB. Les composantes (0-255)
        sont converties en valeurs PWM (0.0-1.0) puis inversées (1.0 - valeur)
        car les LEDs sont câblées en logique inversée (0.0 = pleine intensité).

        Paramètres:
        - R: composante rouge (0-255)
        - G: composante verte (0-255)
        - B: composante bleue (0-255)
        """
        R_val = self.map_val(R, 0, 255, 0, 1.0)
        G_val = self.map_val(G, 0, 255, 0, 1.0)
        B_val = self.map_val(B, 0, 255, 0, 1.0)

        self.L_R.value = 1.0 - R_val
        self.L_G.value = 1.0 - G_val
        self.L_B.value = 1.0 - B_val
        self.R_R.value = 1.0 - R_val
        self.R_G.value = 1.0 - G_val
        self.R_B.value = 1.0 - B_val


    def set_led(self, num, state):
        """
        Pilote individuellement chaque LED.
        num   : 1 à 9
        state : True/1 = allumer, False/0 = éteindre

        Mapping :
        1 → LED1 (simple)
        2 → LED2 (simple)
        3 → LED3 (simple)
        4 → Left_R  (RGB PWM, logique inversée)
        5 → Left_G
        6 → Left_B
        7 → Right_R
        8 → Right_G
        9 → Right_B
        """
        # LEDs simples (logique directe)
        if num == 1:
            self.led1.on()  if state else self.led1.off()
        elif num == 2:
            self.led2.on()  if state else self.led2.off()
        elif num == 3:
            self.led3.on()  if state else self.led3.off()

        # LEDs RGB PWM (logique INVERSÉE : 0.0 = allumé, 1.0 = éteint)
        elif num == 4:
            self.L_R.value = 0.0 if state else 1.0
        elif num == 5:
            self.L_G.value = 0.0 if state else 1.0
        elif num == 6:
            self.L_B.value = 0.0 if state else 1.0
        elif num == 7:
            self.R_R.value = 0.0 if state else 1.0
        elif num == 8:
            self.R_G.value = 0.0 if state else 1.0
        elif num == 9:
            self.R_B.value = 0.0 if state else 1.0
        else:
            print(f"Numéro de LED invalide : {num} (attendu : 1 à 9)")


    def all_off(self):
        """Éteint toutes les LEDs."""
        for i in range(1, 10):
            self.set_led(i, False)

    def destroy(self):
        """
        Arrêt propre : éteint toutes les LEDs puis libère (close) les 6 canaux
        RGB PWM et les 3 LEDs simples afin de relâcher les broches GPIO.
        """
        self.all_off()
        self.L_R.close(); self.L_G.close(); self.L_B.close()
        self.R_R.close(); self.R_G.close(); self.R_B.close()
        self.led1.close(); self.led2.close(); self.led3.close()
        print("GPIO libérés.")


def main(adeept_led_control):

    print("Contrôle manuel des LEDs :")
    print(" 11-19 => Allumer LED 1 à 9")
    print(" 21-29 => Éteindre LED 1 à 9")
    print(" 00    => Tout éteindre")
    print(" 99    => Quitter")

    while True:
        try:
            cmd = input("\nCommande : ").strip()

            if cmd == "99":
                print("Arrêt du programme.")
                break

            if cmd == "00":
                adeept_led_control.all_off()
                print("Toutes les LEDs éteintes.")
                continue

            code = int(cmd)
            action = code // 10   # 1 = allumer, 2 = éteindre
            num    = code % 10    # numéro de LED (1-9)

            if num < 1 or num > 9:
                print("Numéro LED invalide (1-9).")
                continue

            if action == 1:
                adeept_led_control.set_led(num, True)
                print(f"LED{num} allumée.")
            elif action == 2:
                adeept_led_control.set_led(num, False)
                print(f"LED{num} éteinte.")
            else:
                print("Commande invalide. Exemples : 11, 19, 21, 29")

        except ValueError:
            print("Entrée invalide, tapez un nombre (ex: 11, 23).")
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    controlLed = Adeept_LED_Control()
    controlLed.setup()
    try:
        main(controlLed)
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        controlLed.destroy()