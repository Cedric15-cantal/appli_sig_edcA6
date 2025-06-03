# Guide d'installation Flask - Environnement Virtuel

```bash
# 1. Mise à jour du système (prérequis)
sudo apt update && sudo apt upgrade -y
# - 'update' rafraîchit la liste des paquets
# - 'upgrade' installe les mises à jour
# - '-y' répond automatiquement 'oui' aux confirmations

# 2. Installation des outils Python
sudo apt install python3 python3-pip python3-venv -y
# - Installe Python 3, pip et le module venv en une commande

# 3. Configuration du projet
mkdir -p ~/mon_projet_flask && cd ~/mon_projet_flask
# - Crée un dossier dédié et s'y déplace
# - À adapter selon votre structure existante

# 4. Copie des fichiers essentiels
# Coller ici vos fichiers (app.py, index.html, etc.)

# 5. Création de l'environnement virtuel
python3 -m venv /chemin/vers/votre/projet/mon_env  # "mon_env" est le nom de votre environnement
# - 'venv' est le nom conventionnel recommandé
# - Le chemin est relatif au dossier courant

# 6. Activation de l'environnement
source /chemin/vers/votre/projet/mon_env/bin/activate  # Linux/Mac/WSL
# Sur Windows natif : venv\Scripts\activate
# Le prompt devrait montrer '(venv)' quand actif

# 7. Installation des dépendances
pip install flask python-dotenv pyjwt requests
# - flask inclut déjà werkzeug


# 8. Lancement de l'application en local
python3 app.py


# OU
# 8. Lancement du serveur de développement
export FLASK_APP=app.py  # Définit le point d'entrée
export FLASK_ENV=development  # Mode développement
flask run --host=0.0.0.0 --port=5000
# Alternative : python3 app.py

# 9. Désactivation propre
deactivate
# Important pour éviter les conflits entre projets



# A FAIRE ... !
/mon_projet_flask
├── venv/               # Environnement virtuel
├── app.py              # Point d'entrée principal
├── requirements.txt    # Liste des dépendances
├── /static            # Fichiers statiques (CSS, JS)
└── /templates         # Fichiers HTML/Jinja2