#!/usr/bin/env python
# File name : led_control.py
# Adeept PiCar-B2 - Contrôle des LEDs

from gpiozero import PWMOutputDevice as PWM
from gpiozero import LED
import time

# ─── GPIO des LEDs RGB (feux avant - logique inversée) ───
Left_R  = 19
Left_G  = 0
Left_B  = 13
Right_R = 1
Right_G = 5
Right_B = 6

# ─── GPIO des 3 LEDs simples ───
LED1_PIN = 9
LED2_PIN = 25
LED3_PIN = 11

# ─── Palette de couleurs ───
colors = [0xFF0000, 0x00FF00, 0x0000FF, 0xFFFF00,
          0xFF00FF, 0x00FFFF, 0x6F00D2, 0xFF5809]

# ─── Variables globales ───
L_R = L_G = L_B = None
R_R = R_G = R_B = None
led1 = led2 = led3 = None


# ══════════════════════════════════════════════
#  SETUP
# ══════════════════════════════════════════════

def setup():
    global L_R, L_G, L_B, R_R, R_G, R_B
    global led1, led2, led3

    # LEDs RGB PWM (initial_value=1.0 = éteint car logique inversée)
    L_R = PWM(pin=Left_R,  initial_value=1.0, frequency=2000)
    L_G = PWM(pin=Left_G,  initial_value=1.0, frequency=2000)
    L_B = PWM(pin=Left_B,  initial_value=1.0, frequency=2000)
    R_R = PWM(pin=Right_R, initial_value=1.0, frequency=2000)
    R_G = PWM(pin=Right_G, initial_value=1.0, frequency=2000)
    R_B = PWM(pin=Right_B, initial_value=1.0, frequency=2000)

    # LEDs simples ON/OFF
    led1 = LED(LED1_PIN)
    led2 = LED(LED2_PIN)
    led3 = LED(LED3_PIN)


# ══════════════════════════════════════════════
#  UTILITAIRES
# ══════════════════════════════════════════════

def map_val(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


# ══════════════════════════════════════════════
#  CONTRÔLE COULEUR (LEDs RGB)
# ══════════════════════════════════════════════

def setAllColor(col):
    """Applique une couleur hex (ex: 0xFF0000) aux 6 LEDs RGB."""
    R_val = map_val((col & 0xFF0000) >> 16, 0, 255, 0, 1.0)
    G_val = map_val((col & 0x00FF00) >> 8,  0, 255, 0, 1.0)
    B_val = map_val((col & 0x0000FF),        0, 255, 0, 1.0)

    L_R.value = 1.0 - R_val
    L_G.value = 1.0 - G_val
    L_B.value = 1.0 - B_val
    R_R.value = 1.0 - R_val
    R_G.value = 1.0 - G_val
    R_B.value = 1.0 - B_val


def setAllRGBColor(R, G, B):
    """Applique une couleur RGB (0-255) aux 6 LEDs RGB."""
    R_val = map_val(R, 0, 255, 0, 1.0)
    G_val = map_val(G, 0, 255, 0, 1.0)
    B_val = map_val(B, 0, 255, 0, 1.0)

    L_R.value = 1.0 - R_val
    L_G.value = 1.0 - G_val
    L_B.value = 1.0 - B_val
    R_R.value = 1.0 - R_val
    R_G.value = 1.0 - G_val
    R_B.value = 1.0 - B_val


# ══════════════════════════════════════════════
#  CONTRÔLE INDIVIDUEL ON/OFF (toutes les 9 LEDs)
# ══════════════════════════════════════════════

def set_led(num, state):
    """
    Pilote individuellement chaque LED.
    num   : 1 à 9
    state : True/1 = allumer, False/0 = éteindre

    Mapping :
      1 → LED1 (simple)
      2 → LED2 (simple)
      3 → LED3 (simple)
      4 → Left_R  (RGB PWM, logique inversée)
      5 → Left_G
      6 → Left_B
      7 → Right_R
      8 → Right_G
      9 → Right_B
    """
    # LEDs simples (logique directe)
    if num == 1:
        led1.on()  if state else led1.off()
    elif num == 2:
        led2.on()  if state else led2.off()
    elif num == 3:
        led3.on()  if state else led3.off()

    # LEDs RGB PWM (logique INVERSÉE : 0.0 = allumé, 1.0 = éteint)
    elif num == 4:
        L_R.value = 0.0 if state else 1.0
    elif num == 5:
        L_G.value = 0.0 if state else 1.0
    elif num == 6:
        L_B.value = 0.0 if state else 1.0
    elif num == 7:
        R_R.value = 0.0 if state else 1.0
    elif num == 8:
        R_G.value = 0.0 if state else 1.0
    elif num == 9:
        R_B.value = 0.0 if state else 1.0
    else:
        print(f"Numéro de LED invalide : {num} (attendu : 1 à 9)")


def all_off():
    """Éteint toutes les LEDs."""
    for i in range(1, 10):
        set_led(i, False)


# ══════════════════════════════════════════════
#  DEMO COULEURS (boucle arc-en-ciel)
# ══════════════════════════════════════════════

def loop():
    while True:
        for col in colors:
            setAllColor(col)
            time.sleep(0.5)


# ══════════════════════════════════════════════
#  DESTROY
# ══════════════════════════════════════════════

def destroy():
    all_off()
    L_R.close(); L_G.close(); L_B.close()
    R_R.close(); R_G.close(); R_B.close()
    led1.close(); led2.close(); led3.close()
    print("GPIO libérés.")


# ══════════════════════════════════════════════
#  MAIN — Contrôle manuel via input()
# ══════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════╗")
    print("║     Contrôle manuel des LEDs         ║")
    print("╠══════════════════════════════════════╣")
    print("║  11-19 → Allumer LED 1 à 9           ║")
    print("║  21-29 → Éteindre LED 1 à 9          ║")
    print("║  00    → Tout éteindre               ║")
    print("║  99    → Quitter                     ║")
    print("╚══════════════════════════════════════╝")

    while True:
        try:
            cmd = input("\nCommande : ").strip()

            if cmd == "99":
                print("Arrêt du programme.")
                break

            if cmd == "00":
                all_off()
                print("Toutes les LEDs éteintes.")
                continue

            code = int(cmd)
            action = code // 10   # 1 = allumer, 2 = éteindre
            num    = code % 10    # numéro de LED (1-9)

            if num < 1 or num > 9:
                print("Numéro LED invalide (1-9).")
                continue

            if action == 1:
                set_led(num, True)
                print(f"LED{num} allumée.")
            elif action == 2:
                set_led(num, False)
                print(f"LED{num} éteinte.")
            else:
                print("Commande invalide. Exemples : 11, 19, 21, 29")

        except ValueError:
            print("Entrée invalide, tapez un nombre (ex: 11, 23).")
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    setup()
    try:
        main()
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        destroy()