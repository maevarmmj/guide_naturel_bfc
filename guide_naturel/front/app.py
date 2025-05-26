from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import uuid
import os
import math

app = Flask(__name__)
CORS(app)

# Configuration MongoDB
MONGO_URI = "mongodb+srv://guest:guestpass@big-data.640be.mongodb.net/?retryWrites=true&w=majority&appName=Big-Data"
DB_NAME = 'LeGuideNaturel'
OBSERVATIONS_COLLECTION = 'Nature'
RESULTS_PER_PAGE = 20

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

conversations = {}

QUESTIONS_FLOW = {
    "q_regne": {
        "text": "Commençons ! As-tu un règne que tu veux chercher ? (ex: Animalia, Plantae, Fungi, ou tapez 'passer')",
        "next_question_id": "q_groupe_taxo",
        "param_to_store": "regne",
        "skippable": True
    },
    "q_groupe_taxo": {
        "text": "Quel groupe taxonomique simple t'intéresse ? (ex: Oiseaux, Mammifères, Insectes, Plantes à fleurs...)",
        "next_question_id": "q2",
        "param_to_store": "groupeTaxoSimple",
        "skippable": True
    },
    "q2": {  # Question sur le département
        "text": "Hum, je vois ! Et ce serait dans quel département ? (Code INSEE numérique svp : 21, 25,... ou 'passer')",
        "next_question_id": "q_commune",
        "param_to_store": "codeInseeDepartement",
        "skippable": True
    },
    "q_commune": {
        "text": "Si tu as une commune à spécifier, je suis preneuse ! (ex : Dijon, Besançon...)",
        "next_question_id": "q_nom_vern",
        "param_to_store": "commune",
        "skippable": True
    },
    "q_nom_vern": {
        "text": "Petite question compliquée : connais-tu le nom commun (vernaculaire) de l'espèce recherchée ? Ou une partie du nom ?",
        "next_question_id": "q_code_statut",
        "param_to_store": "nomVernaculaire",
        "skippable": True
    },
    "q_code_statut": {
        "text": "As-tu un code de statut d'observation spécifique en tête ? (ex: P, O, C)",
        "next_question_id": "results",
        "param_to_store": "codeStatut",
        "skippable": True
    }
}

SKIP_KEYWORDS = ["passer", "skip", "ignorer", "non"]


def build_mongo_match_stage(filters):
    match_query = {}
    if "regne" in filters and filters["regne"]:
        match_query["regne"] = {"$regex": f"^{filters['regne']}$", "$options": "i"}
    if "groupeTaxoSimple" in filters and filters["groupeTaxoSimple"]:
        match_query["groupeTaxoSimple"] = {"$regex": f"^{filters['groupeTaxoSimple']}", "$options": "i"}

    # Le filtre codeInseeDepartement est crucial pour la logique d'agrégation
    if "codeInseeDepartement" in filters and filters["codeInseeDepartement"]:
        code_dept_str = filters["codeInseeDepartement"]
        try:
            code_dept_int = int(code_dept_str)
            match_query["codeInseeDepartement"] = code_dept_int
        except ValueError:
            print(f"Avertissement: Valeur invalide pour codeInseeDepartement '{code_dept_str}', filtre ignoré.")
            # Si le code dept est invalide, il ne sera pas dans les filtres,
            # donc l'agrégation se comportera comme si aucun département n'était spécifié.
            pass

    if "commune" in filters and filters["commune"]:
        # Le filtre commune n'a de sens que si un département est aussi spécifié.
        # On pourrait ajouter une logique ici pour l'ignorer si codeInseeDepartement n'est pas dans les filtres.
        # Pour l'instant, on le laisse, mais l'agrégation le traitera.
        match_query["commune"] = {"$regex": f"^{filters['commune']}", "$options": "i"}

    if "nomVernaculaire" in filters and filters["nomVernaculaire"]:
        match_query["nomVernaculaire"] = {"$regex": filters['nomVernaculaire'], "$options": "i"}
    if "codeStatut" in filters and filters["codeStatut"]:
        match_query["codeStatut"] = {"$regex": f"^{filters['codeStatut']}$", "$options": "i"}
    return match_query


