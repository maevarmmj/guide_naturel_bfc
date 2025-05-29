from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_cors import CORS
import uuid
from thefuzz import process, fuzz

from API_request.mongo_request import *
from API_request.recherche import *

app = Flask(__name__)
CORS(app)

# Configuration MongoDB
MONGO_URI = "mongodb+srv://guest:guestpass@big-data.640be.mongodb.net/?retryWrites=true&w=majority&appName=Big-Data"
DB_NAME = 'LeGuideNaturel'
COLLECTION_NAME = 'Nature'

mongo_client_instance = None
collection_instance = None

departements_a_analyser = [21, 25, 39, 58, 70, 71, 89, 90]

# Connexion à la base de donnée
try:
    collection_instance = get_mongo_collection(MONGO_URI, DB_NAME, COLLECTION_NAME)
    mongo_client_instance = collection_instance.database.client
    print("MongoDB client initialized for Flask app.")
except Exception as e:
    print(f"Failed to initialize MongoDB client for Flask app: {e}")


# *** Routes Flask ***
@app.route('/')
def index():
    return redirect(url_for('guide_naturel'))


@app.route('/guide_naturel')
def guide_naturel():

    initial_info = request.args.get('info', 'default')

    return render_template(
        'index.html',
        initial_info=initial_info  # Passons toutes les données préparées
    )


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


# Initialisation d'une nouvelle session de conversation avec le Chatbot
@app.route('/chat/start', methods=['POST'])
def start_chat():
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

    return jsonify({"error": "Could not start chat"}), 500


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

    current_question_id = conv_data["current_question_id"]
    current_question_config = QUESTIONS_FLOW.get(current_question_id)

    if not current_question_config:
        return jsonify({"error": "Current question config not found."}), 500

    param_to_store = current_question_config.get("param_to_store")
    is_current_question_skippable_by_config = current_question_config.get("skippable", False)
    user_answer_processed = user_answer_raw.strip().lower()

    value_to_store = user_answer_processed

    if param_to_store in KNOWN_VALUES_FOR_FUZZY_MATCHING and user_answer_processed:
        choices = KNOWN_VALUES_FOR_FUZZY_MATCHING[param_to_store]
        best_match, score = process.extractOne(user_answer_processed, choices, scorer=fuzz.WRatio)

        print(
            f"Fuzzy match for '{param_to_store}': input='{user_answer_processed}', best_match='{best_match}', score={score}")
        if score >= FUZZY_MATCH_THRESHOLD:
            value_to_store = best_match
            print(f"Correction applied: '{user_answer_processed}' -> '{value_to_store}'")
        else:
            print(f"Fuzzy score too low for '{user_answer_processed}'. Storing original (or consider re-prompting).")

    if not (is_current_question_skippable_by_config
            and (user_answer_processed.lower() in SKIP_KEYWORDS or not user_answer_processed)):
        if param_to_store:
            conv_data["answers"][param_to_store] = value_to_store

    next_question_id = current_question_config.get("next_question_id")

    if next_question_id == "results":
        results_payload = get_results_from_db(conv_data["answers"], col=collection_instance, page=1)
        conv_data["mode"] = "results_displayed"
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
            "question": {
                         "text": next_question_config["text"],
                         "id": next_question_id,
                         "is_skippable": is_next_skippable
                         },
            "is_final_questions": False, "conversation_id": conversation_id
        })
    else:
        if conv_data.get("answers"):
            results_payload = get_results_from_db(conv_data["answers"], col=collection_instance, page=1)
            conv_data["mode"] = "results_displayed"
            return jsonify({
                "results_data": results_payload,
                "is_final_questions": True,
                "conversation_id": conversation_id,
                "warning": "Chatbot flow ended unexpectedly, showing results."
            })
        conversations.pop(conversation_id, None)
        return jsonify({"error": "Chatbot flow error or no answers.", "is_final_questions": True}), 500


@app.route('/chat/results/<conversation_id>/page/<int:page_num>', methods=['GET'])
def get_paginated_results(conversation_id, page_num):
    conv_data = conversations.get(conversation_id)
    if not conv_data:
        return jsonify({"error": "Conversation not found."}), 404

    if "answers" not in conv_data or conv_data.get("mode") != "results_displayed":
        return jsonify({"error": "No search filters or results not processed."}), 400

    if page_num < 1:
        return jsonify({"error": "Page number must be >= 1."}), 400

    filters = conv_data["answers"]
    results_payload = get_results_from_db(filters,col=collection_instance, page=page_num)

    return jsonify({
        "results_data": results_payload, "is_final_questions": True, "conversation_id": conversation_id
    })


if __name__ == '__main__':
    if collection_instance is not None:
        app.run(debug=True)
    else:
        print("L'application Flask n'a pas pu démarrer en raison d'un problème de connexion à MongoDB.")
