 # Liste des commandes utiles

 ## Passer un fichier de l'ordinateur à la Rasp
 
 pscp "C:\Users\matdu\Desktop\Cours_ING1\Annee_1\MasterCamp\Test.txt" user@192.168.4.1:/home/user/

## Kill python running en background

sudo pkill -f python3

# ou plus ciblé :
sudo pkill -f 01_LED.py

# les configs qui changent en fonction du bot
control +maj+f "à changer selon le robot"