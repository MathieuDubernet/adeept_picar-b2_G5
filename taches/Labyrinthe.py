import AnalyseFleche
import Tache5
import Tache4
from Tache3 import ServoController

class Labyrinthe:

    def __init__(self):
        self.analyse = AnalyseFleche.AnalyseImage()
        self.ultra = Tache5.AdeeptUltra()
        servo_controller = ServoController()
        self.motor = Tache4.AdeeptMotorController(servo_controller)

    def run(self):
        """
        Boucle principale du labyrinthe.
        Analyse l'image pour détecter les flèches, ajuste la direction du robot
        et contrôle le moteur en fonction de la distance mesurée par le capteur à ultrasons.
        """
        try:
            while True:
                # Analyse de l'image pour détecter les flèches
                direction_angle = self.analyse.Direction()
                distance = self.ultra.checkdist()

                if direction_angle is not None:
                    #TODO
                    None

        except KeyboardInterrupt:
            print("Arrêt du labyrinthe.")
            self.motor.motorStop()

    

