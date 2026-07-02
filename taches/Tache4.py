import threading
import time
from adafruit_pca9685 import PCA9685
from adafruit_motor import motor
from Tache3 import ServoController


class AdeeptMotorController:

    MOTOR_M1_IN1 = 9      # Pôle positif M1(à changer selon le robot)
    MOTOR_M1_IN2 = 8       # Pôle négatif M1(à changer selon le robot)

    DIR_FORWARD  =  1
    DIR_BACKWARD = -1

    def __init__(self, servo_controller):
        """
        Initialise le contrôleur du moteur en utilisant en entrée le controleur des servos pour orienter les roues.
        Construit ensuite le moteur M1 sur ses deux canaux et active le mode SLOW_DECAY (freinage progressif).

        Paramètres:
        - servo_controller: instance ServoController déjà initialisée
        """
        self.servo_controller = servo_controller
        self.pca = servo_controller.pca
        self._owns_pca = False

        self.motor1 = motor.DCMotor(
            self.pca.channels[self.MOTOR_M1_IN1],
            self.pca.channels[self.MOTOR_M1_IN2]
        )
        self.motor1.decay_mode = motor.SLOW_DECAY

        self._stop_ramp = threading.Event()
        
        self.direction_channel = 0

        # Angles de direction configurables
        self.SERVO_CENTER    = 143 # à changer selon le robot
        self.SERVO_LEFT      = self.SERVO_CENTER - 30
        self.SERVO_RIGHT     = self.SERVO_CENTER + 30
        self.SERVO_SLIGHT_LEFT  = self.SERVO_CENTER - 15
        self.SERVO_SLIGHT_RIGHT = self.SERVO_CENTER + 15

    def motorStop(self):
        self.motor1.throttle = 0
        print("[MOTEUR] Arrêt")

    def Motor(self, direction, speed_pct):
        """
        Fait tourner le moteur dans un sens à une vitesse donnée.
        La vitesse en pourcentage (0-100) est bornée puis convertie en
        throttle (0.0-1.0), multiplié par le sens (+1 avant / -1 arrière).

        Paramètres:
        - direction: DIR_FORWARD (+1) ou DIR_BACKWARD (-1)
        - speed_pct: vitesse en pourcentage (0-100)
        """
        
        travelTime = time.time()

        speed_pct = max(0, min(100, speed_pct))
        self.motor1.throttle = (speed_pct / 100) * direction

    def setDirection(self, angle):
        """
        Oriente les roues en fonction de l'angle fourni.
        L'angle est contraint dans la plage [SERVO_LEFT, SERVO_RIGHT].

        Paramètres:
        - angle: angle cible pour le servo de direction (L C R)
        """
        if angle == "L":
            self.servo_controller.setAngle(1, self.SERVO_LEFT)
        elif angle == "R":
            self.servo_controller.setAngle(1, self.SERVO_RIGHT)
        elif angle == "C":
            self.servo_controller.setAngle(1, self.SERVO_CENTER)
        else:
            raise ValueError("Angle invalide. Choix possibles : 'L', 'C', 'R'.")

    def destroy(self):
        """
        Arrêt propre : coupe le moteur, recentre la direction et libère le PCA9685.
        """
        self.motorStop()
        self.servo_controller.setAngle(0, self.SERVO_CENTER)
        self.servo_controller.cleanup()
        print("[SYS] GPIO libérés.")

    def MotorRamp(self, direction, target_speed_pct, ramp_time=1.0, start_speed=0):
        """
        Amène progressivement la vitesse de start_speed à target_speed_pct
        en ramp_time secondes, par paliers (démarrage/arrêt en douceur).

        Paramètres:
        - direction: DIR_FORWARD (+1) ou DIR_BACKWARD (-1)
        - target_speed_pct: vitesse cible en pourcentage (0-100)
        - ramp_time: durée de la rampe en secondes
        - start_speed: vitesse de départ en pourcentage (0 par défaut)
        """
        target_speed_pct = max(0, min(100, target_speed_pct))
        steps      = 20
        step_delay = ramp_time / steps
        label      = "Avant" if direction == self.DIR_FORWARD else "Arrière"

        print(f"[RAMPE] {label} | {start_speed}% → {target_speed_pct}% en {ramp_time}s")

        for i in range(steps + 1):
            if self._stop_ramp.is_set(): break
            current_speed = start_speed + (target_speed_pct - start_speed) * i / steps
            self.Motor(direction, current_speed)
            time.sleep(step_delay)

        print(f"[RAMPE] Vitesse atteinte : {target_speed_pct}%")

def main(AdeeptMotor):
    print("Commande manuelle moteur / direction :")
    print(" 1 => Avancer (25%)")
    print(" 2 => Reculer (25%)")
    print(" 3 => Arrêt moteur")
    print(" 4 => Direction centre")
    print(" 5 => Direction gauche")
    print(" 6 => Direction droite")
    print(" 0 => Quitter")

    while True:
        try:
            cmd = input("\nCommande : ").strip()

            if cmd == "0":
                print("Arrêt du programme.")
                break
            elif cmd == "1":
                AdeeptMotor.MotorRamp(AdeeptMotor.DIR_FORWARD, 25)
            elif cmd == "2":
                AdeeptMotor.MotorRamp(AdeeptMotor.DIR_BACKWARD, 0, start_speed=25)
            elif cmd == "3":
                AdeeptMotor.motorStop()
            elif cmd == "4":
                AdeeptMotor.servo_controller.setAngle(0, AdeeptMotor.SERVO_CENTER)
            elif cmd == "5":
                AdeeptMotor.servo_controller.setAngle(0, AdeeptMotor.SERVO_LEFT)
            elif cmd == "6":
                AdeeptMotor.servo_controller.setAngle(0, AdeeptMotor.SERVO_RIGHT)
            else:
                print("Commande invalide (0 à 6).")

        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    servo_controller = ServoController()
    AdeeptMotor = AdeeptMotorController(servo_controller)
    try:
        main(AdeeptMotor)
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        AdeeptMotor.destroy()