import uuid
import math
from thefuzz import process, fuzz

RESULTS_PER_PAGE = 30
FUZZY_MATCH_THRESHOLD = 20  # Seuil d'acceptation de correction

conversations = {}

QUESTIONS_FLOW = {
    "q_regne": {
        "text": "Commençons ! As-tu un règne que tu veux chercher ? (Animalia, Plantae ou Fungi)",
        "next_question_id": "q_groupe_taxo",
        "param_to_store": "regne",
        "skippable": True
    },
    "q_groupe_taxo": {
        "text": "Quel groupe taxonomique simple t'intéresse ? (Oiseaux, Mammifères, Insectes, Plantes à fleurs...)",
        "next_question_id": "q2",
        "param_to_store": "groupeTaxoSimple",
        "skippable": True
    },
    "q2": {
        "text": "Hum, je vois ! Et ce serait dans quel département ? (Le 21, 25, 70, 39, 58, 71, 90, ou 89)",
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
        "text": "Petite question compliquée : connais-tu le nom commun (ou vernaculaire) de l'espèce recherchée ? Ou une partie du nom ?",
        "next_question_id": "q_code_statut",
        "param_to_store": "nomVernaculaire",
        "skippable": True
    },
    "q_code_statut": {
        "text": "As-tu un code de statut d'observation spécifique en tête ? DD, LC, CR... Tu peux te renseigner sur les différents statuts de conservation qui existent !",
        "next_question_id": "results",
        "param_to_store": "codeStatut",
        "skippable": True
    }
}

SKIP_KEYWORDS = ["passer", "skip", "ignorer", "non"]

# Valeurs connues pour le fuzzy matching
# Compliqué avec les communes et noms vernaculaires
KNOWN_VALUES_FOR_FUZZY_MATCHING = {
    "regne": ["Animalia", "Plantae", "Fungi"],
    "groupeTaxoSimple": ["Amphibiens et reptiles",
                         "Autres",
                         "Crabes, crevettes, cloportes et mille-pattes",
                         "Escargots et autres mollusques",
                         "Insectes et araignées",
                         "Mammifères",
                         "Oiseaux",
                         "Poissons",
                         "Champignons et lichens",
                         "Plantes, mousses et fougères"],
    "codeStatut": ["EX", "EW", "CR", "EN", "VU", "NT", "LC", "DD", "NE"]
}

# Query
def build_mongo_match_stage(filters):
    match_query = {}
    if "regne" in filters and filters["regne"]:
        match_query["regne"] = {"$regex": f"^{filters['regne']}$", "$options": "i"}
    if "groupeTaxoSimple" in filters and filters["groupeTaxoSimple"]:
        match_query["groupeTaxoSimple"] = {"$regex": f"^{filters['groupeTaxoSimple']}", "$options": "i"}

    if "codeInseeDepartement" in filters and filters["codeInseeDepartement"]:
        code_dept_str = filters["codeInseeDepartement"]
        code_dept_int = int(code_dept_str)
        match_query["codeInseeDepartement"] = code_dept_int

    if "commune" in filters and filters["commune"]:
        match_query["commune"] = {"$regex": f"^{filters['commune']}", "$options": "i"}

    if "nomVernaculaire" in filters and filters["nomVernaculaire"]:
        match_query["nomVernaculaire"] = {"$regex": filters['nomVernaculaire'], "$options": "i"}

    if "codeStatut" in filters and filters["codeStatut"]:
        match_query["codeStatut"] = {"$regex": f"^{filters['codeStatut']}$", "$options": "i"}
    return match_query


def get_results_from_db(filters, col, page=1):
    match_stage_query = build_mongo_match_stage(filters)
    departement_specifie = "codeInseeDepartement" in match_stage_query

    if not match_stage_query and not ("nomVernaculaire" in filters and filters["nomVernaculaire"]):
        return {
            "items": [], "message": "Veuillez spécifier au moins un critère de recherche.",
            "page": page, "per_page": RESULTS_PER_PAGE, "total_items": 0, "total_pages": 0,
            "query_used": match_stage_query, "aggregation_type": "none"
        }

    pipeline = []
    if match_stage_query:
        pipeline.append({"$match": match_stage_query})

    group_id_key = "$nomVernaculaire"
    common_group_fields = {
        "nomVernaculaire": {"$first": "$nomVernaculaire"},
        "nomScientifiqueRef": {"$first": "$nomScientifiqueRef"},
        "regne": {"$first": "$regne"},
        "groupeTaxoSimple": {"$first": "$groupeTaxoSimple"},
        "statuts": {"$addToSet": "$codeStatut"},
        "totalObservationsEspece": {"$sum": "$nombreObservations"}
    }

    if departement_specifie:
        group_stage = {
            "$group": {
                "_id": group_id_key, **common_group_fields,
                "departements": {"$addToSet": "$codeInseeDepartement"},
                "communesDetails": {"$addToSet": {"commune": "$commune", "departement": "$codeInseeDepartement"}},
                "aggregation_type": {"$first": "departement_specifique"}
            }
        }
    else:
        group_stage = {
            "$group": {
                "_id": group_id_key, **common_group_fields,
                "departements": {"$addToSet": "$codeInseeDepartement"},
                "aggregation_type": {"$first": "nationale_sans_communes"}
            }
        }
    pipeline.append(group_stage)

    count_pipeline = pipeline + [{"$count": "total_items"}]
    count_result = list(col.aggregate(count_pipeline))
    total_items = count_result[0]["total_items"] if count_result else 0

    if total_items == 0:
        message_no_results = "Désolée, je n'ai rien trouvé avec ces critères..."
        return {
            "items": [], "message": message_no_results, "page": page, "per_page": RESULTS_PER_PAGE,
            "total_items": 0, "total_pages": 0, "query_used": match_stage_query,
            "aggregation_type": group_stage["$group"].get("aggregation_type", {"$first": "unknown"}).get("$first")
        }

    total_pages = math.ceil(total_items / RESULTS_PER_PAGE)
    if page < 1: page = 1
    if page > total_pages and total_pages > 0: page = total_pages

    pipeline.append({"$sort": {"nomVernaculaire": 1}})
    skip_value = (page - 1) * RESULTS_PER_PAGE
    pipeline.append({"$skip": skip_value})
    pipeline.append({"$limit": RESULTS_PER_PAGE})

    aggregated_results = list(col.aggregate(pipeline))
    message_text = f"Page {page} sur {total_pages} ({total_items} espèces trouvées)\n"

    final_aggregation_type = group_stage["$group"].get("aggregation_type", {"$first": "unknown"}).get("$first")
    for item in aggregated_results:
        item["aggregation_type"] = final_aggregation_type

    return {
        "items": aggregated_results, "message": message_text, "page": page, "per_page": RESULTS_PER_PAGE,
        "total_items": total_items, "total_pages": total_pages, "query_used": match_stage_query,
        "aggregation_type": final_aggregation_type
    }
