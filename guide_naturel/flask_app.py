from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_cors import CORS
import uuid
from thefuzz import process, fuzz
from API_request.mongo_request import *
from API_request.recherche import *
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
CORS(app)

# *** CONFIGURATION ***
MONGO_APP_USER = os.getenv("MONGO_APP_USER")
MONGO_APP_PASSWORD = os.getenv("MONGO_APP_PASSWORD")
MONGO_CLUSTER = os.getenv("MONGO_CLUSTER_URL")
DB_NAME = os.getenv("DB_NAME", "LeGuideNaturel")

COLLECTION_NAME = "Nature"
LOG_COMPLETED_SEARCHES_COLLECTION = "completed_searches"
LOG_QUESTION_INTERACTIONS_COLLECTION = "question_interactions"

if not all([MONGO_APP_USER, MONGO_APP_PASSWORD, MONGO_CLUSTER]):
    print("ERREUR CRITIQUE: Des variables d'environnement MongoDB sont manquantes")
    print("L'application ne pourra pas se connecter à la base de données")
    MONGO_URI = None
else:
    MONGO_URI = f"mongodb+srv://{MONGO_APP_USER}:{MONGO_APP_PASSWORD}@{MONGO_CLUSTER}/?retryWrites=true&w=majority&appName=Big-Data"

# *** INITIALISATION MONGODB ***
mongo_client_instance = None
collection_instance = None
completed_searches_log_col = None
question_interactions_log_col = None

# Tenter la connexion seulement si l'URI a pu être construite
if MONGO_URI:
    try:
        temp_collection_instance = get_mongo_collection(MONGO_URI, DB_NAME, COLLECTION_NAME)
        if temp_collection_instance is not None:
            collection_instance = temp_collection_instance
            db_instance = collection_instance.database
            mongo_client_instance = db_instance.client

            completed_searches_log_col = db_instance[LOG_COMPLETED_SEARCHES_COLLECTION]
            question_interactions_log_col = db_instance[LOG_QUESTION_INTERACTIONS_COLLECTION]

            print("MongoDB client and collections initialized for Flask app")
        else:
            print(f"Failed to get MongoDB collection instance using URI: {MONGO_URI} and DB: {DB_NAME}")
    except Exception as e:
        print(f"Failed to initialize MongoDB client for Flask app: {e}")
        print(f"Mongo URI used: {MONGO_URI}")
else:
    print("MongoDB URI n'a pas pu être construite en raison de variables d'environnement manquantes.")


departements_a_analyser = [21, 25, 39, 58, 70, 71, 89, 90]


# *** STOCKAGE EN MÉMOIRE DES CONVERSATIONS ***
conversations = {}


# *** ROUTES FLASK ***
@app.route('/')
def index():
    return redirect(url_for('guide_naturel'))


@app.route('/guide_naturel')
def guide_naturel():
    initial_info = request.args.get('info', 'default')
    return render_template('index.html', initial_info=initial_info)


@app.route('/recherche')
def recherche():
    return render_template('recherche.html')


@app.route('/apropos')
def apropos():
    return render_template('apropos.html')


# Route pour récupérer les informations des graphiques
@app.route('/get_chart_data')
def get_chart_data():
    info_key = request.args.get('info')

    if info_key == "especesParRegne":
        data = [species_by_regne(col=collection_instance)]
    elif info_key == "especesParRegne_dep":
        data = species_by_regne_dep(col=collection_instance, departements=departements_a_analyser)
    elif info_key == "especesParStatutConservation":
        data = [species_by_code_statut(col=collection_instance)]
    elif info_key == "especesParStatutConservation_dep":
        data = species_by_code_statut_dep(col=collection_instance, departements=departements_a_analyser)
    elif info_key == "statutsConservationParRegne":
        data = species_by_regne_and_statut(col=collection_instance)
    elif info_key == "statutsConservationParRegne_dep":
        data = species_by_regne_and_statut_dep(col=collection_instance, dep=departements_a_analyser)
    else:
        data = [species_by_regne(col=collection_instance)]

    return data

@app.route('/header.html')
def get_header_html_fragment():
    return render_template('header.html')


