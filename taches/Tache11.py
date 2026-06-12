

import sys
import threading
from time import sleep, time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685

from Tache1 import Adeept_LED_Control
from Tache2 import Adeept_SPI_LedPixel
from Tache4 import AdeeptMotorController
from Tache5 import AdeeptUltra
from Tache6 import Adeept_infrared


class LineFollowerRobot:
    """
    Suivi de ligne noire sur fond blanc.

    Logique capteurs IR (gpiozero InputDevice) :
      value = 1  → surface blanche (réflexion forte)
      value = 0  → ligne noire  (réflexion faible)

    Stratégie de suivi :
      [0, 1, 0]  → tout droit
      [0, 0, 1]  → ligne à droite  → tourner droite
      [1, 0, 0]  → ligne à gauche  → tourner gauche
      [0, 0, 0]  → ligne perdue (virage serré) → continuer dernier cap
      [1, 1, 1]  → fin de parcours ou perte totale → arrêt
    """

    # ── Paramètres ──────────────────────────────────────────────────────────
    OBSTACLE_DIST   = 20.0   # cm — seuil d'arrêt d'urgence (paramétrable)
    LINE_SPEED      = 30     # % vitesse de suivi de ligne
    ACCEL_TIME      = 1.0    # s — rampe de démarrage
    HAZARD_PERIOD   = 0.25   # s — période clignotement feux détresse
    LOOP_DELAY      = 0.05   # s — délai boucle principale

    # Angles servo direction (à ajuster selon étalonnage physique)
    SERVO_CENTER    = 140
    SERVO_LEFT      = SERVO_CENTER - 30
    SERVO_RIGHT     = SERVO_CENTER + 30

    # ── Initialisation ───────────────────────────────────────────────────────
    def __init__(self, obstacle_dist: float = 20.0):
        self.OBSTACLE_DIST = obstacle_dist

        print("[SYS] Initialisation des sous-systèmes...")
        # Instance unique I2C + PCA9685 partagée entre moteur et servos
        self.i2c = busio.I2C(SCL, SDA)
        self.pca = PCA9685(self.i2c, address=0x5f)
        self.pca.frequency = 50

        self.motor   = AdeeptMotorController(pca=self.pca)
        self.leds    = Adeept_LED_Control()
        self.spileds = Adeept_SPI_LedPixel()
        self.ultra   = AdeeptUltra()
        self.ir      = Adeept_infrared()

        self.leds.setup()

        # État interne
        self._state        = "STOP"
        self._running      = True
        self._command      = ""
        self._cmd_lock     = threading.Lock()
        self._light_state  = False
        self._last_toggle  = time()
        self._last_dir     = "CENTER"   # dernier cap connu (mémoire de ligne)
        self._lost_since   = None       # timestamp du début de perte de ligne
        self._accel_thread = None
        self._destroyed    = False

        print(f"[SYS] Prêt. Distance obstacle : {self.OBSTACLE_DIST} cm")
        print("Commandes : 'M' → démarrer | 'A'/'a' → arrêter | 'Q'/'q' → quitter")

    # ── Propriété état ───────────────────────────────────────────────────────
    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        if new_state != self._state:
            print(f"[ÉTAT] {self._state} → {new_state}")
        self._state = new_state

    # ── Moteur ───────────────────────────────────────────────────────────────
    def _stop_accel(self):
        self.motor._stop_ramp.set()
        if self._accel_thread is not None:
            self._accel_thread.join()
            self._accel_thread = None

    def _accelerate(self):
        self.motor.MotorRamp(
            self.motor.DIR_FORWARD, self.LINE_SPEED, ramp_time=self.ACCEL_TIME
        )

    def _start_move(self):
        self._stop_hazard()
        self.motor._stop_ramp.clear()
        self.leds.setAllRGBColor(255, 255, 255)
        self.spileds.set_all_led_rgb([255, 255, 255])
        self.state = "MOVE"
        self._accel_thread = threading.Thread(target=self._accelerate, daemon=True)
        self._accel_thread.start()

    def _stop_move(self):
        self.state = "STOP"
        self._stop_accel()
        self.motor._stop_ramp.clear()
        self.motor.MotorRamp(
            self.motor.DIR_FORWARD, 0,
            ramp_time=0.5, start_speed=self.LINE_SPEED
        )
        self.motor.motorStop()
        self.leds.all_off()
        self.spileds.set_all_led_rgb([0, 0, 0])

    def _emergency_stop(self, distance: float):
        print(f"[OBSTACLE] {distance:.1f} cm — arrêt d'urgence !")
        self._stop_accel()
        self.state = "HAZARD"
        self.motor.motorStop()
        self._start_hazard()

    # ── Feux de détresse ─────────────────────────────────────────────────────
    def _start_hazard(self):
        print("[DÉTRESSE] Feux de détresse ACTIVÉS")
        self._light_state = False
        self._last_toggle = time()

    def _stop_hazard(self):
        if self._state == "HAZARD":
            print("[DÉTRESSE] Feux de détresse ÉTEINTS")
        self.leds.all_off()
        self.spileds.set_all_led_rgb([0, 0, 0])

    def _update_hazard_lights(self):
        now = time()
        if now - self._last_toggle >= self.HAZARD_PERIOD:
            self._light_state = not self._light_state
            self._last_toggle = now
            if self._light_state:
                self.leds.setAllRGBColor(255, 80, 0)
                for i in range(1, 4):
                    self.leds.set_led(i, True)
                self.spileds.set_all_led_rgb([255, 80, 0])
            else:
                self.leds.all_off()
                self.spileds.set_all_led_rgb([0, 0, 0])

    # ── Suivi de ligne ────────────────────────────────────────────────────────
    #
    # Tableau complet des 8 combinaisons IR (0=noir, 1=blanc) :
    #
    #  G  M  D   Interprétation              Action
    #  1  0  1   Ligne centrée               Tout droit
    #  0  0  1   Ligne déportée à gauche     Braquer gauche (fort)
    #  1  0  0   Ligne déportée à droite     Braquer droite (fort)
    #  0  0  0   Virage serré / large ligne  Continuer dernier cap
    #  0  1  0   Ligne sous G+M              Léger gauche
    #  1  1  0   Ligne sous M+D              Léger droite
    #  1  1  1   Plus de ligne visible       Continuer dernier cap + compteur
    #  0  1  1   (idem 0,1,0 inversé)        Léger gauche
    #
    # Un compteur _lost_count compte les cycles consécutifs sans ligne.
    # Au-delà de LOST_TIMEOUT secondes → arrêt (vraie fin de parcours).

    LOST_TIMEOUT = 2.0   # secondes sans voir la ligne avant arrêt définitif

    def _follow_line(self, ir_values: list):
        """
        Ajuste la direction et maintient la vitesse selon les capteurs IR.
        ir_values : [gauche, milieu, droite]  (0 = noir, 1 = blanc)
        """
        left, mid, right = ir_values
        line_seen = not (left == 1 and mid == 1 and right == 1)

        if line_seen:
            # ── Ligne visible : remettre le compteur à zéro ───────────────
            self._lost_since = None

            if left == 1 and mid == 0 and right == 1:
                # Ligne parfaitement centrée → tout droit
                self.motor.set_angle(self.motor.SERVO_DIR_CHANNEL, self.SERVO_CENTER)
                self._last_dir = "CENTER"

            elif left == 0 and mid == 0 and right == 1:
                # Ligne à gauche → braquer gauche (fort)
                self.motor.set_angle(self.motor.SERVO_DIR_CHANNEL, self.SERVO_LEFT)
                self._last_dir = "LEFT"

            elif left == 1 and mid == 0 and right == 0:
                # Ligne à droite → braquer droite (fort)
                self.motor.set_angle(self.motor.SERVO_DIR_CHANNEL, self.SERVO_RIGHT)
                self._last_dir = "RIGHT"

            elif left == 0 and mid == 1 and right == 1:
                # Ligne sous capteur gauche → léger gauche
                angle = self.SERVO_CENTER - (self.SERVO_CENTER - self.SERVO_LEFT) // 2
                self.motor.set_angle(self.motor.SERVO_DIR_CHANNEL, angle)
                self._last_dir = "LEFT"

            elif left == 1 and mid == 1 and right == 0:
                # Ligne sous capteur droit → léger droite
                angle = self.SERVO_CENTER + (self.SERVO_RIGHT - self.SERVO_CENTER) // 2
                self.motor.set_angle(self.motor.SERVO_DIR_CHANNEL, angle)
                self._last_dir = "RIGHT"

            elif left == 0 and mid == 0 and right == 0:
                # Virage serré / ligne très large → continuer dernier cap
                if self._last_dir == "LEFT":
                    self.motor.set_angle(self.motor.SERVO_DIR_CHANNEL, self.SERVO_LEFT)
                elif self._last_dir == "RIGHT":
                    self.motor.set_angle(self.motor.SERVO_DIR_CHANNEL, self.SERVO_RIGHT)
                else:
                    self.motor.set_angle(self.motor.SERVO_DIR_CHANNEL, self.SERVO_CENTER)

            elif left == 0 and mid == 1 and right == 0:
                # Les deux côtés sur noir, milieu blanc → centrer
                self.motor.set_angle(self.motor.SERVO_DIR_CHANNEL, self.SERVO_CENTER)
                self._last_dir = "CENTER"

        else:
            # ── Aucun capteur ne voit la ligne [1,1,1] ────────────────────
            # Démarrer ou continuer le chrono de perte
            if self._lost_since is None:
                self._lost_since = time()

            elapsed = time() - self._lost_since

            if elapsed >= self.LOST_TIMEOUT:
                print("\n[LIGNE] Ligne perdue trop longtemps — arrêt.")
                self._stop_move()
                return
            else:
                # Continuer sur le dernier cap connu en attendant de retrouver la ligne
                if self._last_dir == "LEFT":
                    self.motor.set_angle(self.motor.SERVO_DIR_CHANNEL, self.SERVO_LEFT)
                elif self._last_dir == "RIGHT":
                    self.motor.set_angle(self.motor.SERVO_DIR_CHANNEL, self.SERVO_RIGHT)
                else:
                    self.motor.set_angle(self.motor.SERVO_DIR_CHANNEL, self.SERVO_CENTER)

        # Maintenir la vitesse de suivi
        self.motor.MotorSetSilent(self.motor.DIR_FORWARD, self.LINE_SPEED)

    # ── Clavier ───────────────────────────────────────────────────────────────
    def _read_keyboard(self):
        while self._running:
            try:
                char = sys.stdin.readline().strip()
                if char:
                    with self._cmd_lock:
                        self._command = char
            except Exception:
                pass

    def _process_command(self):
        with self._cmd_lock:
            cmd = self._command
            self._command = ""

        if not cmd:
            return

        if cmd == 'M':
            if self._state in ("STOP", "HAZARD"):
                print("[ORDRE] Départ suivi de ligne.")
                self._start_move()
            else:
                print("[INFO] Robot déjà en marche.")

        elif cmd in ('A', 'a'):
            if self._state == "MOVE":
                print("[ORDRE] Arrêt manuel.")
                self._stop_move()
            else:
                print("[INFO] Robot déjà arrêté.")

        elif cmd in ('Q', 'q'):
            print("[ORDRE] Quitter.")
            self._running = False

        else:
            print(f"[INFO] Commande inconnue : '{cmd}'")

    # ── Boucle principale ─────────────────────────────────────────────────────
    def run(self):
        kbd = threading.Thread(target=self._read_keyboard, daemon=True)
        kbd.start()

        try:
            while self._running:
                # 1. Commandes clavier
                self._process_command()

                # 2. Mesure distance obstacle
                distance = self.ultra.checkdist()

                # 3. Logique selon l'état
                if self._state == "MOVE":
                    # Détection obstacle prioritaire
                    if distance < self.OBSTACLE_DIST:
                        self._emergency_stop(distance)
                    else:
                        # Lecture IR et suivi de ligne
                        ir = self.ir.read()
                        print(
                            f"[IR] G={ir[0]} M={ir[1]} D={ir[2]} | "
                            f"Dist={distance:.1f} cm | Cap={self._last_dir}",
                            end='\r'
                        )
                        self._follow_line(ir)

                elif self._state == "HAZARD":
                    self._update_hazard_lights()
                    print(f"[SONAR] {distance:.1f} cm — en attente de 'M'", end='\r')

                sleep(self.LOOP_DELAY)

        except KeyboardInterrupt:
            print("\n[SYS] Interruption clavier.")
        finally:
            self.destroy()

    # ── Nettoyage ─────────────────────────────────────────────────────────────
    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        self._running = False
        print("\n[SYS] Arrêt en cours...")
        self._stop_accel()
        self.motor.motorStop()
        self.motor.set_angle(self.motor.SERVO_DIR_CHANNEL, self.SERVO_CENTER)
        self.leds.all_off()
        self.spileds.led_close()
        self.leds.destroy()
        self.pca.deinit()
        print("[SYS] Tous les GPIO libérés.")


# ── Entrée principale ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    # La distance obstacle est paramétrable en argument (ex: python Tache11.py 15)
    import sys as _sys
    obstacle_dist = float(_sys.argv[1]) if len(_sys.argv) > 1 else 20.0

    robot = None
    try:
        robot = LineFollowerRobot(obstacle_dist=obstacle_dist)
        robot.run()
    except Exception as e:
        print(f"[ERREUR] {e}")
    finally:
        if robot:
            robot.destroy()
