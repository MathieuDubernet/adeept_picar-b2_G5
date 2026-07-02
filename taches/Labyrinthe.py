import time
import AnalyseFleche
from Tache5 import AdeeptUltra
from Tache4 import AdeeptMotorController
from Tache3 import ServoController

class Labyrinthe:

    def __init__(self):
        self.analyse = AnalyseFleche.AnalyseImage()
        self.ultra = AdeeptUltra()
        servo_controller = ServoController()
        self.motor = AdeeptMotorController(servo_controller)

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

                if direction_angle is not None: #Prend la direction de la fléche, s'avance devant le mur, recule pour manœuvrer et prend la direction de la fléche
                    if direction_angle == "droite":
                        direction_angle = "R"
                    elif direction_angle == "gauche":
                        direction_angle = "L"

                    self.motor.setDirection("C")
                    while distance > 20:
                        self.motor.Motor(AdeeptMotorController.DIR_FORWARD, 20)
                    self.motor.motorStop()
                    self.motor.Motor(AdeeptMotorController.DIR_BACKWARD, 20)
                    time.sleep(1)
                    self.motor.motorStop()

                    self.motor.setDirection(direction_angle)
                    self.motor.Motor(AdeeptMotorController.DIR_FORWARD, 20)
                    time.sleep(5)
                    self.motor.motorStop()
                else:
                    # Si aucune flèche détectée, avancer si la distance est suffisante
                    if distance > 20:  # Seuil de distance en cm
                        self.motor.Motor(AdeeptMotorController.DIR_FORWARD, 20)  # Avance à 50% de vitesse
                    else:
                        self.motor.motorStop()  # Arrêt si trop proche d'un obstacle


        except KeyboardInterrupt:
            print("Arrêt du labyrinthe.")
            self.motor.motorStop()

    

