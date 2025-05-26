from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import uuid
import os
import math  # Nécessaire pour math.ceil

app = Flask(__name__)
CORS(app)

# Configuration MongoDB
MONGO_URI = "mongodb+srv://guest:guestpass@big-data.640be.mongodb.net/?retryWrites=true&w=majority&appName=Big-Data"
DB_NAME = 'LeGuideNaturel'
OBSERVATIONS_COLLECTION = 'Nature'
RESULTS_PER_PAGE = 20  # Nombre de résultats par page

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

conversations = {}  # Stocke l'état des conversations, y compris les filtres pour la pagination

# Les questions que le Chatbot va poser (inchangé)
QUESTIONS_FLOW = {
    "q1": {
        "text": "Bonjour ! Quel groupe taxonomique simple vous intéresse ? (ex: Oiseaux, Mammifères, Insectes, Plantes à fleurs, ou tapez 'passer' pour ignorer)",
        "next_question_id": "q2",
        "param_to_store": "groupeTaxoSimple",
        "skippable": True
    },
    "q2": {
        "text": "D'accord. Dans quel département souhaitez-vous rechercher ? (Code INSEE, ex: 21, 25, ou tapez 'passer' pour ignorer)",
        "next_question_id": "q_commune",
        "param_to_store": "codeInseeDepartement",
        "skippable": True
    },
    "q_commune": {
        "text": "Souhaitez-vous spécifier une commune ? (Nom de la commune, ou tapez 'passer' pour ignorer)",
        "next_question_id": "q_nom_vern",
        "param_to_store": "commune",
        "skippable": True
    },
    "q_nom_vern": {
        "text": "Connaissez-vous le nom commun (vernaculaire) de l'espèce recherchée ? (Ou une partie du nom. Sinon, tapez 'passer')",
        "next_question_id": "q_regne",
        "param_to_store": "nomVernaculaire",
        "skippable": True
    },
    "q_regne": {
        "text": "Voulez-vous filtrer par règne ? (ex: Animalia, Plantae, Fungi, ou tapez 'passer')",
        "next_question_id": "q_code_statut",
        "param_to_store": "regne",
        "skippable": True
    },
    "q_code_statut": {
        "text": "Avez-vous un code de statut d'observation spécifique en tête ? (ex: P, O, C, ou tapez 'passer')",
        "next_question_id": "results",  # Après cette question, on passe aux résultats
        "param_to_store": "codeStatut",
        "skippable": True
    }
}

SKIP_KEYWORDS = ["passer", "skip", "ignorer", "non"]


def build_mongo_query(filters):
    query = {}
    if "groupeTaxoSimple" in filters and filters["groupeTaxoSimple"]:
        query["groupeTaxoSimple"] = {"$regex": f"^{filters['groupeTaxoSimple']}", "$options": "i"}
    if "codeInseeDepartement" in filters and filters["codeInseeDepartement"]:
        query["codeInseeDepartement"] = filters["codeInseeDepartement"]
    if "commune" in filters and filters["commune"]:
        query["commune"] = {"$regex": f"^{filters['commune']}", "$options": "i"}
    if "nomVernaculaire" in filters and filters["nomVernaculaire"]:
        query["nomVernaculaire"] = {"$regex": filters['nomVernaculaire'], "$options": "i"}
    if "regne" in filters and filters["regne"]:
        query["regne"] = {"$regex": f"^{filters['regne']}$", "$options": "i"}
    if "codeStatut" in filters and filters["codeStatut"]:
        query["codeStatut"] = {"$regex": f"^{filters['codeStatut']}$", "$options": "i"}
    return query


def get_results_from_db(filters, page=1):
    query = build_mongo_query(filters)

    if not query:
        return {
            "items": [],
            "message": "Veuillez spécifier au moins un critère de recherche.",
            "page": page,
            "per_page": RESULTS_PER_PAGE,
            "total_items": 0,
            "total_pages": 0,
            "query_used": query  # Pour débogage
        }

    print(f"Executing MongoDB query: {query} for page {page}")

    total_items = db[OBSERVATIONS_COLLECTION].count_documents(query)

    if total_items == 0:
        return {
            "items": [],
            "message": "Désolé, je n'ai rien trouvé avec ces critères.",
            "page": page,
            "per_page": RESULTS_PER_PAGE,
            "total_items": 0,
            "total_pages": 0,
            "query_used": query  # Pour débogage
        }

    skip_value = (page - 1) * RESULTS_PER_PAGE

    results_cursor = db[OBSERVATIONS_COLLECTION].find(query, {
        "_id": 0,  # Exclure l'ID de MongoDB
        "nomVernaculaire": 1,
        "nomScientifiqueRef": 1,
        "regne": 1,
        "commune": 1,
        "nombreObservations": 1
        # Ajoutez d'autres champs si nécessaire
    }).skip(skip_value).limit(RESULTS_PER_PAGE)

    items_on_page = list(results_cursor)
    total_pages = math.ceil(total_items / RESULTS_PER_PAGE)

    # Formatter les résultats pour qu'ils soient directement utilisables (chaque item est un dictionnaire)
    # La mise en forme textuelle se fera côté client pour plus de flexibilité

    return {
        "items": items_on_page,
        "message": f"Page {page} sur {total_pages} ({total_items} résultats au total).",
        "page": page,
        "per_page": RESULTS_PER_PAGE,
        "total_items": total_items,
        "total_pages": total_pages,
        "query_used": query  # Pour débogage
    }


