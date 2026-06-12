import time
import smbus

# ServoController n'est plus importé ici automatiquement pour éviter le conflit PCA9685.
# Il est injecté depuis l'extérieur via le paramètre 'controller'.

class ADS7830(object):
    """
    Lecture des 2 capteurs de lumière (LDR) via l'ADC ADS7830 (I2C, adresse 0x48).
    Canal 0 → LDR gauche
    Canal 1 → LDR droit

    CORRECTION : ServoController n'est plus créé en interne (conflit PCA9685).
    Passer une instance via le paramètre 'controller' si le suivi de roues est nécessaire.
    """

    def __init__(self, controller=None):
        self.cmd     = 0x84
        self.bus     = smbus.SMBus(1)
        self.address = 0x48
        # Contrôleur de servo optionnel (injecté depuis l'extérieur)
        self.controller = controller

    def analogRead(self, chn):
        """Lit la valeur ADC (0-255) du canal chn."""
        value = self.bus.read_byte_data(
            self.address,
            self.cmd | (((chn << 2 | chn >> 1) & 0x07) << 4)
        )
        return value

    def calculatePercentageLight(self, adc_value):
        """Convertit une valeur ADC (0-255) en pourcentage (0.0-100.0)."""
        return (adc_value / 255) * 100

    def read_ldr(self, chn):
        """Retourne la valeur brute (0-255) du LDR sur le canal chn."""
        return self.analogRead(chn)

    def turnWheelsToLight(self):
        """
        Oriente les roues vers la source lumineuse détectée sur le canal 1.
        Nécessite qu'un ServoController ait été injecté via __init__(controller=...).
        """
        if self.controller is None:
            raise RuntimeError(
                "Aucun ServoController fourni. "
                "Instancier ADS7830(controller=mon_servo_controller)."
            )
        adc_value  = self.analogRead(1)
        percentage = self.calculatePercentageLight(adc_value)

        # On ajoute 50 car l'angle centré est 140 et non 90
        value = (90 + 70) * (percentage / 100) + 50 + 10
        angle = 280 - int(round(value / 5) * 5)   # (90+50)*2

        self.controller.setAngle(0, angle)   # CH0 pour les roues
        return angle


# ── Fonctions utilitaires (utilisées par Tache7) ─────────────────────────────

def read_both(adc_instance):
    """
    Lit les deux LDR et retourne (ldr_gauche, ldr_droit) en valeurs brutes 0-255.
    Paramètre :
    - adc_instance : instance de ADS7830
    """
    ldr_left  = adc_instance.analogRead(0)
    ldr_right = adc_instance.analogRead(1)
    return ldr_left, ldr_right


def get_light_direction(ldr1, ldr2, seuil_obscurite=10, seuil_diff=15):
    """
    Détermine la direction de la source lumineuse à partir des deux valeurs LDR.

    Retourne :
    - "GAUCHE"  si la lumière vient de gauche (ldr1 > ldr2 + seuil_diff)
    - "DROITE"  si la lumière vient de droite (ldr2 > ldr1 + seuil_diff)
    - "CENTRE"  si les deux LDR sont proches
    - "OBSCUR"  si les deux LDR sont en dessous du seuil d'obscurité

    Paramètres :
    - ldr1             : valeur LDR gauche (0-255)
    - ldr2             : valeur LDR droit  (0-255)
    - seuil_obscurite  : valeur en dessous de laquelle on considère l'obscurité (défaut 10)
    - seuil_diff       : différence minimale pour décider d'un côté (défaut 15)
    """
    if ldr1 < seuil_obscurite and ldr2 < seuil_obscurite:
        return "OBSCUR"
    if ldr1 > ldr2 + seuil_diff:
        return "GAUCHE"
    if ldr2 > ldr1 + seuil_diff:
        return "DROITE"
    return "CENTRE"


# ── Programme autonome de test ────────────────────────────────────────────────
if __name__ == "__main__":
    # Test sans servo (lecture seule)
    adc = ADS7830()

    print("Lecture des capteurs de lumière (Ctrl+C pour arrêter)")
    print(f"{'LDR0 (gauche)':>16} | {'LDR1 (droit)':>12} | Direction")
    print("-" * 50)

    try:
        while True:
            ldr0, ldr1 = read_both(adc)
            direction  = get_light_direction(ldr0, ldr1)
            print(f"{ldr0:>16}  | {ldr1:>12}  | {direction}")
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\nArrêt.")
