# Tant que le robot est actif :
# 1. Orienter les roues vers la source lumineuse
# 2. Orienter la caméra dans le même angle
# 3. Mesurer la distance devant le robot
# 4. Si distance < 20 cm :
#       - arrêter le robot
#       - faire clignoter les feux de détresse
#       - attendre 1 seconde
#       - reculer d’environ 30 cm à vitesse réduite avec un son "bip-bip"
#       - arrêter le robot
#       - attendre 2 secondes
# 5. Sinon :
#       - avancer à vitesse modérée
# 6. Recommencer
from gpiozero import TonalBuzzer
from Tache1 import Adeept_LED_Control
from Tache3 import ServoController
from Tache4 import AdeeptMotorController
from Tache5 import AdeeptUltra
from Tache8 import ADS7830

import threading
import time


class Tache10(object):
    def __init__(self, ads, controller, ultra, motor, leds):
        print("Tâche 10 : Suivi de source lumineuse avec détection d'obstacle")
        print("Initialisation des composants...")

        self.ads = ads
        self.controller = controller
        self.ultra = ultra
        self.motor = motor
        self.leds = leds

        self.actual_speed = 0
        self.run_speed = 25
        self.tb = TonalBuzzer(18) 

        print("Initialisation terminée.")
    
    def bip_bip(self):
        """
        Play a musical tune using the buzzer.
        :param tune: List of tuples (note, duration), 
        where each tuple represents a note and its duration.
        """
        while self.warning_active:
            try:
                self.tb.play("F4")
                time.sleep(0.15)
                self.tb.stop()
                time.sleep(0.10)
                if not self.warning_active:
                    break
                self.tb.play("A#3")
                time.sleep(0.15)
                self.tb.stop()
                time.sleep(0.10)
            except Exception:
                break
        self.tb.stop()


    def detresse(self):
        while self.warning_active:
            try:
                self.leds.setAllRGBColor(255, 120, 0)
                time.sleep(0.12)
                self.leds.all_off()
                time.sleep(0.12)
            except Exception:
                break
        
    def recul_avec_bip(self, duree=1.2):
        self.warning_active = True

        thread_bip = threading.Thread(target=self.bip_bip)
        thread_led = threading.Thread(target=self.detresse)

        thread_bip.start()
        thread_led.start()

        self.motor.MotorRamp(self.motor.DIR_BACKWARD, self.run_speed, start_speed=self.actual_speed)
        self.actual_speed = self.run_speed
        time.sleep(duree/2)
        self.motor.MotorRamp(self.motor.DIR_BACKWARD, 0, start_speed=self.actual_speed)
        self.actual_speed = 0

        self.warning_active = False

        thread_bip.join()
        thread_led.join()

        self.tb.stop()
        self.leds.all_off()

    def run(self):
        print("Démarrage de la tâche 10...")
        try:
            self.leds.setup()
            last_angle = 0

            while True:
                angle = self.ads.turnWheelsToLight()

                if last_angle != angle:
                    last_angle = angle
                    self.controller.setAngle(1, angle)

                ultrasonic_distance = self.ultra.checkdist()

                if(ultrasonic_distance < 20):  # 20 cm = 200 mm
                    print("Obstacle détecté ! Exécution de la séquence d'évitement...")
                    self.motor.motorStop()
                    self.actual_speed = 0

                    self.recul_avec_bip(duree=2.4)
                else:
                    if self.actual_speed == 0:
                        self.motor.MotorRamp(self.motor.DIR_FORWARD, self.run_speed, start_speed=self.actual_speed)   
                        self.actual_speed = self.run_speed
                time.sleep(0.01)
                pass

        except KeyboardInterrupt:
            print("\nArrêt demandé par l'utilisateur.")
        finally:
            self.warning_active = False
            self.tb.stop()
            self.motor.destroy()
            self.leds.destroy()
            

            print("Nettoyage des ressources...")


if __name__ == "__main__":
    controller = ServoController()
    ads = ADS7830(controller)
    ultra = AdeeptUltra()
    motor = AdeeptMotorController(controller)
    leds = Adeept_LED_Control()
    tache10 = Tache10(ads, controller, ultra, motor, leds)
    tache10.run()