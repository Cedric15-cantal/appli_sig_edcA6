# app.py
from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
import requests
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Initialisation de l'application Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
ORS_API_KEY = os.getenv('ORS_API_KEY')
ORS_API_URL = 'https://api.openrouteservice.org/v2/directions'

# Fonction pour établir une connexion à la base de données SQLite
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    # Activation du mode WAL pour une meilleure gestion des accès concurrents
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=5000')  # Timeout de 5 secondes
    return conn

# Initialisation de la base de données si elle n'existe pas
def init_db():
    if not os.path.exists('users.db'):
        conn = get_db_connection()
        try:
            conn.execute('''CREATE TABLE users
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          username TEXT UNIQUE NOT NULL,
                          email TEXT UNIQUE NOT NULL,
                          password TEXT NOT NULL,
                          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            conn.commit()
        finally:
            conn.close()

init_db()

# Décorateur pour vérifier la présence et la validité d'un token JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Extraction du token depuis les en-têtes de la requête
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
            
        if not token:
            return jsonify({'message': 'Token manquant !'}), 401
            
        try:
            # Décodage et vérification du token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            conn = get_db_connection()
            try:
                current_user = conn.execute('SELECT * FROM users WHERE id = ?', (data['user_id'],)).fetchone()
                
                if current_user is None:
                    return jsonify({'message': 'Utilisateur non trouvé !'}), 401
                    
                return f(current_user, *args, **kwargs)
            finally:
                conn.close()
                
        except Exception as e:
            return jsonify({'message': 'Token invalide !', 'error': str(e)}), 401
            
    return decorated

# Route pour servir la page d'accueil
@app.route('/')
def serve_index():
    return send_from_directory(os.path.dirname(__file__), 'index.html')

# Route pour servir les fichiers statiques
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(os.path.dirname(__file__), path)

# Route pour l'inscription d'un nouvel utilisateur
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Vérification que tous les champs sont remplis
    if not username or not email or not password:
        return jsonify({'message': 'Tous les champs sont requis'}), 400

    # Hachage du mot de passe
    hashed_password = generate_password_hash(password)
    conn = None

    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                     (username, email, hashed_password))
        conn.commit()
        return jsonify({'message': 'Utilisateur créé avec succès'}), 201
    except sqlite3.IntegrityError as e:
        # Gestion des erreurs d'intégrité (username/email déjà existant)
        error_msg = str(e)
        if 'username' in error_msg:
            return jsonify({'message': 'Nom d\'utilisateur déjà utilisé'}), 400
        elif 'email' in error_msg:
            return jsonify({'message': 'Email déjà utilisé'}), 400
        else:
            return jsonify({'message': 'Erreur lors de la création du compte'}), 400
    except sqlite3.OperationalError as e:
        # Gestion des erreurs de verrouillage de la base de données avec mécanisme de retry
        if "database is locked" in str(e):
            try:
                if conn:
                    conn.close()
                conn = get_db_connection()
                conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                             (username, email, hashed_password))
                conn.commit()
                return jsonify({'message': 'Utilisateur créé avec succès'}), 201
            except Exception as retry_error:
                return jsonify({'message': 'Erreur lors de la création du compte', 'error': str(retry_error)}), 500
        return jsonify({'message': 'Erreur de base de données', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

# Route pour la connexion d'un utilisateur
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Nom d\'utilisateur et mot de passe requis'}), 400

    conn = None
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user is None:
            return jsonify({'message': 'Nom d\'utilisateur incorrect'}), 401

        # Vérification du mot de passe haché
        if check_password_hash(user['password'], password):
            # Génération d'un token JWT valide 1 heure
            token = jwt.encode({
                'user_id': user['id'],
                'username': user['username'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            }, app.config['SECRET_KEY'], algorithm='HS256')

            return jsonify({
                'message': 'Connexion réussie',
                'token': token,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email']
                }
            }), 200
        else:
            return jsonify({'message': 'Mot de passe incorrect'}), 401
    except Exception as e:
        return jsonify({'message': 'Erreur lors de la connexion', 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

# Route pour la déconnexion (nécessite un token valide)
@app.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    return jsonify({'message': 'Déconnexion réussie'}), 200

# Route pour obtenir les informations de l'utilisateur connecté
@app.route('/user', methods=['GET'])
@token_required
def get_user(current_user):
    return jsonify({
        'id': current_user['id'],
        'username': current_user['username'],
        'email': current_user['email']
    }), 200

# Route pour mettre à jour les informations de l'utilisateur
@app.route('/user/update', methods=['PUT'])
@token_required
def update_user(current_user):
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    conn = None
    try:
        conn = get_db_connection()
        
        updates = []
        params = []
        
        # Construction dynamique de la requête SQL en fonction des champs à mettre à jour
        if username and username != current_user['username']:
            updates.append("username = ?")
            params.append(username)
            
        if email and email != current_user['email']:
            updates.append("email = ?")
            params.append(email)
            
        if password:
            hashed_password = generate_password_hash(password)
            updates.append("password = ?")
            params.append(hashed_password)
            
        if not updates:
            return jsonify({'message': 'Aucune modification effectuée'}), 200
            
        query = "UPDATE users SET " + ", ".join(updates) + " WHERE id = ?"
        params.append(current_user['id'])
        
        try:
            conn.execute(query, params)
            conn.commit()
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                # Retry en cas de verrouillage de la base
                conn.execute(query, params)
                conn.commit()
            else:
                raise
        
        # Récupération de l'utilisateur mis à jour
        updated_user = conn.execute('SELECT * FROM users WHERE id = ?', (current_user['id'],)).fetchone()
        
        # Génération d'un nouveau token si le username a changé
        token = None
        if username and username != current_user['username']:
            token = jwt.encode({
                'user_id': updated_user['id'],
                'username': updated_user['username'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'message': 'Profil mis à jour avec succès',
            'user': {
                'id': updated_user['id'],
                'username': updated_user['username'],
                'email': updated_user['email']
            },
            'token': token
        }), 200
        
    except sqlite3.IntegrityError as e:
        # Gestion des erreurs d'intégrité
        error_msg = str(e)
        if 'username' in error_msg:
            return jsonify({'message': 'Nom d\'utilisateur déjà utilisé'}), 400
        elif 'email' in error_msg:
            return jsonify({'message': 'Email déjà utilisé'}), 400
        else:
            return jsonify({'message': 'Erreur lors de la mise à jour du profil'}), 400
    except Exception as e:
        return jsonify({'message': 'Erreur lors de la mise à jour du profil', 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

# Route pour la recherche d'adresses via l'API data.gouv.fr
@app.route('/api/search', methods=['GET'])
def search_address():
    query = request.args.get('q', '')
    if len(query) < 3:
        return jsonify([])
    
    try:
        response = requests.get(
            f'https://api-adresse.data.gouv.fr/search/?q={query}&limit=6'
        )
        response.raise_for_status()
        return jsonify(response.json().get('features', []))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route pour le calcul d'itinéraire via l'API OpenRouteService
@app.route('/api/route', methods=['GET'])
@token_required
def calculate_route(current_user):
    start = request.args.get('start')
    end = request.args.get('end')
    mode = request.args.get('mode', 'driving-car')
    
    if not start or not end:
        return jsonify({'error': 'Les points de départ et d\'arrivée sont requis'}), 400
    
    try:
        # Conversion des coordonnées depuis le format "lon,lat"
        start_coords = list(map(float, start.split(',')))
        end_coords = list(map(float, end.split(',')))
        
        # Appel à l'API OpenRouteService
        response = requests.get(
            f'{ORS_API_URL}/{mode}',
            params={
                'api_key': ORS_API_KEY,
                'start': f"{start_coords[0]},{start_coords[1]}",
                'end': f"{end_coords[0]},{end_coords[1]}",
                'language': 'fr'
            }
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Vérification de la présence des données de route
        if not data.get('features') or len(data['features']) == 0:
            return jsonify({'error': 'Aucun itinéraire trouvé entre ces points'}), 404
            
        if not data['features'][0].get('properties', {}).get('segments'):
            return jsonify({'error': 'L\'itinéraire ne contient pas de segments'}), 404
            
        return jsonify(data)
    except requests.exceptions.HTTPError as e:
        return jsonify({'error': f'Erreur du service de routage: {str(e)}'}), 502
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, threaded=True)