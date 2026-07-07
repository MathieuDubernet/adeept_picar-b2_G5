import time

import cv2
import numpy as np


class DetectionPanneaux:

    # Aire minimale d'un contour pour être considéré comme un panneau (en pixels²)
    AIRE_MIN = 500

    # Proportion minimale de pixels bleus dans la boîte englobante pour
    # valider un panneau tunnel (intérieur "principalement bleu")
    RATIO_BLEU_MIN = 0.45

    def __init__(self, index_camera=0, largeur=640, hauteur=480):
        """
        Initialise et démarre la webcam via cv2.VideoCapture.
        ACHTUNG: Le flux reste actif pendant toute la durée de vie de l'instance.
        """
        self.cap = cv2.VideoCapture(index_camera)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, largeur)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, hauteur)

        if not self.cap.isOpened():
            raise RuntimeError("Impossible d'ouvrir la caméra")

        time.sleep(1.0)

    def _creer_masques(self, hsv):
        """
        Crée les masques de couleur :
        - rouge : pour le BORD du panneau de chantier (triangle)
        - bleu  : pour le REMPLISSAGE du panneau tunnel (carré)
        Ajuste ces plages selon la couleur réelle de tes panneaux (voir note plus bas).
        """
        # Le rouge est à cheval sur 0° et 180° en HSV -> deux plages
        rouge_bas1 = np.array([0, 100, 80])
        rouge_haut1 = np.array([10, 255, 255])
        rouge_bas2 = np.array([170, 100, 80])
        rouge_haut2 = np.array([180, 255, 255])
        masque_rouge = cv2.bitwise_or(
            cv2.inRange(hsv, rouge_bas1, rouge_haut1),
            cv2.inRange(hsv, rouge_bas2, rouge_haut2),
        )

        bleu_bas = np.array([90, 10, 40])
        bleu_haut = np.array([150, 90, 200])
        masque_bleu = cv2.inRange(hsv, bleu_bas, bleu_haut)

        # Nettoyage morphologique (enlève le bruit, comble les petits trous)
        noyau = np.ones((5, 5), np.uint8)
        masque_rouge = cv2.morphologyEx(masque_rouge, cv2.MORPH_OPEN, noyau)
        masque_rouge = cv2.morphologyEx(masque_rouge, cv2.MORPH_CLOSE, noyau)
        masque_bleu = cv2.morphologyEx(masque_bleu, cv2.MORPH_OPEN, noyau)
        masque_bleu = cv2.morphologyEx(masque_bleu, cv2.MORPH_CLOSE, noyau)

        return masque_rouge, masque_bleu

    def _est_triangle(self, contour):
        """
        Vérifie si le contour (bord rouge du panneau de chantier) approxime
        un triangle à 3 sommets.
        """
        perimetre = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * perimetre, True)
        return len(approx) == 3, approx

    def _est_carre_bleu(self, contour, masque_bleu):
        """
        Vérifie si le contour (remplissage bleu du panneau tunnel) approxime
        un carré à 4 sommets ET que le bleu couvre bien la majorité de la
        boîte englobante (panneau "principalement bleu", pas juste un bord bleu).
        """
        perimetre = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * perimetre, True)

        if len(approx) != 4 or not cv2.isContourConvex(approx):
            return False, approx

        x, y, w, h = cv2.boundingRect(approx)
        ratio_forme = w / float(h)
        if not (0.85 <= ratio_forme <= 1.15):
            return False, approx
        
        # Vérifie la proportion de pixels bleus dans la zone détectée
        roi = masque_bleu[y:y + h, x:x + w]
        if roi.size == 0:
            return False, approx
        ratio_bleu = cv2.countNonZero(roi) / float(roi.size)
        if ratio_bleu < self.RATIO_BLEU_MIN:
            return False, approx

        return True, approx

    def _detecter_triangles_rouges(self, masque_rouge, frame_dessin):
        """Cherche les panneaux de chantier (triangle à bord rouge)."""
        detections = []
        contours, _ = cv2.findContours(
            masque_rouge, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        for c in contours:
            aire = cv2.contourArea(c)
            if aire < self.AIRE_MIN:
                continue

            ok, approx = self._est_triangle(c)
            if not ok:
                continue

            x, y, w, h = cv2.boundingRect(c)
            detections.append({
                "forme": "panneau_chantier",
                "bbox": (x, y, w, h),
                "aire": aire,
                "centre": (x + w // 2, y + h // 2),
            })

            cv2.rectangle(frame_dessin, (int(x), int(y)), (int(x + w), int(y + h)), (0, 0, 255), 2)
            cv2.putText(
                frame_dessin, "chantier", (int(x), int(y) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2,
            )

        return detections

    def _detecter_carres_bleus(self, masque_bleu, frame_dessin):
        """Cherche les panneaux tunnel (carré à intérieur majoritairement bleu)."""
        detections = []
        contours, _ = cv2.findContours(
            masque_bleu, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # --- DEBUG temporaire ---
        #print(f"[DEBUG] {len(contours)} contour(s) trouvé(s) dans le masque bleu")

        for c in contours:
            aire = cv2.contourArea(c)
            if aire < self.AIRE_MIN:
                #print(f"[DEBUG] contour ignoré : aire trop petite ({aire:.0f} < {self.AIRE_MIN})")
                continue

            perimetre = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * perimetre, True)
            x, y, w, h = cv2.boundingRect(c)
            ratio_forme = w / float(h)

            roi = masque_bleu[y:y + h, x:x + w]
            ratio_bleu = cv2.countNonZero(roi) / float(roi.size) if roi.size else 0

            #print(
            #    f"[DEBUG] aire={aire:.0f} sommets={len(approx)} "
            #    f"ratio_forme={ratio_forme:.2f} ratio_bleu={ratio_bleu:.2f} "
            #    f"convexe={cv2.isContourConvex(approx)}"
            #)
            # --- FIN DEBUG ---

            ok, approx = self._est_carre_bleu(c, masque_bleu)
            if not ok:
                continue

            detections.append({
                "forme": "panneau_tunnel",
                "bbox": (x, y, w, h),
                "aire": aire,
                "centre": (x + w // 2, y + h // 2),
            })

            cv2.rectangle(frame_dessin, (int(x), int(y)), (int(x + w), int(y + h)), (255, 0, 0), 2)
            cv2.putText(
                frame_dessin, "tunnel", (int(x), int(y) - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2,
            )

        return detections

    def detecter_panneau(self):
        """
        Capture une image et retourne la liste des panneaux détectés,
        chacun sous forme de dict {forme, bbox, aire, centre}.
        Retourne une liste vide si rien n'est détecté (ou si la capture échoue).
        """
        ok, frame = self.cap.read()
        if not ok or frame is None:
            return []

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)  # VideoCapture -> BGR par défaut
        masque_rouge, masque_bleu = self._creer_masques(hsv)

        detections = []
        detections += self._detecter_triangles_rouges(masque_rouge, frame)
        detections += self._detecter_carres_bleus(masque_bleu, frame)

        cv2.imshow("Detection panneaux", frame)
        cv2.waitKey(1)

        return detections

    def liberer(self):
        """Arrêt propre : libère la caméra et ferme les fenêtres."""
        self.cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    detection = DetectionPanneaux()
    try:
        while True:
            panneaux = detection.detecter_panneau()
            for p in panneaux:
                print(f"Panneau détecté : {p['forme']} à {p['centre']} (aire={p['aire']:.0f})")
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        detection.liberer()