import time
import sys
import board
import busio
import adafruit_pca9685

print("=====================================================")
# ── 1. Instance UNIQUE I2C + PCA9685 partagée ────────────────────────────────
try:
    shared_i2c = busio.I2C(board.SCL, board.SDA)
    shared_pca = adafruit_pca9685.PCA9685(shared_i2c, address=0x5f)
    shared_pca.frequency = 50
except Exception as e:
    print(f"[ERREUR CRITIQUE] Impossible d'ouvrir le bus I2C : {e}")
    sys.exit(1)

# ── 2. Monkey-patch pour éviter les doubles ouvertures I2C/PCA9685 ────────────
class MockI2C:
    def __new__(cls, *args, **kwargs):
        return shared_i2c

class MockPCA9685:
    def __new__(cls, *args, **kwargs):
        return shared_pca
    def __init__(self, *args, **kwargs):
        pass

busio.I2C                 = MockI2C
adafruit_pca9685.PCA9685  = MockPCA9685

# ── 3. Imports des modules (le patch est actif, plus de conflit I2C) ──────────
import Tache1
import Tache2
import Tache4
import Tache5
import Tache8

# ── 4. Utilitaire ─────────────────────────────────────────────────────────────
def safe_call(obj, name, *args, **kwargs):
    """Appelle obj.name(*args, **kwargs) si la méthode existe."""
    if obj is None:
        return None
    fn = getattr(obj, name, None)
    if callable(fn):
        return fn(*args, **kwargs)
    return None

# ── 5. Instances globales des sous-systèmes ───────────────────────────────────
# CORRECTION : on instancie les CLASSES, on n'appelle pas les méthodes sur le module.
led_ctrl    = None   # Adeept_LED_Control
ruban_ws2812 = None  # Adeept_SPI_LedPixel
motor_ctrl  = None   # AdeeptMotorController  (CORRECTION : était appelé en tant que module)
ultra_ctrl  = None   # AdeeptUltra            (CORRECTION : idem)
adc_lumiere = None   # ADS7830


def initialiser_robot():
    global led_ctrl, ruban_ws2812, motor_ctrl, ultra_ctrl, adc_lumiere
    print("\n[SYS] Initialisation globale des composants...")

    # ── Phares classiques (Tâche 1) ───────────────────────────────────────────
    # CORRECTION : instanciation de la classe, pas appel sur le module
    try:
        led_ctrl = Tache1.Adeept_LED_Control()
        led_ctrl.setup()
        led_ctrl.all_off()
    except Exception as e:
        print(f"[ATTENTION] LEDs RGB : {e}")
        led_ctrl = None

    # ── Ruban WS2812 (Tâche 2) ────────────────────────────────────────────────
    try:
        ruban_ws2812 = Tache2.Adeept_SPI_LedPixel(count=14, bright=255)
        ruban_ws2812.set_all_led_color(0, 0, 0)
    except Exception as e:
        print(f"[ATTENTION] Ruban WS2812 : {e}")
        ruban_ws2812 = None

    # ── Moteur DC + servo direction (Tâche 4) ────────────────────────────────
    # CORRECTION : AdeeptMotorController est une classe instance, pas un module
    try:
        motor_ctrl = Tache4.AdeeptMotorController(pca=shared_pca)
        motor_ctrl.motorStop()
        motor_ctrl.setDirection(motor_ctrl.SERVO_CENTER)
    except Exception as e:
        print(f"[ATTENTION] Moteur/direction : {e}")
        motor_ctrl = None

    # ── Capteur ultrason (Tâche 5) ────────────────────────────────────────────
    # CORRECTION : AdeeptUltra est une classe instance, pas un module
    try:
        ultra_ctrl = Tache5.AdeeptUltra()
    except Exception as e:
        print(f"[ATTENTION] Ultrason : {e}")
        ultra_ctrl = None

    # ── Capteur de lumière ADS7830 (Tâche 8) ──────────────────────────────────
    # CORRECTION : ADS7830 n'a plus besoin de ServoController interne
    try:
        adc_lumiere = Tache8.ADS7830()
    except Exception as e:
        print(f"[ATTENTION] ADS7830 : {e}")
        adc_lumiere = None

    print("[SYS] Configuration terminée. Lancement dans 2 secondes...\n")
    time.sleep(2.0)


