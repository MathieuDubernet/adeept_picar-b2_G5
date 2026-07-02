import time

import cv2
from picamera2 import Picamera2


class AnalyseImage:

    def __init__(self):
        """
        Initialise et démarre la caméra via Picamera2.
        ACHTUNG: Le flux reste actif pendant toute la durée de vie de l'instance.
        """
        self.picam = Picamera2()
        config = self.picam.create_preview_configuration(
            main={"format": "RGB888", "size": (640, 480)}
        )
        self.picam.configure(config)
        self.picam.start()

        time.sleep(1.0)

    def Direction(self):
        """
        Analyse une seule frame du flux caméra et détermine si une flèche
        y est présente, ainsi que son orientation horizontale.

        Logique: On applique un filtre gris, un flou gaussien et un filtre d'inversion binaire pour faciliter la détection des contours.
        Si l'aire des contours forment une flèche (7 sommets + non convexe), on détermine la direction de la flèche à partir du centre de masse de la forme.
        La distance de la pointe de la flèche par rapport à la base permet de connaître la direction.

        """
        frame = self.picam.capture_array()
        if frame is None:
            return None

        image_grise = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        image_floue = cv2.GaussianBlur(image_grise, (5, 5), 0)
        _, image_binaire = cv2.threshold(
            image_floue, 0, 255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        contours, _ = cv2.findContours(
            image_binaire, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        aire_image = frame.shape[0] * frame.shape[1]
        for cnt in contours:
            aire = cv2.contourArea(cnt)
            if aire < 5000 or aire > 0.5 * aire_image:
                continue

            perimetre = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * perimetre, True)

            if len(approx) != 7 or cv2.isContourConvex(approx):
                continue

            xs = approx.reshape(-1, 2)[:, 0]
            x_max = int(xs.max())
            x_min = int(xs.min())

            moments = cv2.moments(cnt)
            if moments["m00"] == 0:
                continue

            centroide_x = int(moments["m10"] / moments["m00"])
            dist_droite = x_max - centroide_x
            dist_gauche = centroide_x - x_min

            if dist_droite > dist_gauche:
                return "droite"
            elif dist_droite < dist_gauche:
                return "gauche"
            return None  

        return None

    def liberer(self):
        """Arrêt propre : stoppe puis ferme le flux caméra."""
        self.picam.stop()
        self.picam.close()


if __name__ == "__main__":
    analyseur = AnalyseImage()
    try:
        while True:
            direction = analyseur.Direction()
            if direction is not None:
                print("Fleche :", direction)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("Arret.")
    finally:
        analyseur.liberer()