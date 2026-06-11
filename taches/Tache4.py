import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import motor, servo


class AdeeptMotorController:

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

    def __init__(self, pca=None):
        """
        Initialise le contrôleur moteur/direction.
        Si aucun PCA9685 n'est fourni, en crée un (bus I2C, fréquence 50 Hz).
        Construit ensuite le moteur M1 sur ses deux canaux et active le mode
        SLOW_DECAY (freinage progressif).

        Paramètres:
        - pca: instance PCA9685 partagée (None = la classe crée la sienne)
        """
        self._owns_pca = (pca is None)
        if pca is None:
            self.i2c = busio.I2C(SCL, SDA)
            self.pca = PCA9685(self.i2c, address=0x5f)
            self.pca.frequency = 50
        else:
            self.pca = pca

        self.motor1 = motor.DCMotor(self.pca.channels[self.MOTOR_M1_IN1],
                                   self.pca.channels[self.MOTOR_M1_IN2])
        self.motor1.decay_mode = motor.SLOW_DECAY

    def motorStop(self):
        """Coupe le moteur (throttle = 0)."""
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
        speed_pct = max(0, min(100, speed_pct))
        self.motor1.throttle = (speed_pct / 100) * direction
        label = "Avant" if direction == self.DIR_FORWARD else "Arrière"
        print(f"[MOTEUR] {label} - {speed_pct}%")

    def set_angle(self, channel, angle):
        """
        Positionne un servo sur un angle (0-180°).
        Crée l'objet Servo sur le canal demandé avec les largeurs d'impulsion
        min/max de la classe, puis applique l'angle borné entre 0 et 180.

        Paramètres:
        - channel: numéro de canal PCA9685 du servo
        - angle: angle cible en degrés (0-180)
        """
        s = servo.Servo(self.pca.channels[channel],
                        min_pulse=self.SERVO_MIN_PULSE,
                        max_pulse=self.SERVO_MAX_PULSE,
                        actuation_range=180)
        s.angle = max(0, min(180, angle))

    def setDirection(self, angle):
        """
        Oriente les roues avant via le servo de direction.

        Paramètres:
        - angle: angle de braquage en degrés (voir SERVO_LEFT/CENTER/RIGHT)
        """
        self.set_angle(self.SERVO_DIR_CHANNEL, angle)
        print(f"[SERVO] Direction → {angle}°")

    def destroy(self):
        """
        Arrêt propre : coupe le moteur, recentre la direction et libère le
        PCA9685 (uniquement si cette instance en est propriétaire).
        """
        self.motorStop()
        self.setDirection(self.SERVO_CENTER)
        if self._owns_pca:
            self.pca.deinit()
        print("[SYS] GPIO libérés.")

    def MotorSetSilent(self, direction, speed_pct):
            """Applique la vitesse sans affichage."""
            speed_pct = max(0, min(100, speed_pct))
            self.motor1.throttle = (speed_pct / 100) * direction

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
            current_speed = start_speed + (target_speed_pct - start_speed) * i / steps
            self.MotorSetSilent(direction, current_speed)
            time.sleep(step_delay)

        print(f"[RAMPE] Vitesse atteinte : {target_speed_pct}%")

    def MotorFull(self, direction, target_speed_pct, ramp_time=1.0):
        """
        Cycle complet : montée en rampe, maintien 1 s, descente en rampe, arrêt.
        """
        self.MotorRamp(direction, target_speed_pct, ramp_time)                 # montée
        time.sleep(1.0)                                                        # maintien
        self.MotorRamp(direction, 0, ramp_time, start_speed=target_speed_pct)  # descente
        self.motorStop()

def main(AdeeptMotor):
    AdeeptMotor.setDirection(AdeeptMotor.SERVO_CENTER)

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
                AdeeptMotor.Motor(AdeeptMotor.DIR_FORWARD, 25)
            elif cmd == "2":
                AdeeptMotor.Motor(AdeeptMotor.DIR_BACKWARD, 25)
            elif cmd == "3":
                AdeeptMotor.motorStop()
            elif cmd == "4":
                AdeeptMotor.setDirection(AdeeptMotor.SERVO_CENTER)
            elif cmd == "5":
                AdeeptMotor.setDirection(AdeeptMotor.SERVO_LEFT)
            elif cmd == "6":
                AdeeptMotor.setDirection(AdeeptMotor.SERVO_RIGHT)
            else:
                print("Commande invalide (0 à 6).")

        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    AdeeptMotor = None  
    try:
        AdeeptMotor = AdeeptMotorController()
        main(AdeeptMotor)
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        if AdeeptMotor is not None:
            AdeeptMotor.destroy()