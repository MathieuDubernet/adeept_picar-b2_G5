import cv2
import numpy as np


image = cv2.imread("../images/fleche_img.png")

if image is None :
    print("Erreur : image introuvable, vérifiez le chemin.")
    exit()
cv2.imshow("yeeeh",image)
height, width = image.shape[:2]
print(width)
print(height)
cv2.waitKey(7000)

# Resize l'image
image_reduite = cv2.resize(image,(800,600))
cv2.imshow("oiii",image_reduite)
cv2.imwrite("../images/ligne_rouge_img_redim.jpg", image_reduite)
cv2.waitKey(2000)

# Convertit l'image en gris
image_grise= cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
cv2.imwrite("../images/ligne_rouge_img_gris.jpg", image_grise)
cv2.imshow("oiii",image_grise)
cv2.waitKey(2000)

# Convertit l'image en noir et blanc binaire 
(_, image_nb) = cv2.threshold(image_grise, 100, 255, cv2.THRESH_BINARY)
cv2.imshow("test",image_nb)
cv2.waitKey(2000)

# Isole l'image en rouge  
image_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
cv2.imshow("wsh",image_hsv)
cv2.waitKey(2000)

# on cherche à metre en évidence le rouge en le mettant en blanc sur fond noir (filtre binaire en gros)
image_mask =  cv2.inRange(image_hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
image_mask2 = cv2.inRange(image_hsv, np.array([170, 100, 100]), np.array([179, 255, 255]))
masque_jsp = cv2.bitwise_or(image_mask, image_mask2)
cv2.imshow("masque", image_mask)
cv2.waitKey(2000)
cv2.imshow("masque2", image_mask2)
cv2.waitKey(2000)
cv2.imshow("Combinaison masque", masque_jsp)
cv2.waitKey(2000)

points = []
for x in range(width):
    ys = np.where(masque_jsp[:, x] > 0)[0]
    if len(ys) > 0:
        cy = int(np.mean(ys))   
        points.append((x, cy))  
for i in range(1, len(points)):
           image = cv2.line(image, points[i-1], points[i], (0, 255, 0), 2)
cv2.imshow("Ligne centrale", image)
cv2.waitKey(2000)



image_grise = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
# on le floute
image_grise_blur = cv2.GaussianBlur(image_grise, (5,5),0)
coins = cv2.goodFeaturesToTrack(image_grise_blur, maxCorners=20, qualityLevel=0.1, minDistance=30)


for c in coins:
    x, y = c.ravel()  
    x, y = int(x), int(y)
    points.append((x, y))
    cv2.circle(image, (x, y), 5, (0, 255, 0), -1)
cv2.imshow("coins", image)
cv2.waitKey(2000)
cv2.destroyAllWindows()