def get_results_from_db(filters, page=1):
    match_stage_query = build_mongo_match_stage(filters)
    departement_specifie = "codeInseeDepartement" in match_stage_query  # True si un code dept valide a été filtré

    # Si aucun filtre n'est appliqué (sauf potentiellement nomVernaculaire qui est un pré-filtre)
    # on pourrait vouloir un message différent ou un comportement par défaut.
    # Pour l'instant, on procède si au moins un filtre (autre que juste nomVernaculaire pour recherche large) est là.
    # Ou si nomVernaculaire est le SEUL filtre.

    # S'il n'y a aucun filtre du tout après la construction, on sort tôt.
    if not match_stage_query and not ("nomVernaculaire" in filters and filters["nomVernaculaire"]):
        return {
            "items": [], "message": "Veuillez spécifier au moins un critère de recherche.",
            "page": page, "per_page": RESULTS_PER_PAGE, "total_items": 0, "total_pages": 0,
            "query_used": match_stage_query, "aggregation_type": "none"
        }

    pipeline = []
    if match_stage_query:
        pipeline.append({"$match": match_stage_query})

    # Définition du group_stage
    group_id_key = "$nomVernaculaire"  # Clé de groupement principale

    common_group_fields = {
        "nomVernaculaire": {"$first": "$nomVernaculaire"},
        "nomScientifiqueRef": {"$first": "$nomScientifiqueRef"},
        "regne": {"$first": "$regne"},
        "groupeTaxoSimple": {"$first": "$groupeTaxoSimple"},
        "statuts": {"$addToSet": "$codeStatut"},
        "totalObservationsEspece": {"$sum": "$nombreObservations"}
    }

    if departement_specifie:
        # Agrégation spécifique si un département est fourni : inclure les communes du/des département(s) filtré(s)
        group_stage = {
            "$group": {
                "_id": group_id_key,
                **common_group_fields,
                "departements": {"$addToSet": "$codeInseeDepartement"},  # Devrait être le(s) dept spécifié(s)
                "communesDetails": {
                    "$addToSet": {
                        "commune": "$commune",
                        "departement": "$codeInseeDepartement"
                    }
                },
                "aggregation_type": {"$first": "departement_specifique"}  # Pour le debug/frontend
            }
        }
    else:
        # Agrégation générale si aucun département n'est fourni : lister tous les départements, pas de détail commune
        group_stage = {
            "$group": {
                "_id": group_id_key,
                **common_group_fields,
                "departements": {"$addToSet": "$codeInseeDepartement"},  # Tous les départements où l'espèce est trouvée
                # Pas de communesDetails ici car la recherche est large
                "aggregation_type": {"$first": "nationale_sans_communes"}  # Pour le debug/frontend
            }
        }
    pipeline.append(group_stage)

    # Comptage pour la pagination
    count_pipeline = pipeline + [{"$count": "total_items"}]
    print(f"Executing Aggregation Count Pipeline: {count_pipeline}")
    count_result = list(db[OBSERVATIONS_COLLECTION].aggregate(count_pipeline))
    total_items = count_result[0]["total_items"] if count_result else 0

    if total_items == 0:
        message_no_results = "Désolée, je n'ai rien trouvé avec ces critères."
        if not match_stage_query and ("nomVernaculaire" in filters and filters["nomVernaculaire"]):
            message_no_results = f"Aucune observation trouvée pour '{filters['nomVernaculaire']}' avec les autres filtres (ou sans)."

        return {
            "items": [], "message": message_no_results,
            "page": page, "per_page": RESULTS_PER_PAGE, "total_items": 0, "total_pages": 0,
            "query_used": match_stage_query,
            "aggregation_type": group_stage["$group"].get("aggregation_type", {"$first": "unknown"}).get("$first")
        }

    total_pages = math.ceil(total_items / RESULTS_PER_PAGE)
    if page < 1: page = 1
    if page > total_pages and total_pages > 0: page = total_pages  # Correction si page trop élevée

    pipeline.append({"$sort": {"nomVernaculaire": 1}})  # ou "_id": 1
    skip_value = (page - 1) * RESULTS_PER_PAGE
    pipeline.append({"$skip": skip_value})
    pipeline.append({"$limit": RESULTS_PER_PAGE})

    print(f"Executing Full Aggregation Pipeline: {pipeline}")
    aggregated_results = list(db[OBSERVATIONS_COLLECTION].aggregate(pipeline))

    message_text = f"Page {page} sur {total_pages} ({total_items} espèces trouvées).\n"
    if not aggregated_results and total_items > 0:
        message_text = "Aucune espèce sur cette page (mais il y en a sur d'autres pages)."

    # S'assurer que chaque item a bien 'aggregation_type' pour le frontend
    final_aggregation_type = group_stage["$group"].get("aggregation_type", {"$first": "unknown"}).get("$first")
    for item in aggregated_results:
        if "aggregation_type" not in item:  # Au cas où $first ne le met pas si le groupe est vide (ne devrait pas arriver ici)
            item["aggregation_type"] = final_aggregation_type

    return {
        "items": aggregated_results,
        "message": message_text,
        "page": page,
        "per_page": RESULTS_PER_PAGE,
        "total_items": total_items,
        "total_pages": total_pages,
        "query_used": match_stage_query,
        "aggregation_type": final_aggregation_type  # Renvoyer le type d'agrégation utilisé
    }


