@echo off
setlocal enabledelayedexpansion

REM ===== CONFIGURATION - a adapter =====
set "MDP=password"
set "BASE=C:\Users\matdu\Desktop\Cours_ING1\Annee_1\MasterCamp\adeept_picar-b2_G5\taches"
set "DEST=user@172.20.10.2:/home/user/Code"
set "NB_TACHES=11"
REM ======================================

for /L %%i in (1,1,%NB_TACHES%) do (
    echo.
    echo === Envoi de Tache%%i.py ===
    pscp -pw %MDP% "%BASE%\Tache%%i.py" %DEST%
    if errorlevel 1 (
        echo [ERREUR] Echec de l'envoi de Tache%%i.py
    ) else (
        echo [OK] Tache%%i.py envoye avec succes
    )
)

echo.
echo === Envoi de AnalyseFleche.py ===
pscp -pw %MDP% "%BASE%\AnalyseFleche.py" %DEST%
if errorlevel 1 (
    echo [ERREUR] Echec de l'envoi de AnalyseFleche.py
) else (
    echo [OK] AnalyseFleche.py envoye avec succes
)

echo.
echo === Envoi de Labyrinthe.py ===
pscp -pw %MDP% "%BASE%\Labyrinthe.py" %DEST%
if errorlevel 1 (
    echo [ERREUR] Echec de l'envoi de Labyrinthe.py
) else (
    echo [OK] Labyrinthe.py envoye avec succes
)

echo.
echo Tous les envois sont termines.
pause
