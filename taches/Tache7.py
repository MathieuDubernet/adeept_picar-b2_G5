import time
import sys
import board
import busio
import adafruit_pca9685

print("=====================================================")
# 1. PROTECTION MATÉRIELLE : Création d'une instance UNIQUE I2C et PCA9685
# =====================================================================
try:
    shared_i2c = busio.I2C(board.SCL, board.SDA)
    shared_pca = adafruit_pca9685.PCA9685(shared_i2c, address=0x5f)
    shared_pca.frequency = 50
except Exception as e:
    print(f"[ERREUR CRITIQUE] Impossible d'ouvrir le bus I2C : {e}")
    sys.exit(1)

# 2. ASTUCE MAGIQUE : On intercepte les futurs appels pour éviter le plantage "I2C already in use"
class MockI2C:
    def __new__(cls, *args, **kwargs):
        return shared_i2c

class MockPCA9685:
    def __new__(cls, *args, **kwargs):
        return shared_pca
    def __init__(self, *args, **kwargs):
        pass

# On remplace temporairement les fonctions d'origine par nos versions partagées
busio.I2C = MockI2C
adafruit_pca9685.PCA9685 = MockPCA9685

# 3. IMPORTS SÉCURISÉS DES MODULES (Maintenant ils ne planteront plus)
# =====================================================================
import Tache1
import Tache2
import Tache3
import Tache4
import Tache5
import Tache8

# Variables globales pour les objets de contrôle
adc_lumiere = None
ruban_ws2812 = None

def safe_call(obj, name, *args, **kwargs):
    """Appelle obj.name(*args, **kwargs) si disponible (sécurité)."""
    if obj is None:
        return None
    fn = getattr(obj, name, None)
    if callable(fn):
        return fn(*args, **kwargs)
    return None

def initialiser_robot():
    """Initialise proprement les composants sans surcharge matérielle."""
    global adc_lumiere, ruban_ws2812
    print("\n[SYS] Initialisation globale des composants...")

    # Configuration des phares classiques (Tâche 1)
    led_ctrl = getattr(Tache1, "Adeept_LED_Control", None)
    if led_ctrl:
        safe_call(led_ctrl, "setup")
        safe_call(led_ctrl, "all_off")

    # Configuration du ruban WS2812 (Tâche 2)
    try:
        spi_led_cls = getattr(Tache2, "Adeept_SPI_LedPixel", None)
        if spi_led_cls:
            ruban_ws2812 = spi_led_cls(count=14, bright=255)
            safe_call(ruban_ws2812, "set_all_led_color", 0, 0, 0)
    except Exception as e:
        print(f"[ATTENTION] Problème d'initialisation du ruban WS2812 : {e}")

    # Sécurisation des moteurs et alignement des roues (Tâche 4)
    safe_call(Tache4, "motorStop")
    # Essayer d'utiliser une constante SERVO_CENTER soit dans le module soit dans une classe exportée
    servo_center = getattr(Tache4, "SERVO_CENTER", None)
    if servo_center is not None:
        safe_call(Tache4, "setDirection", servo_center)

    # Configuration du capteur de lumière ADS7830 (Tâche 8)
    adc_class = getattr(Tache8, "ADS7830", None)
    if adc_class:
        try:
            adc_lumiere = adc_class()
        except Exception as e:
            print(f"[ATTENTION] Impossible d'instancier ADS7830 : {e}")
            adc_lumiere = None

    print("[SYS] Configuration terminée avec succès ! Lancement dans 2 secondes...\n")
    time.sleep(2.0)

