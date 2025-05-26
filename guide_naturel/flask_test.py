from flask import Flask, render_template, jsonify, redirect, url_for, request
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from API_request.mongo_request import *

app = Flask(__name__)

# Configuration MongoDB (comme avant)
MONGO_URI = "mongodb+srv://guest:guestpass@big-data.640be.mongodb.net/?retryWrites=true&w=majority&appName=Big-Data"
DB_NAME = 'LeGuideNaturel'
COLLECTION_NAME = 'Nature'

mongo_client_instance = None
collection_instance = None

try:
    collection_instance = get_mongo_collection(MONGO_URI, DB_NAME, COLLECTION_NAME)
    mongo_client_instance = collection_instance.database.client
    print("MongoDB client initialized for Flask app.")
except Exception as e:
    print(f"Failed to initialize MongoDB client for Flask app: {e}")


# --- Routes Flask ---
@app.route('/')
def index():
    return redirect(url_for('main_page'))


@app.route('/main_page')
def main_page():

    initial_info = request.args.get('info', 'default')

    return render_template(
        'index.html',
        initial_info=initial_info  # Passons toutes les données préparées
    )


@app.route('/search.html')
def search():
    return render_template('recherche.html')


@app.route('/about.html')
def about():
    return render_template('apropos.html')


@app.route('/get_chart_data')
def get_chart_data():
    info_key = request.args.get('info')

    if info_key == "especesParRegne":
        data = [species_by_regne(col=collection_instance)]
    elif info_key == "statutsConservation":
        data = species_by_regne_and_statut_global(col=collection_instance)
    else:
        data = [species_by_code_statut(col=collection_instance)]

    return data


@app.route('/header.html')
def get_header_html_fragment():
    return render_template('header.html')


@app.route('/footer.html')
def get_footer_html_fragment():
    return render_template('footer.html')


if __name__ == '__main__':
    # Ne pas exécuter app.run() si l'initialisation a échoué gravement
    if collection_instance is not None:
        app.run(debug=True)
    else:
        print("L'application Flask n'a pas pu démarrer en raison d'un problème de connexion à MongoDB.")