@app.route('/chat/start', methods=['POST'])
def start_chat():
    conversation_id = str(uuid.uuid4())
    initial_question_id = "q1"
    initial_question_data = QUESTIONS_FLOW.get(initial_question_id)

    if initial_question_data:
        conversations[conversation_id] = {
            "current_question_id": initial_question_id,
            "answers": {},  # Pour stocker les filtres
            "mode": "questioning"  # Indique qu'on est en phase de questions
        }
        is_skippable = initial_question_data.get("skippable", False)
        return jsonify({
            "conversation_id": conversation_id,
            "question": {
                "text": initial_question_data["text"],
                "id": initial_question_id,
                "is_skippable": is_skippable
            },
            "is_final_questions": False  # Le flux de questions n'est pas terminé
        })
    else:
        return jsonify({"error": "Could not start chat, no initial question configuration."}), 500


@app.route('/chat/send', methods=['POST'])
def handle_message():
    data = request.json
    user_answer_raw = data.get('message')
    conversation_id = data.get('conversation_id')

    if not all([user_answer_raw is not None, conversation_id]):  # Vérifier que user_answer_raw n'est pas None
        return jsonify({"error": "Message or conversation_id missing."}), 400

    conv_data = conversations.get(conversation_id)
    if not conv_data:
        return jsonify({"error": "Conversation not found or expired."}), 404

    # Si on est déjà en mode résultat, ce endpoint n'est pas pour la pagination
    if conv_data.get("mode") == "results_displayed":
        # On pourrait vouloir gérer une nouvelle recherche ici, mais pour l'instant,
        # on suppose que le client utilisera /chat/start pour une nouvelle recherche.
        # Ou permettre de relancer une recherche avec les mêmes filtres mais pour page 1 ?
        # Pour l'instant, on bloque pour éviter la confusion.
        return jsonify({
            "info": "Results already displayed. Use pagination endpoint or start a new chat.",
            "is_final_questions": True
        }), 200

    current_question_id = conv_data["current_question_id"]
    current_question_config = QUESTIONS_FLOW.get(current_question_id)

    param_to_store = current_question_config.get("param_to_store")
    is_current_question_skippable_by_config = current_question_config.get("skippable", False)
    user_answer_processed = user_answer_raw.strip()

    if not (is_current_question_skippable_by_config and \
            (user_answer_processed.lower() in SKIP_KEYWORDS or not user_answer_processed)):
        if param_to_store:
            conv_data["answers"][param_to_store] = user_answer_processed

    next_question_id = current_question_config.get("next_question_id")

    if next_question_id == "results":
        # Les questions sont terminées, on récupère la première page de résultats
        results_payload = get_results_from_db(conv_data["answers"], page=1)
        conv_data["mode"] = "results_displayed"  # Marquer que les résultats (page 1) ont été envoyés
        # La conversation (avec ses filtres) est conservée pour la pagination

        return jsonify({
            "results_data": results_payload,  # Contient items, page, total_pages, etc.
            "is_final_questions": True,  # Le flux de questions est terminé
            "conversation_id": conversation_id  # Important pour les futurs appels de pagination
        })

    elif next_question_id and next_question_id in QUESTIONS_FLOW:
        next_question_config = QUESTIONS_FLOW.get(next_question_id)
        conv_data["current_question_id"] = next_question_id
        is_next_question_skippable = next_question_config.get("skippable", False)
        return jsonify({
            "question": {
                "text": next_question_config["text"],
                "id": next_question_id,
                "is_skippable": is_next_question_skippable
            },
            "is_final_questions": False,
            "conversation_id": conversation_id  # Toujours renvoyer pour garder la session
        })
    else:
        # Fin anormale du flux ou erreur de configuration
        # On pourrait tenter de donner des résultats si des filtres existent
        if conv_data["answers"]:
            results_payload = get_results_from_db(conv_data["answers"], page=1)
            conv_data["mode"] = "results_displayed"
            return jsonify({
                "results_data": results_payload,
                "is_final_questions": True,
                "conversation_id": conversation_id,
                "warning": "Chatbot flow ended unexpectedly, showing results based on current answers."
            })
        # Si pas de réponse, et pas de flux normal, alors erreur.
        # conversations.pop(conversation_id, None) # On pourrait nettoyer ici
        return jsonify({"error": "Chatbot flow error or end of defined flow.", "is_final_questions": True}), 500


# NOUVELLE ROUTE POUR LA PAGINATION DES RÉSULTATS
@app.route('/chat/results/<conversation_id>/page/<int:page_num>', methods=['GET'])
def get_paginated_results(conversation_id, page_num):
    conv_data = conversations.get(conversation_id)
    if not conv_data:
        return jsonify({"error": "Conversation not found or expired. Please start a new search."}), 404

    # S'assurer que la conversation a bien des filtres (a atteint l'étape des résultats)
    if "answers" not in conv_data or conv_data.get("mode") != "results_displayed":
        return jsonify({
                           "error": "No search filters found for this conversation or results not yet processed. Please complete the questions first."}), 400

    if page_num < 1:
        return jsonify({"error": "Page number must be 1 or greater."}), 400

    filters = conv_data["answers"]
    results_payload = get_results_from_db(filters, page=page_num)

    # Vérifier si la page demandée est valide par rapport au nombre total de pages
    # (get_results_from_db gère déjà le cas où page_num > total_pages en retournant une liste vide,
    # mais on pourrait ajouter une vérification ici aussi si on le souhaite)

    return jsonify({
        "results_data": results_payload,
        "is_final_questions": True,  # On est toujours en mode "questions finies"
        "conversation_id": conversation_id
    })


if __name__ == '__main__':
    app.run(debug=True, port=5001)