# Les routes @app.route('/chat/start'), @app.route('/chat/send'), @app.route('/chat/results/...')
# restent identiques à votre version précédente, car elles appellent get_results_from_db
# qui gère maintenant la logique d'agrégation conditionnelle.

@app.route('/chat/start', methods=['POST'])
def start_chat():
    conversation_id = str(uuid.uuid4())
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
            "question": {
                "text": initial_question_data["text"],
                "id": initial_question_id,
                "is_skippable": is_skippable
            },
            "is_final_questions": False
        })
    else:
        return jsonify({"error": "Could not start chat, no initial question configuration."}), 500


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
        return jsonify({
            "info": "Results already displayed. Use pagination endpoint or start a new chat.",
            "is_final_questions": True
        }), 200

    current_question_id = conv_data["current_question_id"]
    current_question_config = QUESTIONS_FLOW.get(current_question_id)

    if not current_question_config:
        return jsonify({"error": "Current question configuration not found."}), 500

    param_to_store = current_question_config.get("param_to_store")
    is_current_question_skippable_by_config = current_question_config.get("skippable", False)
    user_answer_processed = user_answer_raw.strip()

    if not (is_current_question_skippable_by_config and \
            (user_answer_processed.lower() in SKIP_KEYWORDS or not user_answer_processed)):
        if param_to_store:
            conv_data["answers"][param_to_store] = user_answer_processed

    next_question_id = current_question_config.get("next_question_id")

    if next_question_id == "results":
        results_payload = get_results_from_db(conv_data["answers"], page=1)
        if not results_payload.get("items") and results_payload.get("total_items", 0) == 0 and not conv_data.get(
                "answers"):
            conv_data["mode"] = "questioning"
        else:
            conv_data["mode"] = "results_displayed"
        return jsonify({
            "results_data": results_payload,  # Contient maintenant aggregation_type
            "is_final_questions": True,
            "conversation_id": conversation_id
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
            "conversation_id": conversation_id
        })
    else:
        if conv_data.get("answers"):
            results_payload = get_results_from_db(conv_data["answers"], page=1)
            conv_data["mode"] = "results_displayed"
            return jsonify({
                "results_data": results_payload,
                "is_final_questions": True,
                "conversation_id": conversation_id,
                "warning": "Chatbot flow ended unexpectedly, showing results based on current answers."
            })
        conversations.pop(conversation_id, None)
        return jsonify({"error": "Chatbot flow error or no answers provided.", "is_final_questions": True}), 500


@app.route('/chat/results/<conversation_id>/page/<int:page_num>', methods=['GET'])
def get_paginated_results(conversation_id, page_num):
    conv_data = conversations.get(conversation_id)
    if not conv_data:
        return jsonify({"error": "Conversation not found or expired. Please start a new search."}), 404

    if "answers" not in conv_data or conv_data.get("mode") != "results_displayed":
        return jsonify({
            "error": "No search filters for this conversation or results not yet processed."}), 400

    if page_num < 1:
        return jsonify({"error": "Page number must be 1 or greater."}), 400

    filters = conv_data["answers"]
    results_payload = get_results_from_db(filters, page=page_num)

    return jsonify({
        "results_data": results_payload,  # Contient maintenant aggregation_type
        "is_final_questions": True,
        "conversation_id": conversation_id
    })


if __name__ == '__main__':
    app.run(debug=True, port=5001)