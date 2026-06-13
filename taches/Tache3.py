import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo


class ServoController(object):
    def __init__(self, pca=None):
        # Configuration matérielle
        self.address = 0x5F          # Adresse I2C du PCA9685
        self.frequency = 50          # 50 Hz = fréquence standard pour les servos
        self.angle_min = 10          # Limite basse pour éviter les butées mécaniques
        self.angle_max = 170         # Limite haute
        self.servo_test = 15         # Canal réservé aux tests (servo libre)
        self.servos_robot = [0, 1, 2]
        self.all_servos = [0, 1, 2, 15]

        self.i2c = busio.I2C(SCL, SDA)

        # Si aucun PCA fourni, on en crée un (et on sera responsable de le libérer)
        self._owns_pca = (pca is None)
        if pca is None:
            self.pca = PCA9685(self.i2c, address=self.address)
        else:
            self.pca = pca
        self.pca.frequency = self.frequency

        # Initialisation des servos avec plage de pulse adaptée à un 180°
        self.servos = {
            0: servo.Servo(self.pca.channels[0], min_pulse=500, max_pulse=2400, actuation_range=180),
            1: servo.Servo(self.pca.channels[1], min_pulse=500, max_pulse=2400, actuation_range=180),
            2: servo.Servo(self.pca.channels[2], min_pulse=500, max_pulse=2400, actuation_range=180),
            15: servo.Servo(self.pca.channels[15], min_pulse=500, max_pulse=2400, actuation_range=180),
        }

        # Position initiale supposée à 90° (centre) pour tous les servos
        self.current_angles = {ch: 90 for ch in self.all_servos}

    def clampAngle(self, angle):
        """Contraint l'angle dans la plage [angle_min, angle_max]."""
        angle = int(angle)
        if angle < self.angle_min:
            return self.angle_min
        if angle > self.angle_max:
            return self.angle_max
        return angle

    def setAngle(self, channel, angle, step=20, delay=0.1):
        """
        Déplace un servo vers l'angle cible de façon progressive (pas à pas)
        pour éviter les à-coups mécaniques.
        """
        if channel not in self.servos:
            raise ValueError(f"Servo invalide: {channel}. Choix possibles: {self.all_servos}")

        target = self.clampAngle(angle)
        current = self.current_angles[channel]

        if target == current:
            return target

        # Déplacement progressif vers la cible
        if target > current:
            angle_range = range(current, target + 1, step)
        else:
            angle_range = range(current, target - 1, -step)

        for a in angle_range:
            safe_a = self.clampAngle(a)
            self.servos[channel].angle = safe_a
            self.current_angles[channel] = safe_a
            time.sleep(delay)

        # Forcer la position finale exacte (le range peut ne pas l'atteindre pile)
        self.current_angles[channel] = target
        self.servos[channel].angle = target
        return target

    def centerAll(self):
        """Remet tous les servos à 90° (position neutre)."""
        for ch in self.all_servos:
            self.setAngle(ch, 90)

    def testServo(self, channel):
        """Séquence de test : fait bouger le servo sur quelques angles de référence."""
        if channel not in self.servos:
            raise ValueError(f"Servo invalide: {channel}. Choix possibles: {self.all_servos}")

        print(f"Test du servo sur CH{channel}")
        for angle in [60, 90, 120, 90]:
            self.setAngle(channel, angle)
            print(f"CH{channel} -> {angle}°")
            time.sleep(1)

    def releaseAll(self):
        """Coupe le signal PWM de tous les servos (ils ne maintiennent plus leur position)."""
        for ch in self.all_servos:
            try:
                self.servos[ch].angle = None
            except Exception:
                pass

    def cleanup(self):
        """Libère proprement les ressources : relâche les servos et désinitialise le PCA si on le possède."""
        self.releaseAll()
        if self._owns_pca:
            self.pca.deinit()

if __name__ == "__main__":
    controller = ServoController()

    try:
        print("Initialisation OK")
        print("Étape 1 : test sécurité sur le servo libre CH15")
        controller.testServo(controller.servo_test)

        print("\nÉtape 2 : centrage des servos")
        controller.centerAll()

        print("\nÉtape 3 : commande manuelle")
        print("Servos disponibles : 0, 1, 2, 15")
        print(f"Angles autorisés : {controller.angle_min} à {controller.angle_max}")
        print("Commande : numero angle   (ex: 15 90)")
        print("Commandes spéciales : center, test, test 15, quit\n")

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
                    print("Format invalide. Exemple : test 15")
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