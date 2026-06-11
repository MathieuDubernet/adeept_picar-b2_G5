import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo


class ServoController(object):
    def __init__(self, pca=None):
        self.address = 0x5F
        self.frequency = 50
        self.angle_min = 10
        self.angle_max = 170
        self.servo_test = 4
        self.servos_robot = [0, 1, 2]
        self.all_servos = [0, 1, 2, 4]

        self.i2c = busio.I2C(SCL, SDA)
        self._owns_pca = (pca is None)
        if pca is None:
            self.pca = PCA9685(self.i2c, address=self.address)
        else:
            self.pca = pca
        self.pca.frequency = self.frequency

        self.servos = {
            0: servo.Servo(self.pca.channels[0], min_pulse=500, max_pulse=2400, actuation_range=180),
            1: servo.Servo(self.pca.channels[1], min_pulse=500, max_pulse=2400, actuation_range=180),
            2: servo.Servo(self.pca.channels[2], min_pulse=500, max_pulse=2400, actuation_range=180),
            4: servo.Servo(self.pca.channels[4], min_pulse=500, max_pulse=2400, actuation_range=180),
        }

    def clampAngle(self, angle):
        angle = int(angle)
        if angle < self.angle_min:
            return self.angle_min
        if angle > self.angle_max:
            return self.angle_max
        return angle

    def setAngle(self, channel, angle):
        if channel not in self.servos:
            raise ValueError(f"Servo invalide: {channel}. Choix possibles: {self.all_servos}")

        safe_angle = self.clampAngle(angle)
        self.servos[channel].angle = safe_angle
        time.sleep(0.05)
        return safe_angle

    def centerAll(self):
        for ch in self.all_servos:
            self.setAngle(ch, 90)

    def testServo(self, channel):
        if channel not in self.servos:
            raise ValueError(f"Servo invalide: {channel}. Choix possibles: {self.all_servos}")

        print(f"Test du servo sur CH{channel}")
        for angle in [60, 90, 120, 90]:
            self.setAngle(channel, angle)
            print(f"CH{channel} -> {angle}°")
            time.sleep(1)

    def releaseAll(self):
        for ch in self.all_servos:
            try:
                self.servos[ch].angle = None
            except Exception:
                pass

    def cleanup(self):
        self.releaseAll()
        if self._owns_pca:
            self.pca.deinit()

if __name__ == "__main__":
    controller = ServoController()

    try:
        print("Initialisation OK")
        print("Étape 1 : test sécurité sur le servo libre CH4")
        controller.testServo(controller.servo_test)

        print("\nÉtape 2 : centrage des servos")
        controller.centerAll()

        print("\nÉtape 3 : commande manuelle")
        print("Servos disponibles : 0, 1, 2, 4")
        print(f"Angles autorisés : {controller.angle_min} à {controller.angle_max}")
        print("Commande : numero angle   (ex: 4 90)")
        print("Commandes spéciales : center, test, test 4, quit\n")

        while True:
            cmd = input(">>> ").strip().lower()
            parts = cmd.split()

            if not parts:
                continue

            if parts[0] in ("quit", "exit", "q"):
                break

            if parts[0] == "center":
                controller.centerAll()
                print("Tous les servos ont été centrés à 90°")
                continue

            if parts[0] == "test":
                if len(parts) == 1:
                    controller.testServo(controller.servo_test)
                elif len(parts) == 2:
                    controller.testServo(int(parts[1]))
                else:
                    print("Format invalide. Exemple : test 4")
                continue

            if len(parts) != 2:
                print("Format invalide. Exemple : 1 120")
                continue

            try:
                channel = int(parts[0])
                angle = int(parts[1])
                safe_angle = controller.setAngle(channel, angle)
                print(f"CH{channel} -> {safe_angle}°")
            except ValueError as e:
                print(f"Erreur : {e}")
            except Exception as e:
                print(f"Erreur inattendue : {e}")

    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur")
    finally:
        controller.cleanup()
        print("PCA9685 libéré proprement")