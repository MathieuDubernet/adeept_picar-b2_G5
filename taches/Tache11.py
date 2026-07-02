from Tache9 import AdeeptRobot
from Tache6 import Adeept_infrared
import threading
import time
import math

class Tache11Robot(AdeeptRobot):

    OBSTACLE_DIST  = 20.0   # cm, seuil d'arrêt d'urgence
    LIMIT_DISTANCE_WITHOUT_IR = 30.0   # cm parcourus sans ligne détectée avant d'abandonner
    CRUISE_SPEED   = 22   # % vitesse de croisière
    SEARCH_SPEED   = 45   # % vitesse quand on traverse un [0,0,0] à l'aveugle
    ACCEL_TIME     = 1.5  # s, durée de la rampe d'accélération
    HAZARD_PERIOD  = 0.25 # s, période de clignotement des feux de détresse
    LOOP_DELAY     = 0.01 # s, délai de la boucle principale
    BACKWARD_DELAY = 1
    DEFAULT_ANGLE = 140
    TARGET_ANGLE = DEFAULT_ANGLE
    ACTUAL_DIRECTION = 2   # 0 = extreme droite, 1 = droit, 2 = milieu, 3 = gauche, 4 = extreme gauche

    SLIGHT_DEVIATION = 12      # utilisé pour la récupération de virage
    BIG_DEVIATION = 45         # borne max du braquage
    KP = 16                    # gain proportionnel : erreur 1 -> 16°, erreur 2 -> 32°
    KD = 0

    def __init__(self, infrared):
        super().__init__()
        self.infrared = infrared
        self.actualAngle = self.servo_controller.current_angles[0]
        self.lastIRstate = [[1, 1, 1]] * 100
        self.last_error = 0

    def timeByDistSpeed(self, distance, speed):
        b = 1.3 * speed - 10.3
        return (-b + math.sqrt(b**2 + 7.2 * distance)) / 3.6

    def distance(self, speed, time):
        """Calcule la distance parcourue"""
        return (1.3 * speed - 10.3) * time + 1.8 * time**2

    def is_dash(self):
        """
        Retourne True si le [0,0,0] est un blanc de pointillé (ligne droite),
        False si c'est une sortie de virage.

        On regarde les derniers états avant la perte de ligne. Si le robot allait
        tout droit, l'historique est centré ; s'il déviait fort, on y trouve des
        [1,0,0] ou [0,0,1].
        """

        WINDOW = 15  # nombre d'états récents à analyser

        # on ne garde que les états où la ligne était encore visible
        last_seen = [s for s in self.lastIRstate if s != [0, 0, 0]][:WINDOW]

        if not last_seen:
            return True  # pas d'historique, on tente le pointillé, c'est moins risqué

        strong_deviation = ([1, 0, 0], [0, 0, 1])
        count_strong = sum(1 for s in last_seen if s in strong_deviation)

        # au moins deux états en forte déviation, on considère que c'était un virage
        return count_strong < 2

    def _reading_to_error(self, reading):
        """Erreur de position de la ligne. Signe + = même sens que le code d'origine.
        1 = légère déviation, 2 = forte. None = lecture ambiguë (on tient le cap)."""
        mapping = {
            (1, 1, 1):  0,
            (1, 1, 0): +1,
            (1, 0, 0): +2,
            (0, 1, 1): -1,
            (0, 0, 1): -2,
            (0, 1, 0):  0,   # seul le centre allumé, on est centré
        }
        return mapping.get(tuple(reading), None)

    def checking_infrared(self, line_binding):
        if not isinstance(line_binding, list) or len(line_binding) != 3:
            return

        if line_binding == [0, 0, 0]:
            if self.is_dash():
                # cas du pointillé : on garde le cap et on traverse le blanc tout droit
                self.servo_controller.setAngle(0, self.DEFAULT_ANGLE)
                self.actualAngle = self.DEFAULT_ANGLE

                self.motor.Motor(self.motor.DIR_FORWARD, self.SEARCH_SPEED)

                i = 0
                # temps max pour parcourir la distance limite à SEARCH_SPEED
                max_time = self.timeByDistSpeed(self.LIMIT_DISTANCE_WITHOUT_IR, self.SEARCH_SPEED)
                while self.infrared.read() == [0, 0, 0] and i < max_time:
                    i += 0.01
                    time.sleep(0.01)

                if self.infrared.read() == [0, 0, 0]:
                    self.motor.motorStop()
                    self.servo_controller.setAngle(0, self.DEFAULT_ANGLE)
                    self.motor.Motor(self.motor.DIR_BACKWARD, self.CRUISE_SPEED)
                    while self.infrared.read() != [1, 1, 1]:
                        time.sleep(0.01)
                    self.motor.motorStop()
                    self.servo_controller.setAngle(0, self.DEFAULT_ANGLE)
                    self.actualAngle = self.DEFAULT_ANGLE
                    self.TARGET_ANGLE = self.DEFAULT_ANGLE
                    self.motor.Motor(self.motor.DIR_FORWARD, self.CRUISE_SPEED)
                else:
                    self.motor.Motor(self.motor.DIR_FORWARD, self.CRUISE_SPEED)

            else:
                # virage perdu : on accélère pour aller rechercher la ligne
                self.motor.Motor(self.motor.DIR_FORWARD, self.SEARCH_SPEED)

                i = 0
                max_time = self.timeByDistSpeed(self.LIMIT_DISTANCE_WITHOUT_IR * 5, self.SEARCH_SPEED)
                while self.infrared.read() == [0, 0, 0] and i < max_time:
                    self.lastIRstate.insert(0, self.infrared.read())  # ajoute en tête
                    self.lastIRstate.pop()
                    i += 0.01
                    time.sleep(0.01)

                if self.infrared.read() == [0, 0, 0]:
                    self.motor.motorStop()
                    self.servo_controller.setAngle(0, self.DEFAULT_ANGLE * 2 - self.actualAngle)
                    self.motor.Motor(self.motor.DIR_BACKWARD, self.CRUISE_SPEED)
                    while self.infrared.read() != [1, 1, 1]:
                        time.sleep(0.01)
                    self.motor.motorStop()
                    self.TARGET_ANGLE = self.DEFAULT_ANGLE + self.SLIGHT_DEVIATION
                    self.motor.Motor(self.motor.DIR_FORWARD, self.CRUISE_SPEED)
                else:
                    # ligne retrouvée, on repasse en vitesse de croisière
                    self.motor.Motor(self.motor.DIR_FORWARD, self.CRUISE_SPEED)

            self.last_error = 0      # on repart d'une erreur nulle après la récupération

        else:
            error = self._reading_to_error(line_binding)
            if error is None:
                error = self.last_error          # lecture ambiguë → on maintient le cap

            # P : proportionnel à l'erreur, plus de palier brutal
            p_term = self.KP * error

            # D : amortit la variation de l'erreur
            d_term = self.KD * (error - self.last_error)

            target = self.DEFAULT_ANGLE + p_term + d_term

            # bornage de sécurité
            lo = self.DEFAULT_ANGLE - self.BIG_DEVIATION
            hi = self.DEFAULT_ANGLE + self.BIG_DEVIATION
            self.TARGET_ANGLE = max(lo, min(hi, target))
            self.ACTUAL_DIRECTION = 2 - error
            self.last_error = error

        # --- queue commune (inchangée) ---
        if self.TARGET_ANGLE != self.actualAngle:
            self.servo_controller.setAngle(0, self.TARGET_ANGLE)
        self.actualAngle = self.servo_controller.current_angles[0]
        self.speedbasedOnDirection()
        self.lastIRstate.insert(0, line_binding)
        self.lastIRstate.pop()

    def speedbasedOnDirection(self):
        angle_rad = math.radians(self.actualAngle - self.DEFAULT_ANGLE)

        # Cos de l angle
        cos_theta = math.cos(angle_rad)

        # Éviter la division par zéro (si angle ≈ 90°)
        if cos_theta < 0.1:
            cos_theta = 0.1  # Limite max

        # Vitesse à commander aux roues
        vitesse_roues = self.CRUISE_SPEED / cos_theta

        # print(f"\r[VITESSE] angle={self.actualAngle:.1f} | roues={vitesse_roues:.1f}%", end="", flush=True)

        # self.motor.Motor(self.motor.DIR_FORWARD, vitesse_roues)

    def run(self):
        """Boucle principale du robot."""

        # on lance la lecture clavier dans son propre thread
        kbd_thread = threading.Thread(target=self.read_keyboard, daemon=True)
        kbd_thread.start()
        self.servo_controller.setAngle(0, self.DEFAULT_ANGLE)

        try:
            while self._running:

                self.process_command()

                distance = self.ultra.checkdist()

                # arrêt d'urgence si un obstacle est trop proche pendant le déplacement
                if self._state == "MOVE" and distance < self.OBSTACLE_DIST:
                    print("STOP !!")
                    self.emergency_stop(distance)

                elif self._state == "HAZARD":
                    self.update_hazard_lights()
                    print(f"[SONAR] Distance : {distance:.1f} cm", end='\r')

                elif self._state == "MOVE":
                    line_binding = self.infrared.read()
                    self.checking_infrared(line_binding)

                time.sleep(self.LOOP_DELAY)



        except KeyboardInterrupt:
            print("\n[SYS] Interruption clavier.")
        finally:
            self.destroy()


if __name__ == "__main__":
    robot = None
    infrared = None
    try:
        infrared = Adeept_infrared()
        robot = Tache11Robot(infrared)
        robot.run()
    except Exception as e:
        print(f"[ERREUR] {e}")
    finally:
        if robot:
            robot.destroy()