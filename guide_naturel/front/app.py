from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import uuid
import os

app = Flask(__name__)
CORS(app) # Important pour le développement local

# Configuration MongoDB
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "guide_naturel_db"
OBSERVATIONS_COLLECTION = "observations_data"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

conversations = {}

QUESTIONS_FLOW = {
    "q1": {
        "text": "Bonjour ! Quel groupe taxonomique simple vous intéresse ? (ex: Oiseaux, Mammifères, Insectes, Plantes à fleurs)",
        "next_question_id": "q2",
        "param_to_store": "groupeTaxoSimple"
    },
    "q2": {
        "text": "D'accord. Dans quel département souhaitez-vous rechercher ? (Veuillez entrer le code INSEE du département, ex: 21, 25, 70, 89, 39, 58, 71, 90)",
        "next_question_id": "results", # Marqueur pour indiquer la génération de résultats
        "param_to_store": "codeInseeDepartement"
    }
}

def get_results_from_db(filters):
    # Exemple de requête simple. 'filters' est un dictionnaire comme {'groupeTaxoSimple': 'Oiseaux', 'codeInseeDepartement': '25'}
    # Pour MongoDB, les filtres de texte sont sensibles à la casse par défaut.
    # Pour une recherche insensible à la casse, on peut utiliser $regex.
    query = {}
    if "groupeTaxoSimple" in filters:
        # Recherche insensible à la casse pour groupeTaxoSimple
        query["groupeTaxoSimple"] = {"$regex": f"^{filters['groupeTaxoSimple']}$", "$options": "i"}
    if "codeInseeDepartement" in filters:
        query["codeInseeDepartement"] = filters["codeInseeDepartement"]

    results = list(db[OBSERVATIONS_COLLECTION].find(query, {"_id": 0, "nomVernaculaire": 1, "nomScientifiqueRef": 1, "commune": 1, "nombreObservations":1}))
    if results:
        formatted_results = "Voici ce que j'ai trouvé :\n"
        for res in results:
            formatted_results += f"- {res.get('nomVernaculaire', 'N/A')} ({res.get('nomScientifiqueRef', 'N/A')}) observé(e) à {res.get('commune', 'N/A')} ({res.get('nombreObservations', 'N/A')} obs.)\n"
        return formatted_results
    else:
        return "Désolé, je n'ai rien trouvé avec ces critères."

@app.route('/chat/start', methods=['POST'])
def start_chat():
    conversation_id = str(uuid.uuid4())
    initial_question_id = "q1"
    initial_question_data = QUESTIONS_FLOW.get(initial_question_id)

    if initial_question_data:
        conversations[conversation_id] = {
            "current_question_id": initial_question_id,
            "answers": {}
        }
        return jsonify({
            "conversation_id": conversation_id,
            "question": {"text": initial_question_data["text"], "id": initial_question_id},
            "is_final": False
        })
    else:
        return jsonify({"error": "Could not start chat, no initial question configuration."}), 500

@app.route('/chat/send', methods=['POST'])
def handle_message():
    data = request.json
    user_answer = data.get('message')
    conversation_id = data.get('conversation_id')

    if not conversation_id or conversation_id not in conversations:
        return jsonify({"error": "Invalid or missing conversation ID"}), 400
    if user_answer is None:
        return jsonify({"error": "Message is required"}), 400


    conv_data = conversations.get(conversation_id)
    current_question_id = conv_data["current_question_id"]
    current_question_config = QUESTIONS_FLOW.get(current_question_id)

    if not current_question_config:
        return jsonify({"error": "Chatbot configuration error."}), 500

    param_to_store = current_question_config.get("param_to_store")
    if param_to_store:
        conv_data["answers"][param_to_store] = user_answer

    next_question_id = current_question_config.get("next_question_id")

    if next_question_id == "results":
        results_text = get_results_from_db(conv_data["answers"])
        conversations.pop(conversation_id, None)
        return jsonify({"results": results_text, "is_final": True})
    elif next_question_id and next_question_id in QUESTIONS_FLOW:
        next_question_config = QUESTIONS_FLOW.get(next_question_id)
        conv_data["current_question_id"] = next_question_id
        return jsonify({
            "question": {"text": next_question_config["text"], "id": next_question_id},
            "is_final": False
        })
    else:
        conversations.pop(conversation_id, None)
        return jsonify({"error": "Chatbot flow error or end of defined flow.", "is_final": True}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)