@app.route('/footer.html')
def get_footer_html_fragment():
    return render_template('footer.html')


# *** ENDPOINTS API POUR LE CHATBOT ***

# Initialisation d'une nouvelle session de conversation avec le Chatbot
@app.route('/chat/start', methods=['POST'])
def start_chat_endpoint():
    conversation_id = str(uuid.uuid4()) # Génération d'un nouvel id pour cette nouvelle conv
    initial_question_id = "q_regne"
    initial_question_data = QUESTIONS_FLOW.get(initial_question_id)

    if initial_question_data:
        conversations[conversation_id] = {
            "current_question_id": initial_question_id,
            "answers": {},
            "mode": "questioning"
        }
        is_skippable = initial_question_data.get("skippable", False)
        return jsonify({
            "conversation_id": conversation_id,
            "question": {"text": initial_question_data["text"],
                         "id": initial_question_id,
                         "is_skippable": is_skippable},
            "is_final_questions": False
        })


# Gestion de la réception d'une réponse de l'utilisateur à une question du chatbot et détermine la prochaine action
@app.route('/chat/send', methods=['POST'])
def handle_message():
    data = request.json
    user_answer_raw = data.get('message')
    conversation_id = data.get('conversation_id')

    if not all([user_answer_raw is not None, conversation_id]):
        return jsonify({"error": "Message or conversation_id missing."}), 400

    conv_data = conversations.get(conversation_id)
    if not conv_data:
        return jsonify({"error": "Conversation not found or expired."}), 404

    if conv_data.get("mode") == "results_displayed":
        return jsonify({"info": "Results displayed. Use pagination or new chat.", "is_final_questions": True}), 200

    current_question_id = conv_data.get("current_question_id")  # Utiliser .get pour éviter KeyError
    if not current_question_id:  # Sécurité
        return jsonify({"error": "Conversation state error: current_question_id missing."}), 500

    current_question_config = QUESTIONS_FLOW.get(current_question_id)
    if not current_question_config:
        return jsonify({"error": f"Current question config not found for id: {current_question_id}."}), 500

    param_to_store = current_question_config.get("param_to_store")
    is_current_question_skippable_by_config = current_question_config.get("skippable", False)
    user_answer_processed_for_skip_check = user_answer_raw.strip().lower()  # Pour la vérification de skip

    # Déterminer l'action de l'utilisateur pour le logging (pour l'analyse)
    action_taken_for_log = "answered"
    if (is_current_question_skippable_by_config
            and (user_answer_processed_for_skip_check in SKIP_KEYWORDS
            or not user_answer_processed_for_skip_check)):

        action_taken_for_log = "skipped"

    # Log de l'interaction avec la question (skippée ou non) - pour question_interactions
    if question_interactions_log_col is not None:  # Vérifie si la collection de log est initialisée
        try:
            question_interactions_log_col.insert_one({
                "timestamp": datetime.now(timezone.utc),
                "conversation_id": conversation_id,
                "question_id": current_question_id,
                "action_taken": action_taken_for_log
            })
        except Exception as e:
            print(f"Erreur lors du logging de l'interaction question: {e}")

    # Traitement et stockage de la réponse - pour completed_searches
    value_to_store = user_answer_raw.strip()  # Stocker la valeur après strip
    if action_taken_for_log == "answered":  # On traite/stocke seulement si ce n'est pas un skip effectif
        if param_to_store in KNOWN_VALUES_FOR_FUZZY_MATCHING and value_to_store:  # value_to_store ici est la version strip()
            choices = KNOWN_VALUES_FOR_FUZZY_MATCHING[param_to_store]
            best_match, score = process.extractOne(value_to_store, choices,
                                                   scorer=fuzz.WRatio)  # Match sur la valeur strip()
            print(
                f"Fuzzy match for '{param_to_store}': input='{value_to_store}', best_match='{best_match}', score={score}")
            if score >= FUZZY_MATCH_THRESHOLD:
                value_to_store = best_match  # La valeur corrigée est stockée
                print(f"Correction applied: '{user_answer_raw.strip()}' -> '{value_to_store}'")
            # Si le score est trop bas, value_to_store reste la valeur originale (après strip)

        if param_to_store and value_to_store:  # Assure qu'il y a quelque chose à stocker
            conv_data["answers"][param_to_store] = value_to_store
    # Si c'est un skip effectif, on ne met rien dans conv_data["answers"] pour ce param_to_store

    next_question_id = current_question_config.get("next_question_id")

    if next_question_id == "results":
        # Préparer les filtres actifs (ceux où une valeur a été effectivement stockée)
        active_filters = {k: v for k, v in conv_data.get("answers", {}).items() if v is not None and v != ""}

        results_payload = get_results_from_db(active_filters, col=collection_instance, page=1)
        conv_data["mode"] = "results_displayed"

        # Log de la recherche complétée - completed_searches
        if completed_searches_log_col is not None:
            try:
                completed_searches_log_col.insert_one({
                    "timestamp": datetime.now(timezone.utc),
                    "conversation_id": conversation_id,
                    "filters_applied": active_filters,  # Logger uniquement les filtres actifs
                    "results_count": results_payload.get("total_items", 0)
                })
            except Exception as e:
                print(f"Erreur lors du logging de la recherche complétée: {e}")

        return jsonify({
            "results_data": results_payload,
            "is_final_questions": True,
            "conversation_id": conversation_id
        })

    elif next_question_id and next_question_id in QUESTIONS_FLOW:
        next_question_config = QUESTIONS_FLOW.get(next_question_id)
        conv_data["current_question_id"] = next_question_id
        is_next_skippable = next_question_config.get("skippable", False)
        return jsonify({
            "question": {"text": next_question_config["text"], "id": next_question_id,
                         "is_skippable": is_next_skippable},
            "is_final_questions": False, "conversation_id": conversation_id
        })

    else:
        active_answers = conv_data.get("answers", {})
        active_filters_fallback = {k: v for k, v in active_answers.items() if v is not None and v != ""}

        if active_filters_fallback:  # S'il y a au moins un filtre actif
            results_payload = get_results_from_db(active_filters_fallback, col=collection_instance, page=1)
            conv_data["mode"] = "results_displayed"
            # Log aussi cette recherche si elle produit des résultats
            if completed_searches_log_col:
                try:
                    completed_searches_log_col.insert_one({
                        "timestamp": datetime.now(timezone.utc),
                        "conversation_id": conversation_id,
                        "filters_applied": active_filters_fallback,
                        "results_count": results_payload.get("total_items", 0)
                    })
                except Exception as e:
                    print(f"Erreur lors du logging de la recherche (fallback): {e}")
            return jsonify({"results_data": results_payload, "is_final_questions": True,
                            "conversation_id": conversation_id,
                            "warning": "Chatbot flow ended unexpectedly, showing results."})

        conversations.pop(conversation_id, None)  # Pas de réponses, pas de résultats, fin de la conversation
        return jsonify({"error": "Chatbot flow error or no answers to process.", "is_final_questions": True}), 500


@app.route('/chat/results/<conversation_id>/page/<int:page_num>', methods=['GET'])
def get_paginated_results(conversation_id, page_num):
    conv_data = conversations.get(conversation_id)
    if not conv_data:
        return jsonify({"error": "Conversation not found or session expired."}), 404

    if "answers" not in conv_data or conv_data.get("mode") != "results_displayed":
        return jsonify({"error": "No search filters associated with this session or results not yet processed."}), 400

    if page_num < 1:
        return jsonify({"error": "Page number must be 1 or greater."}), 400

    filters = conv_data.get("answers", {})  # Utiliser .get avec une valeur par défaut
    active_filters_for_pagination = {k: v for k, v in filters.items() if v is not None and v != ""}

    # S'assurer que collection_instance est disponible
    if collection_instance is None:
        return jsonify({"error": "Database connection not available."}), 503

    results_payload = get_results_from_db(active_filters_for_pagination, col=collection_instance, page=page_num)

    return jsonify({
        "results_data": results_payload,
        "is_final_questions": True,
        "conversation_id": conversation_id
    })


if __name__ == '__main__':
    if collection_instance is not None:
        app.run(debug=True)
    else:
        print("L'application Flask n'a pas pu démarrer en raison d'un problème de connexion à MongoDB.")