def integration_principale():
    """Boucle principale : suivi de lumière intelligent et sécurité anti-collision."""
    global adc_lumiere, ruban_ws2812
    try:
        while True:
            # ---------------------------------------------------------
            # LECTURE DES CAPTEURS (Ultrason & Lumière)
            # ---------------------------------------------------------
            temp = safe_call(Tache5, "checkdist")
            # S'assurer que distance_cm est un nombre (float) pour éviter les erreurs de comparaison
            if isinstance(temp, (int, float, str)):
                try:
                    distance_cm = float(temp)
                except Exception:
                    distance_cm = 0.0
            else:
                distance_cm = 0.0

            ldr1, ldr2 = (0, 0)
            read_both = getattr(Tache8, "read_both", None)
            if read_both:
                try:
                    ldr1, ldr2 = read_both(adc_lumiere)
                except Exception:
                    ldr1, ldr2 = (0, 0)
            direction_lumiere = safe_call(Tache8, "get_light_direction", ldr1, ldr2) or "CENTRE"

            # Affichage de débogage en direct
            try:
                print(f"Dist: {distance_cm:5.1f} cm | LDR1={int(ldr1):3d} LDR2={int(ldr2):3d} -> Action: {direction_lumiere}")
            except Exception:
                print(f"Dist: {distance_cm} cm | LDR1={ldr1} LDR2={ldr2} -> Action: {direction_lumiere}")

            # ---------------------------------------------------------
            # AUTOMATE DE DÉCISION (LOGIQUE DU ROBOT)
            # ---------------------------------------------------------

            # --- CAS DE SÉCURITÉ : OBSTACLE PROCHE DÉTECTÉ ---
            if 0 < distance_cm < 20.0:
                safe_call(Tache4, "motorStop")                       # Arrêt immédiat des moteurs
                safe_call(Tache4, "setDirection", getattr(Tache4, "SERVO_CENTER", None)) # Roues droites

                # Alerte visuelle générale rouge
                safe_call(getattr(Tache1, "Adeept_LED_Control", None), "setAllRGBColor", 255, 0, 0)
                if ruban_ws2812:
                    safe_call(ruban_ws2812, "set_all_led_color", 255, 0, 0)

            # --- CAS NORMAL : COMPORTEMENT SUIVEUR DE LUMIÈRE ---
            else:
                # Tout va bien : Phares et ruban en VERT
                safe_call(getattr(Tache1, "Adeept_LED_Control", None), "setAllRGBColor", 0, 255, 0)
                if ruban_ws2812:
                    safe_call(ruban_ws2812, "set_all_led_color", 0, 255, 0)

                # Gestion de la direction (Inversion physique gauche/droite corrigée ici)
                if direction_lumiere == "GAUCHE":
                    safe_call(Tache4, "setDirection", getattr(Tache4, "SERVO_RIGHT", None))
                    safe_call(Tache4, "Motor", getattr(Tache4, "DIR_FORWARD", None), 25)

                elif direction_lumiere == "DROITE":
                    safe_call(Tache4, "setDirection", getattr(Tache4, "SERVO_LEFT", None))
                    safe_call(Tache4, "Motor", getattr(Tache4, "DIR_FORWARD", None), 25)

                elif direction_lumiere == "CENTRE":
                    safe_call(Tache4, "setDirection", getattr(Tache4, "SERVO_CENTER", None))
                    safe_call(Tache4, "Motor", getattr(Tache4, "DIR_FORWARD", None), 30)

                elif direction_lumiere == "OBSCUR":
                    safe_call(Tache4, "motorStop")
                    safe_call(getattr(Tache1, "Adeept_LED_Control", None), "setAllRGBColor", 0, 0, 255)
                    if ruban_ws2812:
                        safe_call(ruban_ws2812, "set_all_led_color", 0, 0, 255)

            # Pause impérative pour ne pas saturer le CPU du Raspberry Pi
            time.sleep(0.1)

    except KeyboardInterrupt:
        # ---------------------------------------------------------
        # ARRÊT PROPRE ET NETTOYAGE (Ctrl+C)
        # ---------------------------------------------------------
        print("\n[SYS] Interruption détectée. Arrêt sécurisé du PiCar-B...")
        safe_call(Tache4, "destroy")
        safe_call(getattr(Tache1, "Adeept_LED_Control", None), "destroy")
        if ruban_ws2812:
            safe_call(ruban_ws2812, "led_close")
        print("[SYS] Tout est libéré et éteint. Mission accomplie !")

if __name__ == "__main__":
    initialiser_robot()
    integration_principale()