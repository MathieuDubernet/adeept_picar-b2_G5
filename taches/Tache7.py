import time

from Tache1 import Adeept_LED_Control
from Tache2 import Adeept_SPI_LedPixel
from Tache3 import ServoController
from Tache4 import AdeeptMotorController
from Tache5 import AdeeptUltra
from Tache6 import Adeept_infrared


class RobotSystem:
    def __init__(self):
        # Dictionnaire central qui stocke tous les modules matériels du robot
        self.modules = {}

    def init_modules(self):
        # Initialisation de tous les périphériques dans un ordre logique
        print("[INIT] LEDs GPIO...")
        self.modules["led_gpio"] = Adeept_LED_Control()
        self.modules["led_gpio"].setup()

        print("[INIT] LEDs SPI...")
        self.modules["led_spi"] = Adeept_SPI_LedPixel(14, 128)

        print("[INIT] Servos...")
        self.modules["servo"] = ServoController()

        print("[INIT] Moteur...")
        # Le contrôleur moteur dépend ici du contrôleur de servo
        self.modules["motor"] = AdeeptMotorController(self.modules["servo"])

        print("[INIT] Ultrason...")
        self.modules["ultra"] = AdeeptUltra()

        print("[INIT] IR...")
        self.modules["ir"] = Adeept_infrared()

        print("[OK] Tous les modules sont initialisés.")

    def test_led_gpio(self):
        # Test simple des LEDs GPIO une par une
        led = self.modules["led_gpio"]
        print("[TEST] LEDs GPIO")
        led.all_off()
        for i in range(1, 10):
            led.set_led(i, True)
            time.sleep(0.2)
            led.set_led(i, False)

    def test_led_spi(self):
        # Test des LEDs SPI : allume brièvement chaque LED en rouge
        leds = self.modules["led_spi"]
        print("[TEST] LEDs SPI")
        for i in range(1, 15):
            leds.set_one_led(i, "R", 80)
            time.sleep(0.1)
            leds.set_one_led(i, "N", 0)

    def test_servos(self):
        # Recentre d'abord les servos, puis lance une séquence de test sur plusieurs canaux
        servo = self.modules["servo"]
        print("[TEST] Servos")
        servo.centerAll()
        time.sleep(1)

        # Vérifier que ces canaux existent bien dans ServoController
        for ch in [0, 1, 2, 15]:
            servo.testServo(ch)

    def test_motor(self):
        # Test basique moteur : avance, stop, recule, stop
        motor = self.modules["motor"]
        print("[TEST] Moteur")
        motor.MotorRamp(motor.DIR_FORWARD, 20, ramp_time=1.0)
        time.sleep(1)
        motor.motorStop()
        time.sleep(1)
        motor.MotorRamp(motor.DIR_BACKWARD, 20, ramp_time=1.0)
        time.sleep(1)
        motor.motorStop()

    def test_sensors(self):
        # Lecture répétée des capteurs pour vérifier qu'ils répondent correctement
        ultra = self.modules["ultra"]
        ir = self.modules["ir"]
        print("[TEST] Capteurs")
        for _ in range(10):
            print(f"Distance: {ultra.checkdist():.2f} cm | IR: {ir.read()}")
            time.sleep(0.3)

    def integration_loop(self):
        # Boucle principale : combine obstacle + suivi de ligne + retour visuel LEDs
        motor = self.modules["motor"]
        ultra = self.modules["ultra"]
        ir = self.modules["ir"]
        led = self.modules["led_gpio"]
        spi = self.modules["led_spi"]

        print("[RUN] Boucle d'intégration démarrée. Ctrl+C pour quitter.")
        while True:
            dist = ultra.checkdist()
            line = ir.read()   # Format attendu : [left, middle, right]

            # Priorité sécurité : si obstacle trop proche, arrêt immédiat
            if dist < 15:
                motor.motorStop()
                led.setAllRGBColor(255, 0, 0)
                spi.set_all_led_rgb([255, 0, 0])

            else:
                # Pas d'obstacle : LEDs vertes et comportement de suivi de ligne
                led.setAllRGBColor(0, 255, 0)
                spi.set_all_led_rgb([0, 50, 0])

                # Ligne détectée au centre -> avancer tout droit
                if line == [1, 0, 1] or line == [0, 1, 0]:
                    motor.servo_controller.setAngle(0, motor.SERVO_CENTER)
                    motor.Motor(motor.DIR_FORWARD, 25)

                # Ligne décalée à gauche -> orienter le servo vers la gauche
                elif line == [1, 1, 0]:
                    motor.servo_controller.setAngle(0, motor.SERVO_LEFT)
                    motor.Motor(motor.DIR_FORWARD, 20)

                # Ligne décalée à droite -> orienter le servo vers la droite
                elif line == [0, 1, 1]:
                    motor.servo_controller.setAngle(0, motor.SERVO_RIGHT)
                    motor.Motor(motor.DIR_FORWARD, 20)

                # Cas non reconnu : arrêt de sécurité
                else:
                    motor.motorStop()

            print(f"Distance={dist:.1f} cm | IR={line}")
            time.sleep(0.1)

    def cleanup(self):
        # Libération propre des ressources, même si une erreur survient
        print("[CLEANUP] Arrêt propre...")

        try:
            if "motor" in self.modules:
                self.modules["motor"].motorStop()
        except:
            pass

        try:
            if "led_gpio" in self.modules:
                self.modules["led_gpio"].destroy()
        except:
            pass

        try:
            if "led_spi" in self.modules:
                self.modules["led_spi"].led_close()
        except:
            pass

        try:
            if "servo" in self.modules:
                self.modules["servo"].cleanup()
        except:
            pass

        print("[OK] Ressources libérées.")


if __name__ == "__main__":
    robot = RobotSystem()
    try:
        # 1) Initialisation de tous les modules
        robot.init_modules()

        # 2) Série de tests unitaires avant le lancement réel
        robot.test_led_gpio()
        robot.test_led_spi()
        robot.test_servos()
        robot.test_motor()
        robot.test_sensors()

        # 3) Lancement de la boucle principale du robot
        robot.integration_loop()

    except KeyboardInterrupt:
        print("\n[STOP] Interruption utilisateur.")
    except Exception as e:
        print(f"[ERREUR] {e}")
    finally:
        # Toujours exécuté pour éviter de laisser le matériel actif
        robot.cleanup()