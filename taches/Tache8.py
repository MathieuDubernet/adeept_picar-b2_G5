#!/usr/bin/env python3
# File name : light_tracking.py
# Adeept PiCar-B2 - Lecture des 2 capteurs de lumière (ADS7830)

import time
import smbus

# ══════════════════════════════════════════════
#  CONSTANTES
# ══════════════════════════════════════════════

ADC_ADDRESS  = 0x48   # Adresse I2C du chip ADS7830
ADC_CMD      = 0x84

# Canaux ADC des capteurs sur le HAT V3.1
# X3 : Light Tracking → canal A1
LDR1_CHANNEL = 1      # Photorésistance gauche
LDR2_CHANNEL = 2      # Photorésistance droite  ← à ajuster si besoin

# Seuil pour considérer qu'une lumière est détectée (0-255)
LIGHT_THRESHOLD = 150


# ══════════════════════════════════════════════
#  CLASSE ADS7830
# ══════════════════════════════════════════════

class ADS7830(object):
    """Driver pour le convertisseur ADC 8 bits ADS7830."""

    def __init__(self):
        self.cmd     = ADC_CMD
        self.bus     = smbus.SMBus(1)
        self.address = ADC_ADDRESS

    def analogRead(self, chn):
        """
        Lit la valeur ADC sur un canal (0-7).
        Retourne une valeur entre 0 (obscurité) et 255 (lumière vive).
        """
        value = self.bus.read_byte_data(
            self.address,
            self.cmd | (((chn << 2 | chn >> 1) & 0x07) << 4)
        )
        return value


# ══════════════════════════════════════════════
#  FONCTIONS DE LECTURE
# ══════════════════════════════════════════════

def read_ldr1(adc):
    """Lit la valeur du capteur gauche (LDR1)."""
    return adc.analogRead(LDR1_CHANNEL)


def read_ldr2(adc):
    """Lit la valeur du capteur droit (LDR2)."""
    return adc.analogRead(LDR2_CHANNEL)


def read_both(adc):
    """
    Lit les 2 capteurs simultanément.
    Retourne (ldr1, ldr2).
    """
    return read_ldr1(adc), read_ldr2(adc)


def get_light_direction(ldr1, ldr2):
    """
    Analyse la différence entre les 2 capteurs.
    Retourne la direction de la source lumineuse :
      'GAUCHE'  → lumière à gauche  (LDR1 > LDR2)
      'DROITE'  → lumière à droite  (LDR2 > LDR1)
      'CENTRE'  → lumière centrée   (LDR1 ≈ LDR2)
      'OBSCUR'  → pas de lumière détectée
    """
    if ldr1 < LIGHT_THRESHOLD and ldr2 < LIGHT_THRESHOLD:
        return "OBSCUR"

    diff = ldr1 - ldr2

    if abs(diff) < 15:       # Tolérance ±15 pour considérer le centre
        return "CENTRE"
    elif diff > 0:
        return "GAUCHE"
    else:
        return "DROITE"


def print_bar(value, max_val=255, width=30):
    """Affiche une barre de progression ASCII pour visualiser la valeur."""
    filled = int(value / max_val * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {value:3d}"


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════

if __name__ == "__main__":
    adc = ADS7830()

    print("╔══════════════════════════════════════════╗")
    print("║    LECTURE CAPTEURS DE LUMIÈRE (x2)      ║")
    print("║    Ctrl+C pour quitter                   ║")
    print("╚══════════════════════════════════════════╝\n")

    try:
        while True:
            ldr1, ldr2 = read_both(adc)
            direction  = get_light_direction(ldr1, ldr2)

            print(f"LDR1 (gauche) : {print_bar(ldr1)}")
            print(f"LDR2 (droite) : {print_bar(ldr2)}")
            print(f"Direction     : {direction}")
            print(f"Différence    : {ldr1 - ldr2:+d}")
            print("-" * 48)

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nArrêt du programme.")