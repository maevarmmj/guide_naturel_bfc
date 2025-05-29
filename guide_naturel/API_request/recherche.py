import math

RESULTS_PER_PAGE = 50
FUZZY_MATCH_THRESHOLD = 20  # Seuil d'acceptation de correction

conversations = {}

# Liste des questions du chatbot
QUESTIONS_FLOW = {
    "q_regne": {
        "text": "Commençons ! As-tu un règne que tu veux chercher ? (Animalia, Plantae ou Fungi)",
        "next_question_id": "q_groupe_taxo", "param_to_store": "regne", "skippable": True,
    },
    "q_groupe_taxo": {
        "text": "Quel groupe taxonomique simple t'intéresse ? (Oiseaux, Mammifères, Insectes, Plantes à fleurs...)",
        "next_question_id": "q2", "param_to_store": "groupeTaxoSimple", "skippable": True,
    },
    "q2": {
        "text": "Hum, je vois ! Et ce serait dans quel département ? (Le 21, 25, 70, 39, 58, 71, 90, ou 89)",
        "next_question_id": "q_commune", "param_to_store": "codeInseeDepartement", "skippable": True
    },
    "q_commune": {
        "text": "Si tu as une commune à spécifier, je suis preneuse ! (ex : Dijon, Besançon...)",
        "next_question_id": "q_nom_vern", "param_to_store": "commune", "skippable": True
    },
    "q_nom_vern": {
        "text": "Petite question compliquée : connais-tu le nom commun (ou vernaculaire) de l'espèce recherchée ? Ou une partie du nom ?",
        "next_question_id": "q_code_statut", "param_to_store": "nomVernaculaire", "skippable": True
    },
    "q_code_statut": {
        "text": "As-tu un code de statut d'observation spécifique en tête ? DD, LC, CR... Tu peux te renseigner sur les différents statuts de conservation qui existent !",
        "next_question_id": "results", "param_to_store": "codeStatut", "skippable": True,
    }
}

# Mots pour skip les questions
SKIP_KEYWORDS = ["passer", "skip", "je ne sais pas", "je sais pas", "non"]

# Valeurs pour fuzzy matching
KNOWN_VALUES_FOR_FUZZY_MATCHING = {
    "regne": ["Animalia", "Plantae", "Fungi"],
    "groupeTaxoSimple": ["Amphibiens et reptiles", "Autres", "Crabes, crevettes, cloportes et mille-pattes",
                         "Escargots et autres mollusques", "Insectes et araignées", "Mammifères", "Oiseaux", "Poissons",
                         "Champignons et lichens", "Plantes, mousses et fougères"],
    "codeStatut": ["EX", "EW", "CR", "EN", "VU", "NT", "LC", "DD", "NE"]
}


def build_mongo_match_stage(filters):
    # Conditions de filtrage fournies par l'utilisateur (initialisation) pour la base MongoDB
    match_query = {}

    # Si le filtre "regne" existe (si l'utilisateur l'a fourni) et s'il a une valeur
    if "regne" in filters and filters["regne"]:
        match_query["regne"] = {"$regex": f"^{filters['regne']}$", "$options": "i"} # On veut trouver les documents où le champ "regne" correspond à la valeur fournie par l'utilisateur
    # i : insensible à la casse

    if "groupeTaxoSimple" in filters and filters["groupeTaxoSimple"]:
        match_query["groupeTaxoSimple"] = {"$regex": f"^{filters['groupeTaxoSimple']}", "$options": "i"}

    if "codeInseeDepartement" in filters and filters["codeInseeDepartement"]:
        code_dept_str = filters["codeInseeDepartement"]

        try:
            code_dept_int = int(code_dept_str)
            match_query["codeInseeDepartement"] = code_dept_int

        except ValueError:
            print(f"Avertissement: Code département invalide '{code_dept_str}', ignoré.")
            pass

    if "commune" in filters and filters["commune"]:
        match_query["commune"] = {"$regex": f"^{filters['commune']}", "$options": "i"}

    if "nomVernaculaire" in filters and filters["nomVernaculaire"]:
        match_query["nomVernaculaire"] = {"$regex": filters['nomVernaculaire'], "$options": "i"}

    if "codeStatut" in filters and filters["codeStatut"]:
        match_query["codeStatut"] = {"$regex": f"^{filters['codeStatut']}$", "$options": "i"}

    return match_query

