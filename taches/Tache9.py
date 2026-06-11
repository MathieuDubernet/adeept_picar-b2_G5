#!/usr/bin/env python3
# File name : Tache9_POO.py
# Adeept PiCar-B2 - Robot obstacle en POO (réutilise Tache1, Tache4, Tache5)

import sys
import threading
from time import sleep, time

# Import des classes des autres tâches
from Tache1 import Adeept_LED_Control
from Tache4 import AdeeptMotorController
from Tache5 import AdeeptUltra


# ══════════════════════════════════════════════
#  CLASSE PRINCIPALE DU ROBOT
# ══════════════════════════════════════════════

class AdeeptRobot:
    """
    Orchestre les sous-systèmes :
      - AdeeptMotorController  (Tache4) → moteur DC + servo direction
      - Adeept_LED_Control     (Tache1) → LEDs RGB + LEDs simples
      - AdeeptUltra            (Tache5) → capteur ultrason

    États possibles :
      STOP   → robot à l'arrêt
      MOVE   → robot en marche
      HAZARD → obstacle détecté, feux de détresse actifs
    """

    OBSTACLE_DIST  = 20.0   # cm — seuil d'arrêt d'urgence
    CRUISE_SPEED   = 40     # % vitesse de croisière
    ACCEL_TIME     = 1.5    # s — durée rampe accélération
    DECEL_TIME     = 0.5    # s — durée rampe décélération urgence
    HAZARD_PERIOD  = 0.25   # s — période clignotement feux de détresse
    LOOP_DELAY     = 0.05   # s — délai boucle principale

    def __init__(self):
        print("[SYS] Initialisation des sous-systèmes...")

        # Instanciation des sous-systèmes
        self.motor = AdeeptMotorController()
        self.leds  = Adeept_LED_Control()
        self.ultra = AdeeptUltra()

        # Setup LEDs (PWM + LED simples)
        self.leds.setup()

        # État interne
        self._state         = "STOP"
        self._running       = True
        self._command       = ""
        self._light_state   = False
        self._last_toggle   = time()
        self._destroyed = False

        # Mutex pour protéger _command entre threads
        self._cmd_lock = threading.Lock()

        print("[SYS] Initialisation terminée. Prêt.")
        print("[SYS] Commandes : 'M' → démarrer | 'A' ou 'a' → arrêter | 'Q' → quitter")


    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        print(f"[ÉTAT] {self._state} → {new_state}")
        self._state = new_state


    def _accelerate(self):
        """Rampe d'accélération progressive. Interruptible."""
        print(f"[MOTEUR] Accélération → {self.CRUISE_SPEED}% en {self.ACCEL_TIME}s")
        self.motor.MotorRamp(
            self.motor.DIR_FORWARD,
            self.CRUISE_SPEED,
            ramp_time=self.ACCEL_TIME
        )

    def _decelerate_emergency(self):
        """Décélération rapide d'urgence."""
        print("[MOTEUR] Décélération d'urgence...")
        self.motor.MotorRamp(
            self.motor.DIR_FORWARD,
            0,
            ramp_time=self.DECEL_TIME,
            start_speed=self.CRUISE_SPEED
        )
        self.motor.motorStop()

    def _startMove(self):
        """Démarre le robot : éteint les feux de détresse, accélère."""
        self._stopHazard()
        self.leds.setAllRGBColor(255, 255, 255)   # Phares blancs
        self.state = "MOVE"
        t = threading.Thread(target=self._accelerate, daemon=True)
        t.start()

    def _stopMove(self):
        """Arrêt manuel avec décélération."""
        self.state = "STOP"
        self.motor.MotorRamp(
            self.motor.DIR_FORWARD,
            0,
            ramp_time=1.0,
            start_speed=self.CRUISE_SPEED
        )
        self.motor.motorStop()
        self.leds.all_off()

    def _emergencyStop(self, distance):
        """Arrêt d'urgence sur obstacle détecté."""
        print(f"[OBSTACLE] Détecté à {distance:.1f} cm ! Arrêt d'urgence.")
        self.state = "HAZARD"
        self._decelerate_emergency()
        self._startHazard()

    def _startHazard(self):
        """Active le mode feux de détresse (clignotement orange)."""
        print("[DÉTRESSE] Feux de détresse ACTIVÉS")
        self._light_state = False
        self._last_toggle = time()

    def _stopHazard(self):
        """Désactive les feux de détresse."""
        if self._state == "HAZARD":
            print("[DÉTRESSE] Feux de détresse ÉTEINTS")
        self.leds.all_off()

    def _updateHazardLights(self):
        """
        À appeler à chaque tour de boucle quand state == HAZARD.
        Fait clignoter toutes les LEDs en orange à HAZARD_PERIOD.
        """
        now = time()
        if now - self._last_toggle >= self.HAZARD_PERIOD:
            self._light_state  = not self._light_state
            self._last_toggle  = now

            if self._light_state:
                # Orange sur LEDs RGB
                self.leds.setAllRGBColor(255, 80, 0)
                # LEDs simples allumées
                self.leds.set_led(1, True)
                self.leds.set_led(2, True)
                self.leds.set_led(3, True)
            else:
                self.leds.all_off()

    def _readKeyboard(self):
        """Thread : lit les commandes clavier sans bloquer la boucle principale."""
        while self._running:
            try:
                char = sys.stdin.readline().strip()
                if char:
                    with self._cmd_lock:
                        self._command = char
            except Exception:
                pass

    def _processCommand(self):
        """Traite la dernière commande reçue."""
        with self._cmd_lock:
            cmd = self._command
            self._command = ""

        if not cmd:
            return

        if cmd == 'M':
            if self._state in ("STOP", "HAZARD"):
                print("[ORDRE] Départ demandé.")
                self._startMove()
            else:
                print("[INFO] Robot déjà en marche.")

        elif cmd in ('A', 'a'):
            if self._state == "MOVE":
                print("[ORDRE] Arrêt manuel demandé.")
                self._stopMove()
            else:
                print("[INFO] Robot déjà arrêté.")

        elif cmd in ('Q', 'q'):
            print("[ORDRE] Quitter.")
            self._running = False

        else:
            print(f"[INFO] Commande inconnue : '{cmd}'")


    def run(self):
        """Boucle principale du robot."""

        # Démarrage thread clavier
        kbd_thread = threading.Thread(target=self._readKeyboard, daemon=True)
        kbd_thread.start()

        try:
            while self._running:

                # 1. Traitement commande clavier
                self._processCommand()

                # 2. Mesure distance
                distance = self.ultra.checkdist()

                # 3. Détection obstacle si en mouvement
                if self._state == "MOVE" and distance < self.OBSTACLE_DIST:
                    self._emergencyStop(distance)

                # 4. Clignotement feux de détresse si HAZARD
                elif self._state == "HAZARD":
                    self._updateHazardLights()
                    # Affichage distance pour info
                    print(f"[SONAR] Distance : {distance:.1f} cm", end='\r')

                sleep(self.LOOP_DELAY)

        except KeyboardInterrupt:
            print("\n[SYS] Interruption clavier.")
        finally:
            self.destroy()


    def destroy(self):
        """Libère tous les sous-systèmes proprement."""
        if self._destroyed:            
            return                     
        self._destroyed = True         

        self._running = False
        print("[SYS] Arrêt en cours...")
        self.motor.motorStop()
        self.leds.all_off()
        self.leds.destroy()
        self.motor.pca.deinit()
        print("[SYS] Tous les GPIO libérés.")


if __name__ == "__main__":
    robot = None
    try:
        robot = AdeeptRobot()
        robot.run()
    except Exception as e:
        print(f"[ERREUR] {e}")
    finally:
        if robot:
            robot.destroy()