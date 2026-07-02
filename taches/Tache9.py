import sys
import threading
from time import sleep, time
from adafruit_pca9685 import PCA9685

# Import des classes des autres tâches
from Tache1 import Adeept_LED_Control
from Tache2 import Adeept_SPI_LedPixel
from Tache3 import ServoController
from Tache4 import AdeeptMotorController
from Tache5 import AdeeptUltra


class AdeeptRobot:
    """
    Orchestre les sous-systèmes :
      - AdeeptMotorController  (Tache4) → moteur DC + servo direction
      - Adeept_LED_Control     (Tache1) → LEDs RGB + LEDs simples
      - AdeeptUltra            (Tache5) → capteur ultrason
      - Adeept_SPI_LedPixel    (Tache2) → bandeau LED SPI

    États possibles :
      STOP   → robot à l'arrêt
      MOVE   → robot en marche
      HAZARD → obstacle détecté, feux de détresse actifs
    """

    OBSTACLE_DIST = 20.0
    CRUISE_SPEED = 40
    ACCEL_TIME = 1.5
    HAZARD_PERIOD = 0.25
    LOOP_DELAY = 0.05

    def __init__(self):
        print("Initialisation des sous-systèmes...")

        self.servo_controller = ServoController()
        self.motor = AdeeptMotorController(self.servo_controller)
        self.leds = Adeept_LED_Control()
        self.SPIleds = Adeept_SPI_LedPixel()
        self.ultra = AdeeptUltra()

        self.leds.setup()

        self._state = "STOP"
        self._running = True
        self._command = ""
        self._light_state = False
        self._last_toggle = time()
        self._destroyed = False
        self._last_dir = "CENTER"
        self._accel_thread = None
        self._kbd_thread = None

        self._cmd_lock = threading.Lock()
        self._stop_event = threading.Event()

        print("Commandes : 'M' → démarrer | 'A' → arrêter | 'Q' → quitter")

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        print(f"[ÉTAT] {self._state} → {new_state}")
        self._state = new_state

    def accelerate(self):
        """Rampe d'accélération progressive, interruptible."""
        try:
            self.motor.MotorRamp(
                self.motor.DIR_FORWARD,
                self.CRUISE_SPEED,
                ramp_time=self.ACCEL_TIME
            )
        except Exception as e:
            if not self._stop_event.is_set():
                print(f"[ERREUR] Accélération : {e}")

    def stop_accel(self):
        """Interrompt proprement la rampe d'accélération et attend la fin du thread."""
        try:
            self.motor._stop_ramp.set()
        except Exception:
            pass

        if self._accel_thread is not None and self._accel_thread.is_alive():
            self._accel_thread.join(timeout=2.0)

        self._accel_thread = None

    def start_move(self):
        """Démarre le robot : éteint les feux de détresse, accélère."""
        self.stop_hazard()
        self.stop_accel()

        try:
            self.motor._stop_ramp.clear()
        except Exception:
            pass

        self.leds.setAllRGBColor(255, 255, 255)
        self.SPIleds.set_all_led_rgb([255, 255, 255])
        self.state = "MOVE"

        self._accel_thread = threading.Thread(target=self.accelerate, name="accel-thread")
        self._accel_thread.start()

    def stop_move(self):
        """Arrêt manuel avec rampe de décélération."""
        self.state = "STOP"
        self.stop_accel()

        try:
            self.motor._stop_ramp.clear()
        except Exception:
            pass

        self.motor.MotorRamp(
            self.motor.DIR_FORWARD,
            0,
            ramp_time=1.0,
            start_speed=self.CRUISE_SPEED
        )
        self.motor.motorStop()
        self.leds.all_off()
        self.SPIleds.set_all_led_rgb([0, 0, 0])

    def emergency_stop(self, distance):
        """Arrêt d'urgence sur obstacle détecté."""
        print(f"[OBSTACLE] Détecté à {distance:.1f} cm ! Arrêt d'urgence.")
        self.stop_accel()
        self.state = "HAZARD"
        self.motor.motorStop()
        self.start_hazard()

    def start_hazard(self):
        """Active le mode feux de détresse."""
        print("[DÉTRESSE] Feux de détresse ACTIVÉS")
        self._light_state = False
        self._last_toggle = time()

    def stop_hazard(self):
        """Désactive les feux de détresse."""
        if self._state == "HAZARD":
            print("[DÉTRESSE] Feux de détresse ÉTEINTS")
        self.leds.all_off()
        self.SPIleds.set_all_led_rgb([0, 0, 0])

    def update_hazard_lights(self):
        """Clignotement des feux de détresse."""
        now = time()
        if now - self._last_toggle >= self.HAZARD_PERIOD:
            self._light_state = not self._light_state
            self._last_toggle = now

            if self._light_state:
                self.leds.setAllRGBColor(255, 80, 0)
                self.leds.set_led(1, True)
                self.leds.set_led(2, True)
                self.leds.set_led(3, True)
                self.SPIleds.set_all_led_rgb([255, 80, 0])
            else:
                self.leds.all_off()
                self.SPIleds.set_all_led_rgb([0, 0, 0])

    def read_keyboard(self):
        """
        Thread clavier.
        Note: readline() reste bloquant, mais le thread n'est plus daemon.
        On force un arrêt coordonné via _stop_event et join au shutdown.
        """
        while not self._stop_event.is_set():
            try:
                char = sys.stdin.readline()
                if self._stop_event.is_set():
                    break
                if not char:
                    continue

                char = char.strip()
                if char:
                    with self._cmd_lock:
                        self._command = char
            except Exception as e:
                if not self._stop_event.is_set():
                    print(f"[ERREUR] Lecture clavier : {e}")
                break

    def process_command(self):
        """Traite la dernière commande reçue."""
        with self._cmd_lock:
            cmd = self._command
            self._command = ""

        if not cmd:
            return

        if cmd.upper() == 'M':
            if self._state in ("STOP", "HAZARD"):
                print("[ORDRE] Départ demandé.")
                self.start_move()
            else:
                print("[INFO] Robot déjà en marche.")

        elif cmd.upper() == 'A':
            if self._state == "MOVE":
                print("[ORDRE] Arrêt manuel demandé.")
                self.stop_move()
            else:
                print("[INFO] Robot déjà arrêté.")

        elif cmd.upper() == 'Q':
            print("[ORDRE] Quitter.")
            self._running = False
            self._stop_event.set()

        else:
            print(f"[INFO] Commande inconnue : '{cmd}'")

    def run(self):
        """Boucle principale du robot."""
        self._kbd_thread = threading.Thread(target=self.read_keyboard, name="keyboard-thread")
        self._kbd_thread.start()

        try:
            while self._running and not self._stop_event.is_set():
                self.process_command()

                distance = self.ultra.checkdist()

                if self._state == "MOVE" and distance < self.OBSTACLE_DIST:
                    self.emergency_stop(distance)

                elif self._state == "HAZARD":
                    self.update_hazard_lights()
                    print(f"[SONAR] Distance : {distance:.1f} cm", end='\r')

                sleep(self.LOOP_DELAY)

        except KeyboardInterrupt:
            print("\n[SYS] Interruption clavier.")
            self._running = False
            self._stop_event.set()

        finally:
            self.destroy()

    def destroy(self):
        """Libère tous les sous-systèmes proprement."""
        if self._destroyed:
            return
        self._destroyed = True

        self._running = False
        self._stop_event.set()

        print("Arrêt en cours...")

        self.stop_accel()

        try:
            self.motor.motorStop()
        except Exception as e:
            print(f"[WARN] motorStop: {e}")

        try:
            self.leds.all_off()
        except Exception as e:
            print(f"[WARN] leds.all_off: {e}")

        try:
            self.SPIleds.led_close()
        except Exception as e:
            print(f"[WARN] SPI leds close: {e}")

        try:
            self.leds.destroy()
        except Exception as e:
            print(f"[WARN] leds.destroy: {e}")

        try:
            self.servo_controller.cleanup()
        except Exception as e:
            print(f"[WARN] servo cleanup: {e}")

        if self._kbd_thread is not None and self._kbd_thread.is_alive():
            self._kbd_thread.join(timeout=1.0)

        print("Tous les GPIO libérés.")


if __name__ == "__main__":
    robot = None
    try:
        robot = AdeeptRobot()
        robot.run()
    except KeyboardInterrupt:
        print("\n[SYS] Interruption clavier (main).")
    except Exception as e:
        print(f"[ERREUR] {e}")
    finally:
        if robot:
            robot.destroy()