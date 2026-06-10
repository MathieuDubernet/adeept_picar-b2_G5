#!/usr/bin/env python3
import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

# Adresse PCA
PCA_ADDR = 0x5f

# Canaux utilisés
SERVO_TEST = 4
SERVOS_ROBOT = [0, 1, 2]
ALL_SERVOS = [0, 1, 2, 4]

# Réglages de sécurité
ANGLE_MIN = 10
ANGLE_MAX = 170
FREQ = 50

# Initialisation
i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=PCA_ADDR)
pca.frequency = FREQ

# Création des objets servo
servos = {
    0: servo.Servo(pca.channels[0], min_pulse=500, max_pulse=2400, actuation_range=180),
    1: servo.Servo(pca.channels[1], min_pulse=500, max_pulse=2400, actuation_range=180),
    2: servo.Servo(pca.channels[2], min_pulse=500, max_pulse=2400, actuation_range=180),
    4: servo.Servo(pca.channels[4], min_pulse=500, max_pulse=2400, actuation_range=180),
}

def clamp_angle(angle):
    angle = int(angle)
    if angle < ANGLE_MIN:
        return ANGLE_MIN
    if angle > ANGLE_MAX:
        return ANGLE_MAX
    return angle

def set_servo(num_servo, angle):
    """
    Commande un servo par son numéro de canal et son angle.
    Exemple: set_servo(4, 90)
    """
    if num_servo not in servos:
        raise ValueError(f"Servo invalide: {num_servo}. Choix possibles: {ALL_SERVOS}")

    safe_angle = clamp_angle(angle)
    servos[num_servo].angle = safe_angle
    time.sleep(0.05)

def centre_all():
    for ch in ALL_SERVOS:
        set_servo(ch, 90)

def test_servo(channel):
    print(f"Test du servo sur CH{channel}")
    for angle in [60, 90, 120, 90]:
        set_servo(channel, angle)
        print(f"CH{channel} -> {angle}°")
        time.sleep(1)

def manual_mode():
    print("\nMode manuel")
    print("Servos disponibles : 0, 1, 2, 4")
    print(f"Angles autorisés : {ANGLE_MIN} à {ANGLE_MAX}")
    print("Commande : numero angle   (ex: 4 90)")
    print("Commandes spéciales : center, test, quit\n")

    while True:
        cmd = input(">>> ").strip().lower()

        if cmd in ("quit", "exit", "q"):
            break

        if cmd == "center":
            centre_all()
            print("Tous les servos ont été centrés à 90°")
            continue

        if cmd == "test":
            test_servo(SERVO_TEST)
            continue

        parts = cmd.split()
        if len(parts) != 2:
            print("Format invalide. Exemple : 1 120")
            continue

        try:
            num_servo = int(parts[0])
            angle = int(parts[1])
            set_servo(num_servo, angle)
            print(f"CH{num_servo} -> {clamp_angle(angle)}°")
        except ValueError as e:
            print(f"Erreur : {e}")
        except Exception as e:
            print(f"Erreur inattendue : {e}")

def cleanup():
    for ch in ALL_SERVOS:
        try:
            servos[ch].angle = None
        except Exception:
            pass
    pca.deinit()

if __name__ == "__main__":
    try:
        print("Initialisation OK")
        print("Étape 1 : test sécurité sur le servo libre CH4")
        test_servo(SERVO_TEST)

        print("\nÉtape 2 : centrage des servos")
        centre_all()

        print("\nÉtape 3 : commande manuelle")
        manual_mode()

    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur")
    finally:
        cleanup()
        print("PCA9685 libéré proprement")