def integration_principale():
    """Boucle principale : suivi de lumière + sécurité anti-collision."""
    global led_ctrl, ruban_ws2812, motor_ctrl, ultra_ctrl, adc_lumiere

    try:
        while True:
            # ── Lecture ultrason ──────────────────────────────────────────────
            # CORRECTION : checkdist() est une méthode d'instance (ultra_ctrl), pas du module
            distance_cm = 0.0
            if ultra_ctrl is not None:
                try:
                    distance_cm = float(ultra_ctrl.checkdist())
                except Exception:
                    distance_cm = 0.0

            # ── Lecture des LDR ───────────────────────────────────────────────
            # CORRECTION : read_both et get_light_direction sont des fonctions
            #              du module Tache8, pas des méthodes de ADS7830
            ldr1, ldr2 = 0, 0
            if adc_lumiere is not None:
                try:
                    ldr1, ldr2 = Tache8.read_both(adc_lumiere)
                except Exception:
                    ldr1, ldr2 = 0, 0

            direction_lumiere = Tache8.get_light_direction(ldr1, ldr2)

            # Affichage de débogage
            print(
                f"Dist: {distance_cm:5.1f} cm | "
                f"LDR1={int(ldr1):3d} LDR2={int(ldr2):3d} -> {direction_lumiere}"
            )

            # ── Automate de décision ──────────────────────────────────────────

            if 0 < distance_cm < 20.0:
                # --- OBSTACLE ---
                safe_call(motor_ctrl, "motorStop")
                safe_call(motor_ctrl, "setDirection",
                          getattr(motor_ctrl, "SERVO_CENTER", 140))
                safe_call(led_ctrl,   "setAllRGBColor", 255, 0, 0)
                if ruban_ws2812:
                    ruban_ws2812.set_all_led_color(255, 0, 0)

            else:
                # --- SUIVI DE LUMIÈRE ---
                safe_call(led_ctrl, "setAllRGBColor", 0, 255, 0)
                if ruban_ws2812:
                    ruban_ws2812.set_all_led_color(0, 255, 0)

                servo_center = getattr(motor_ctrl, "SERVO_CENTER", 140) if motor_ctrl else 140
                servo_left   = getattr(motor_ctrl, "SERVO_LEFT",   110) if motor_ctrl else 110
                servo_right  = getattr(motor_ctrl, "SERVO_RIGHT",  170) if motor_ctrl else 170

                if direction_lumiere == "GAUCHE":
                    # Inversion physique gauche/droite
                    safe_call(motor_ctrl, "setDirection", servo_right)
                    safe_call(motor_ctrl, "Motor",
                              getattr(motor_ctrl, "DIR_FORWARD", 1), 25)

                elif direction_lumiere == "DROITE":
                    safe_call(motor_ctrl, "setDirection", servo_left)
                    safe_call(motor_ctrl, "Motor",
                              getattr(motor_ctrl, "DIR_FORWARD", 1), 25)

                elif direction_lumiere == "CENTRE":
                    safe_call(motor_ctrl, "setDirection", servo_center)
                    safe_call(motor_ctrl, "Motor",
                              getattr(motor_ctrl, "DIR_FORWARD", 1), 30)

                elif direction_lumiere == "OBSCUR":
                    safe_call(motor_ctrl, "motorStop")
                    safe_call(led_ctrl,   "setAllRGBColor", 0, 0, 255)
                    if ruban_ws2812:
                        ruban_ws2812.set_all_led_color(0, 0, 255)

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[SYS] Arrêt sécurisé du PiCar-B...")
        # CORRECTION : destroy() est une méthode d'instance de motor_ctrl
        safe_call(motor_ctrl,  "destroy")
        safe_call(led_ctrl,    "destroy")
        if ruban_ws2812:
            ruban_ws2812.led_close()
        print("[SYS] Tout est libéré. Mission accomplie !")


if __name__ == "__main__":
    initialiser_robot()
    integration_principale()
