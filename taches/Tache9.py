from gpiozero import DistanceSensor
from time import sleep, time
from adafruit_motor import motor
import busio
from adafruit_pca9685 import PCA9685
from board import SCL, SDA
from gpiozero import PWMOutputDevice as PWM
import threading
import sys

# Configuration Moteur
MOTOR_M1_IN1 = 9       # Pôle positif M1
MOTOR_M1_IN2 = 8       # Pôle négatif M1

DIR_FORWARD  =  1
DIR_BACKWARD = -1

# Configuration Phares (LEDs RGB)
Left_R  = 19
Left_G  = 0
Left_B  = 13
Right_R = 1
Right_G = 5
Right_B = 6

# Configuration Capteur Ultrason
Tr = 23
Ec = 24
sensor = DistanceSensor(echo=Ec, trigger=Tr, max_distance=2)

# Initialisation I2C et PCA9685
i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=0x5f)
pca.frequency = 50
motor1 = motor.DCMotor(pca.channels[MOTOR_M1_IN1], pca.channels[MOTOR_M1_IN2])
motor1.decay_mode = motor.SLOW_DECAY

# Variables globales pour le contrôle de l'état
current_speed = 0       # Vitesse actuelle (0 à 100)
robot_state = "STOP"    # États possibles : "STOP", "MOVE", "HAZARD"
command_input = ""      # Stocke le dernier caractère saisi
running = True          # Contrôle de la boucle principale

L_R = L_G = L_B = None
R_R = R_G = R_B = None

def checkdist():
    return (sensor.distance) * 100

def map_val(x, in_min, in_max, out_min, out_max):
    return (x - in_min) / (in_max - in_min) * (out_max - out_min) + out_min

def Motor(direction, speed_pct):
    global current_speed
    speed_pct = max(0, min(100, speed_pct))
    current_speed = speed_pct
    throttle = map_val(speed_pct, 0, 100, 0.0, 1.0)
    motor1.throttle = throttle * direction

def motorStop():
    global current_speed
    motor1.throttle = 0
    current_speed = 0
    print("[MOTEUR] Arrêt immédiat")

def set_lights(r, g, b, r2, g2, b2):
    L_R.value = r; L_G.value = g; L_B.value = b
    R_R.value = r2; R_G.value = g2; R_B.value = b2

def setup():
    global L_R, L_G, L_B, R_R, R_G, R_B
    L_R = PWM(pin=Left_R,  initial_value=0.0, frequency=2000)
    L_G = PWM(pin=Left_G,  initial_value=0.0, frequency=2000)
    L_B = PWM(pin=Left_B,  initial_value=0.0, frequency=2000)
    R_R = PWM(pin=Right_R, initial_value=0.0, frequency=2000)
    R_G = PWM(pin=Right_G, initial_value=0.0, frequency=2000)
    R_B = PWM(pin=Right_B, initial_value=0.0, frequency=2000)
    print("Initialisation terminée. Prêt.")

def destroy():
    global running
    running = False
    motorStop()
    if L_R:
        set_lights(0, 0, 0, 0, 0, 0)
        L_R.close(); L_G.close(); L_B.close()
        R_R.close(); R_G.close(); R_B.close()
    print("GPIO libérés.")

# --- Fonctions de mouvement avec pentes ---

def accelerate(target_speed=50, duration=1.5):
    """Augmente progressivement la vitesse jusqu'à target_speed"""
    global current_speed
    print(f"[MOTEUR] Accélération vers {target_speed}%...")
    steps = 10
    sleep_time = duration / steps
    increment = (target_speed - current_speed) / steps
    
    for _ in range(steps):
        if robot_state != "MOVE":  # Interruption si un arrêt est demandé pendant la pente
            break
        next_speed = current_speed + increment
        Motor(DIR_FORWARD, next_speed)
        sleep(sleep_time)

def decelerate(duration=1.0):
    """Diminue progressivement la vitesse jusqu'à l'arrêt"""
    global current_speed
    print("[MOTEUR] Décélération...")
    steps = 10
    sleep_time = duration / steps
    decrement = current_speed / steps
    
    for _ in range(steps):
        next_speed = max(0, current_speed - decrement)
        Motor(DIR_FORWARD, next_speed)
        sleep(sleep_time)
    motorStop()

# --- Lecture Clavier Non-Bloquante ---

def read_keyboard():
    global command_input, running
    while running:
        # Lecture simplifiée dans la console (Appuyer sur Entrée après la lettre)
        char = sys.stdin.readline().strip()
        if char:
            command_input = char

# --- Boucle Principale ---

if __name__ == "__main__":
    setup()
    
    # Lancement du thread d'écoute clavier
    input_thread = threading.Thread(target=read_keyboard)
    input_thread.daemon = True
    input_thread.start()
    
    last_light_toggle = time()
    light_state = False
    
    print("Instructions : 'M' pour démarrer, 'A' ou 'a' pour stopper.")
    
    try:
        while running:
            distance = checkdist()
            
            # 1. Gestion des commandes clavier reçues
            if command_input != "":
                cmd = command_input
                command_input = "" # Réinitialise l'ordre
                
                if cmd == 'M':
                    if robot_state == "STOP" or robot_state == "HAZARD":
                        print("\n[ORDRE] Départ demandé.")
                        set_lights(0, 0, 0, 0, 0, 0)
                        robot_state = "MOVE"
                        accelerate(target_speed=40, duration=2.0) # Vitesse réduite pour tests
                
                elif cmd in ['A', 'a']:
                    print("\n[ORDRE] Arrêt Manuel Immédiat.")
                    robot_state = "STOP"
                    motorStop()
                    set_lights(0, 0, 0, 0, 0, 0)

            # 2. Sécurité : Détection d'obstacle (< 20 cm)
            if robot_state == "MOVE" and distance < 20:
                print(f"\n[ATTENTION] Obstacle détecté à {distance:.1f} cm !")
                robot_state = "HAZARD"
                decelerate(duration=0.5) # Décélération rapide d'urgence
            
            # 3. Gestion des Feux de détresse (Mode HAZARD)
            if robot_state == "HAZARD":
                if time() - last_light_toggle > 0.25:
                    light_state = not light_state
                    last_light_toggle = time()
                    if light_state:
                        set_lights(1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
                    else:
                        set_lights(0, 0, 0, 0, 0, 0)

            sleep(0.05) # Petite pause pour soulager le processeur

    except KeyboardInterrupt:
        print("\nFin du programme par Ctrl+C.")
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        destroy()