from gpiozero import DistanceSensor
from time import sleep
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685


class AdeeptUltra:

    TRIG_PIN = 23
    ECHO_PIN = 24

    SERVO_HEAD_CHANNEL = 2   # Servo tête (haut/bas)
    SERVO_NECK_CHANNEL = 1   # Servo cou  (balayage gauche/droite)

    SCAN_MIN   = 30    # Angle minimum du balayage
    SCAN_MAX   = 150   # Angle maximum
    SCAN_STEP  = 5     # Pas en degrés
    SCAN_DELAY = 0.1   # Délai entre chaque pas (secondes)

    def __init__(self):
        # Capteur ultrason
        self.sensor = DistanceSensor(
            echo=self.ECHO_PIN,
            trigger=self.TRIG_PIN,
            max_distance=2          # Portée max 2m
        )

        # PCA9685
        self.i2c = busio.I2C(SCL, SDA)
        self.pca = PCA9685(self.i2c, address=0x5f)
        self.pca.frequency = 50

        # État du scan
        self.current_angle = self.SCAN_MIN
        self.scan_forward  = True   # True = vers SCAN_MAX


    def checkdist(self):
        return self.sensor.distance * 100


    def set_angle(self, channel, angle):
        """Positionne un servo sur un angle (0-180°)."""
        angle = max(0, min(180, angle))
        s = servo.Servo(
            self.pca.channels[channel],
            min_pulse=500,
            max_pulse=2400,
            actuation_range=180
        )
        s.angle = angle


    def scanStep(self):
        """
        Effectue un pas de balayage et retourne (angle, distance).
        À appeler en boucle depuis le main.
        """
        # Mise à jour de l'angle
        if self.scan_forward:
            self.current_angle += self.SCAN_STEP
            if self.current_angle >= self.SCAN_MAX:
                self.current_angle = self.SCAN_MAX
                self.scan_forward  = False
        else:
            self.current_angle -= self.SCAN_STEP
            if self.current_angle <= self.SCAN_MIN:
                self.current_angle = self.SCAN_MIN
                self.scan_forward  = True

        self.set_angle(self.SERVO_NECK_CHANNEL, self.current_angle)
        sleep(self.SCAN_DELAY)

        distance = self.checkdist()
        return self.current_angle, distance

    def destroy(self):
        self.pca.deinit()
        print("[SYS] PCA9685 libéré.")

if __name__ == "__main__":
    ultra = None
    try:
        ultra = AdeeptUltra()

        # Position initiale
        ultra.set_angle(ultra.SERVO_HEAD_CHANNEL, 80)   # Tête
        ultra.set_angle(ultra.SERVO_NECK_CHANNEL, ultra.SCAN_MIN)
        sleep(0.5)   # Attente position initiale

        print("Démarrage du scan ultrason...")
        print(f"Balayage : {ultra.SCAN_MIN}° → {ultra.SCAN_MAX}° | pas : {ultra.SCAN_STEP}°\n")

        while True:
            angle, distance = ultra.scanStep()
            print(f"Angle : {angle:3d}°  |  Distance : {distance:.2f} cm")

    except KeyboardInterrupt:
        print("\nArrêt du scan.")
    finally:
        if ultra:
            ultra.destroy()