# LA fonction qui va interroger MongoDB
def get_results_from_db(filters, col, page=1):

    match_stage_query = build_mongo_match_stage(filters)

    departement_specifie = "codeInseeDepartement" in match_stage_query

    if not match_stage_query and not ("nomVernaculaire" in filters and filters["nomVernaculaire"]):
        return {"items": [], "message": "Veuillez spécifier au moins un critère de recherche",
                "page": page,
                "per_page": RESULTS_PER_PAGE,
                "total_items": 0,
                "total_pages": 0,
                "query_used": match_stage_query,
                "aggregation_type": "none"
                }

    pipeline = []

    if match_stage_query:
        pipeline.append({"$match": match_stage_query})

    group_id_key = "$nomScientifiqueRef"
    common_group_fields = {
        # On prend le $first nomVernaculaire, on le traitera en "N/A" dans $project
        "nomVernaculaireSource": {"$first": "$nomVernaculaire"},
        "regne": {"$first": "$regne"},
        "groupeTaxoSimple": {"$first": "$groupeTaxoSimple"},
        "statuts": {"$addToSet": "$codeStatut"},
        "totalObservationsEspece": {"$sum": "$nombreObservations"}
    }

    if departement_specifie:
        group_stage_content = {"_id": group_id_key, **common_group_fields,
                               "departements": {"$addToSet": "$codeInseeDepartement"}, "communesDetails": {
                "$addToSet": {"commune": "$commune", "departement": "$codeInseeDepartement"}}}
        aggregation_type_for_stage = "departement_specifique"
    else:
        group_stage_content = {"_id": group_id_key, **common_group_fields,
                               "departements": {"$addToSet": "$codeInseeDepartement"}}
        aggregation_type_for_stage = "nationale_sans_communes"

    pipeline.append({"$group": group_stage_content})

    # Étape de projection pour formater nomVernaculaire en "N/A" si besoin et préparer le tri
    project_stage = {
        "$project": {
            "_id": 0,
            "nomScientifiqueRef": "$_id",
            "nomVernaculaire": {"$ifNull": ["$nomVernaculaireSource", "N/A"]},  # Si null, mettre "N/A"
            "regne": 1,
            "groupeTaxoSimple": 1,
            "statuts": 1,
            "totalObservationsEspece": 1,
            "departements": 1,
            "communesDetails": {"$ifNull": ["$communesDetails", []]},
            "aggregation_type": aggregation_type_for_stage,
            "sort_priority_nomVernaculaire": {
                "$cond": [{"$eq": [{"$ifNull": ["$nomVernaculaireSource", "N/A"]}, "N/A"]}, 1, 0]
            }
        }
    }
    pipeline.append(project_stage)

    count_pipeline_after_group = [stage for stage in pipeline if
                                  "$skip" not in stage and "$limit" not in stage and "$sort" not in stage]
    count_pipeline_after_group.append({"$count": "total_items"})
    count_result = list(col.aggregate(count_pipeline_after_group))
    total_items = count_result[0]["total_items"] if count_result else 0

    if total_items == 0:
        return {"items": [], "message": "Désolée, je n'ai rien trouvé avec ces critères...", "page": page,
                "per_page": RESULTS_PER_PAGE, "total_items": 0, "total_pages": 0, "query_used": match_stage_query,
                "aggregation_type": aggregation_type_for_stage}

    total_pages = math.ceil(total_items / RESULTS_PER_PAGE)

    if page < 1:
        page = 1

    if page > total_pages and total_pages > 0:
        page = total_pages

    # Étape de tri
    pipeline.append({
        "$sort": {
            "sort_priority_nomVernaculaire": 1,  # Les N/A (valeur 1) en dernier
            "nomVernaculaire": 1  # Puis tri alphabétique sur le nom vernaculaire
        }
    })

    skip_value = (page - 1) * RESULTS_PER_PAGE
    pipeline.append({"$skip": skip_value})
    pipeline.append({"$limit": RESULTS_PER_PAGE})

    aggregated_results = list(col.aggregate(pipeline))
    message_text = f"Page {page} sur {total_pages} ({total_items} espèces trouvées)\n"
    return {"items": aggregated_results, "message": message_text, "page": page, "per_page": RESULTS_PER_PAGE,
            "total_items": total_items, "total_pages": total_pages, "query_used": match_stage_query,
            "aggregation_type": aggregation_type_for_stage}
