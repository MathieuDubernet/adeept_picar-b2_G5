import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import motor, servo


MOTOR_M1_IN1 = 9       # Pôle positif M1
MOTOR_M1_IN2 = 8       # Pôle négatif M1

SERVO_DIR_CHANNEL = 0
SERVO_MIN_PULSE   = 500
SERVO_MAX_PULSE   = 2400

DIR_FORWARD  =  1
DIR_BACKWARD = -1

# Angle central du servo (à ajuster lors de l'étalonnage)
SERVO_CENTER  = 140      # Position centrale (à ajuster)
SERVO_LEFT    = SERVO_CENTER - 30  # Limite gauche (à ajuster)
SERVO_RIGHT   = SERVO_CENTER + 30  # Limite droite (à ajuster)


i2c       = busio.I2C(SCL, SDA)
pca       = PCA9685(i2c, address=0x5f)
pca.frequency = 50

motor1 = motor.DCMotor(pca.channels[MOTOR_M1_IN1],
                       pca.channels[MOTOR_M1_IN2])
motor1.decay_mode = motor.SLOW_DECAY


def map_val(x, in_min, in_max, out_min, out_max):
    return (x - in_min) / (in_max - in_min) * (out_max - out_min) + out_min


def motorStop():
    motor1.throttle = 0
    print("[MOTEUR] Arrêt")


def Motor(direction, speed_pct):
    speed_pct = max(0, min(100, speed_pct))           # Clamp 0-100
    throttle  = map_val(speed_pct, 0, 100, 0.0, 1.0)
    motor1.throttle = throttle * direction
    label = "Avant" if direction == DIR_FORWARD else "Arrière"
    print(f"[MOTEUR] {label} - {speed_pct}%")


def MotorRamp(direction, target_speed_pct, ramp_time=1.0, start_speed=0):
    target_speed_pct = max(0, min(100, target_speed_pct))
    steps      = 20
    step_delay = ramp_time / steps
    label      = "Avant" if direction == DIR_FORWARD else "Arrière"

    print(f"[RAMPE] {label} | {start_speed}% → {target_speed_pct}% en {ramp_time}s")

    for i in range(steps + 1):
        current_speed = start_speed + (target_speed_pct - start_speed) * i / steps
        Motor(direction, current_speed)
        time.sleep(step_delay)

    print(f"[RAMPE] Vitesse atteinte : {target_speed_pct}%")


def MotorFull(direction, target_speed_pct, ramp_time=1.0):
    MotorRamp(direction, target_speed_pct, ramp_time)   # Montée
    time.sleep(1.0)                                      # Maintien 1s
    MotorRamp(direction, 0, ramp_time, target_speed_pct) # Descente
    motorStop()


def set_angle(channel, angle):
    """Positionne un servo sur un angle (0-180°)."""
    s = servo.Servo(pca.channels[channel],
                    min_pulse=SERVO_MIN_PULSE,
                    max_pulse=SERVO_MAX_PULSE,
                    actuation_range=180)
    s.angle = max(0, min(180, angle))


def setDirection(angle):
    set_angle(SERVO_DIR_CHANNEL, angle)
    print(f"[SERVO] Direction → {angle}°")


def destroy():
    motorStop()
    setDirection(SERVO_CENTER)
    pca.deinit()
    print("[SYS] GPIO libérés.")


# ══════════════════════════════════════════════
#  MAIN — Commande manuelle
# ══════════════════════════════════════════════

def printMenu():
    print("\n╔═══════════════════════════════════════════╗")
    print("║       COMMANDE MANUELLE ROBOT             ║")
    print("╠═══════════════════════════════════════════╣")
    print("║  MOTEUR                                   ║")
    print("║   1  → Marche avant  (25%)                ║")
    print("║   2  → Marche arrière (25%)               ║")
    print("║   3  → Arrêt immédiat                     ║")
    print("║   4  → Rampe avant (0→100% en 1s)         ║")
    print("║   5  → Rampe arrière (0→100% en 1s)       ║")
    print("║   6  → Cycle complet (rampe+maintien+stop)║")
    print("║   7  → Vitesse/sens/rampe personnalisés   ║")
    print("╠═══════════════════════════════════════════╣")
    print("║  DIRECTION                                ║")
    print("║   8  → Centre                             ║")
    print("║   9  → Gauche                             ║")
    print("║   10 → Droite                             ║")
    print("║   11 → Angle personnalisé                 ║")
    print("╠═══════════════════════════════════════════╣")
    print("║   0  → Quitter                            ║")
    print("╚═══════════════════════════════════════════╝")


def main():
    last_angle = 90
    setDirection(SERVO_CENTER)

    while True:
        printMenu()
        cmd = input("\nCommande : ").strip()

        try:
            code = int(cmd)

            # ─── Moteur ───
            if code == 1:
                Motor(DIR_FORWARD, 25)

            elif code == 2:
                Motor(DIR_BACKWARD, 25)

            elif code == 3:
                motorStop()

            elif code == 4:
                MotorRamp(DIR_FORWARD, 100, ramp_time=1.0)

            elif code == 5:
                MotorRamp(DIR_BACKWARD, 100, ramp_time=1.0)

            elif code == 6:
                sens = input("Sens (1=avant, -1=arrière) : ").strip()
                MotorFull(int(sens), 100, ramp_time=1.0)

            elif code == 7:
                spd   = int(input("Vitesse cible (0-100%) : ").strip())
                sens  = int(input("Sens (1=avant, -1=arrière) : ").strip())
                ramp  = float(input("Durée rampe (secondes) : ").strip())
                MotorRamp(sens, spd, ramp_time=ramp)

            # ─── Direction ───
            elif code == 8:
                setDirection(SERVO_CENTER)

            elif code == 9:
                setDirection(SERVO_LEFT)

            elif code == 10:
                setDirection(SERVO_RIGHT)

            elif code == 11:
                angle = int(input("Angle (0-180) : ").strip())
                setDirection(angle)

            elif code == 0:
                print("Arrêt du programme.")
                break

            else:
                print("Commande invalide.")

        except ValueError:
            print("Entrée invalide.")
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        destroy()