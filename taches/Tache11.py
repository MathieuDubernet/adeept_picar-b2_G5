from Tache9 import AdeeptRobot
from Tache6 import Adeept_infrared
import threading
import time

class Tache11Robot(AdeeptRobot):

    OBSTACLE_DIST  = 20.0   # cm — seuil d'arrêt d'urgence
    CRUISE_SPEED   = 20   # % vitesse de croisière
    ACCEL_TIME     = 1.5    # s — durée rampe accélération
    HAZARD_PERIOD  = 0.25   # s — période clignotement feux de détresse
    LOOP_DELAY     = 0.00   # s — délai boucle principale
    BACKWARD_DELAY = 1
    DEFAULT_ANGLE = 90

    SLIGHT_DEVIATION = 30
    BIG_DEVIATION = 70

    # 0 = droite
    # 180 = gauche

    def __init__(self, infrared):
        super().__init__()
        # attributs spécifiques à la tâche 11
        self.infrared = infrared
        self.actualAngle = self.servo_controller.current_angles[0]

    def trouverLaLigne(self, line_binding):
        return

    def checking_infrared(self, line_binding):
        if not isinstance(line_binding, list) or len(line_binding) != 3:
            return

        target_angle = self.DEFAULT_ANGLE

        if line_binding == [0, 1, 1]:
            if self.actualAngle >= self.DEFAULT_ANGLE:
                target_angle = self.DEFAULT_ANGLE - self.SLIGHT_DEVIATION
        elif line_binding == [1, 1, 0]:
            if self.actualAngle <= self.DEFAULT_ANGLE:
                target_angle = self.DEFAULT_ANGLE + self.SLIGHT_DEVIATION
        elif line_binding == [1, 0, 0]:
            target_angle = self.DEFAULT_ANGLE + self.BIG_DEVIATION
        elif line_binding == [0, 0, 1]:
            target_angle = self.DEFAULT_ANGLE - self.BIG_DEVIATION
        elif line_binding == [0, 0, 0]:
            self.motor.motorStop()
            self.motor.Motor(self.motor.DIR_BACKWARD, self.CRUISE_SPEED)
            time.sleep(0.5)
            self.motor.motorStop()
            target_angle = self.DEFAULT_ANGLE + self.SLIGHT_DEVIATION
            self.motor.Motor(self.motor.DIR_FORWARD, self.CRUISE_SPEED)

        if target_angle != self.actualAngle:
            self.servo_controller.setAngle(0, target_angle)
            self.actualAngle = target_angle

    def run(self):
        """Boucle principale du robot."""

        # Démarrage thread clavier
        kbd_thread = threading.Thread(target=self.read_keyboard, daemon=True)
        kbd_thread.start()
        self.servo_controller.setAngle(0, 90)

        try:
            while self._running:

                # 1. Traitement commande clavier
                self.process_command()

                # 2. Mesure distance
                distance = self.ultra.checkdist()

                # 3. Détection obstacle si en mouvement
                if self._state == "MOVE" and distance < self.OBSTACLE_DIST:
                    print("STOP !!")
                    self.emergency_stop(distance)

                # 4. Clignotement feux de détresse si HAZARD
                elif self._state == "HAZARD":
                    self.update_hazard_lights()
                    # Affichage distance pour info
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