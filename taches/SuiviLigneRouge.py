import time
from collections import deque

import numpy as np
import cv2

from Tache3 import ServoController
from Tache4 import AdeeptMotorController

try:
    from picamera2 import Picamera2
    _HAS_PICAM2 = True
except ImportError:
    Picamera2 = None
    _HAS_PICAM2 = False


class SuiviLigneRouge:
    """

    """

    def __init__(self):
        self.LARGEUR, self.HAUTEUR = 640, 480

        self.CENTRE_DIRECTION = 140     # angle CH0 "roues droites"
        self.DELTA_MAX        = 40      # amplitude max de braquage (deg)
        self.KP               = 45      # gain proportionnel
        self.KD               = 0       # gain derive (0 = P pur)
        self.SENS_DIRECTION   = -1      # -1 : braquage inverse.
        self.SEUIL_DEADBAND   = 8       # zone morte en % d'ecart : en dessous = tout droit

        self.VITESSE_CROISIERE = 25     # % de la vitesse max
        self.ALPHA_VITESSE     = 0.1    # reduction de vitesse en virage (0 = constante)

        self.TILT_CAMERA     = 60       # à changer selon le robot
        self.CENTRE_COU      = 92       # à changer selon le robot
        self.FLIP_HORIZONTAL = False    # True si l'image est le miroir gauche-droite du reel

        self.MOTEUR_ACTIF = True        # False : observe detection

        # Bande d'analyse : bas de l'image.
        self.BANDE_HAUT = int(self.HAUTEUR * 0.75)
        self.BANDE_BAS  = self.HAUTEUR

        # Masque rouge HSV (le rouge est a cheval sur H=0 et H=180).
        self.ROUGE_BAS_1 = np.array([0,   120, 100]); self.ROUGE_HAUT_1 = np.array([10,  255, 255])
        self.ROUGE_BAS_2 = np.array([170, 120, 100]); self.ROUGE_HAUT_2 = np.array([180, 255, 255])

        self.MIN_PIXELS_ROUGE_IMG    = 400   # sous ce seuil : rouge absent du champ
        self.DELAI_ARRET_APRES_ROUGE = 0.5   # s sans rouge visible avant l'arret
        self.SORTIE_BAS_Y            = int(self.HAUTEUR * 0.80)

        self.MIN_PIXELS_ROUGES = 50
        self.PERTE_MAX_FRAMES  = 25
        self.N_LISSAGE         = 5

    def masque_rouge(self, bgr):
        """
        Masque binaire des pixels rouges de l'image entiere,
        nettoye par ouverture morphologique.
        """
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, self.ROUGE_BAS_1, self.ROUGE_HAUT_1)
        m2 = cv2.inRange(hsv, self.ROUGE_BAS_2, self.ROUGE_HAUT_2)
        masque = cv2.bitwise_or(m1, m2)
        noyau = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        return cv2.morphologyEx(masque, cv2.MORPH_OPEN, noyau)

    def centre_ligne(self, masque):
        """
        (x_centre, ecart_pct) sur la bande basse, ou (None, None).
        ecart_pct dans [-100, +100] : negatif = ligne a gauche du centre image.
        """
        bande = masque[self.BANDE_HAUT:self.BANDE_BAS, :]
        xs = np.where(bande > 0)[1]
        if xs.size < self.MIN_PIXELS_ROUGES:
            return None, None
        x_centre = int(np.median(xs))
        ecart_pct = (x_centre - self.LARGEUR / 2) / (self.LARGEUR / 2) * 100.0
        return x_centre, ecart_pct

    def pixels_rouges(self, masque):
        """
        (nb de pixels rouges du masque plein champ, y_max de ces pixels).
        y_max est l'ordonnee la plus basse a l'ecran (sol proche du robot) ;
        -1 si aucun pixel rouge.
        """
        ys = np.where(masque > 0)[0]
        if ys.size == 0:
            return 0, -1
        return int(ys.size), int(ys.max())

    def angle_direction(self, ecart_pct, dernier_ecart):
        """
        Angle CH0 par loi PD bornee avec zone morte :
        theta = theta0 + sat(+-DELTA_MAX)[SENS * (KP*e + KD*de)].
        Retourne (angle, ecart courant a memoriser).
        """
        if abs(ecart_pct) < self.SEUIL_DEADBAND:
            return self.CENTRE_DIRECTION, ecart_pct
        e  = ecart_pct / 100.0
        de = (ecart_pct - dernier_ecart) / 100.0
        correction = self.SENS_DIRECTION * (self.KP * e + self.KD * de)
        correction = max(-self.DELTA_MAX, min(self.DELTA_MAX, correction))
        return int(round(self.CENTRE_DIRECTION + correction)), ecart_pct

    def vitesse_en_virage(self, ecart_pct):
        """
        Vitesse reduite avec l'ecart : v = v0 * (1 - ALPHA * e).
        """
        e = min(1.0, abs(ecart_pct) / 100.0)
        return self.VITESSE_CROISIERE * (1 - self.ALPHA_VITESSE * e)

    def ouvrir_camera(self):
        """
        Ouvre picamera2 si disponible, sinon cv2.VideoCapture(0).
        """
        if _HAS_PICAM2:
            assert Picamera2 is not None
            cam = Picamera2()
            cfg = cam.create_preview_configuration(
                main={"size": (self.LARGEUR, self.HAUTEUR), "format": "RGB888"})
            cam.configure(cfg)
            cam.start()
            time.sleep(0.5)
            return cam
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.LARGEUR)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.HAUTEUR)
        return cap

    def lire_image(self, cam):
        """
        Retourne une frame BGR, ou None si la lecture echoue.
        """
        if _HAS_PICAM2:
            # picamera2 "RGB888"
            return cam.capture_array()
        ok, bgr = cam.read()
        return bgr if ok else None

    def fermer_camera(self, cam):
        """
        Fermeture de la camera.
        """
        if _HAS_PICAM2:
            cam.stop()
        else:
            cam.release()

    def main(self):
        """
        Boucle principale du suivi de ligne rouge.

        Logique: On isole les pixels rouges par seuillage HSV puis on calcule
        la médiane des colonnes rouges dans la bande basse de l'image. L'écart
        entre ce centre et le milieu du champ, lissé sur 5 frames, commande le
        servo de direction proportionnellement autour de l'angle roues droites.
        Le robot s'arrête quand le rouge a disparu du champ par le bas depuis
        0.5s (fin de ligne franchie), ou si la bande basse reste vide trop
        longtemps (ligne perdue).
        """
        servo  = ServoController()
        moteur = AdeeptMotorController(servo)
        cam    = self.ouvrir_camera()

        servo.setAngle(2, self.TILT_CAMERA, delay=0)
        servo.setAngle(1, self.CENTRE_COU, delay=0)
        servo.setAngle(0, self.CENTRE_DIRECTION, delay=0)

        dernier_ecart   = 0.0
        frames_perdues  = 0
        rouge_vu        = False    # latch : du rouge a ete apercu au moins une fois
        t_dernier_rouge = 0.0      # instant de derniere vue du rouge
        y_dernier_rouge = -1       # ordonnee max des derniers pixels rouges vus
        ecarts_recents  = deque(maxlen=self.N_LISSAGE)
        t0 = time.time()

        try:
            if self.MOTEUR_ACTIF:
                moteur.MotorRamp(moteur.DIR_FORWARD, self.VITESSE_CROISIERE, ramp_time=1.0)

            while True:
                bgr = self.lire_image(cam)
                if bgr is None:
                    continue
                if self.FLIP_HORIZONTAL:
                    bgr = cv2.flip(bgr, 1)

                t = time.time() - t0
                masque = self.masque_rouge(bgr)

                n_rouge, y_rouge = self.pixels_rouges(masque)
                if n_rouge > self.MIN_PIXELS_ROUGE_IMG:
                    rouge_vu = True
                    t_dernier_rouge = t
                    y_dernier_rouge = y_rouge
                elif (rouge_vu
                      and (t - t_dernier_rouge) >= self.DELAI_ARRET_APRES_ROUGE
                      and y_dernier_rouge >= self.SORTIE_BAS_Y):
                    if self.MOTEUR_ACTIF:
                        moteur.motorStop()
                    print(f"\n[FIN] Rouge sorti par le bas (y={y_dernier_rouge}) "
                          f"et hors champ depuis {t - t_dernier_rouge:.1f}s - arret.")
                    break

                x_centre, ecart = self.centre_ligne(masque)

                if x_centre is None:
                    frames_perdues += 1
                    if frames_perdues > self.PERTE_MAX_FRAMES:
                        if self.MOTEUR_ACTIF:
                            moteur.motorStop()
                        print("\n[LIGNE] Perdue durablement - arret de securite.")
                        break
                    if self.MOTEUR_ACTIF:
                        moteur.Motor(moteur.DIR_FORWARD, self.vitesse_en_virage(dernier_ecart))
                else:
                    frames_perdues = 0

                    ecarts_recents.append(ecart)
                    ecart_filtre = sum(ecarts_recents) / len(ecarts_recents)

                    angle, dernier_ecart = self.angle_direction(ecart_filtre, dernier_ecart)
                    servo.setAngle(0, angle, delay=0)
                    if self.MOTEUR_ACTIF:
                        moteur.Motor(moteur.DIR_FORWARD, self.vitesse_en_virage(ecart_filtre))

                    sens = "D" if angle < self.CENTRE_DIRECTION else ("G" if angle > self.CENTRE_DIRECTION else "-")
                    print(f"x={x_centre:3d}  ecart={ecart:+5.0f}%  "
                          f"angle={angle:3d}  braquage={sens}", end="\r")

                time.sleep(0.02)

        except KeyboardInterrupt:
            print("\n[SYS] Arret demande par l'utilisateur.")
        finally:
            moteur.destroy()
            self.fermer_camera(cam)
            print("Ressources liberees.")


if __name__ == "__main__":
    slr = SuiviLigneRouge()
    slr.main()