from collections import defaultdict
from pymongo.mongo_client import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.server_api import ServerApi
from typing import Collection, Dict, List
import pprint

# --- Constantes pour l'ordre et les couleurs des statuts IUCN ---
STATUS_INFO = {
    "Autre": {"order": 0, "color": "#9E9E9E", "full_name": "Autres (DD/Non spécifié)"},
    "LC": {"order": 1, "color": "#4CAF50", "full_name": "Préoccupation mineure"},
    "NT": {"order": 3, "color": "#0097A7", "full_name": "Quasi menacée"},
    "VU": {"order": 4, "color": "#FBC02D", "full_name": "Vulnérable"},
    "EN": {"order": 5, "color": "#F57C00", "full_name": "En danger"},
    "CR": {"order": 6, "color": "#D32F2F", "full_name": "En danger critique"},
    "EW": {"order": 7, "color": "#616161", "full_name": "Éteinte à l'état sauvage"},
    "EX": {"order": 8, "color": "#424242", "full_name": "Éteinte"}
}

REGNE_COLORS = {
    'Animalia': '#FF6384',      # Rouge/rose
    'Plantae': '#2DA03E',       # vert
    'Fungi': '#A06E2D',         # marron
    'Sans Règne': '#757575'      # Gris
}


# --- Fonctions utilitaires ---
def get_mongo_collection(uri: str, db_name: str, collection_name: str) -> Collection:
    """
    Établit une connexion à MongoDB et retourne l'objet Collection.
    """
    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client[db_name]
    return db[collection_name]


def _format_key(key, default_label: str = "Non spécifié"):
    """
    Formate une clé (règne, statut, groupe taxonomique) pour l'affichage,
    en remplaçant None par une étiquette par défaut.
    """
    if key is None:
        return default_label
    return str(key)


# --- Fonctions d'Agrégation (retournent les données structurées) ---
def species_by_code_statut(col: Collection) -> dict:
    """
    Compte le nombre d'espèces uniques par codeStatut sur l'ensemble de la base de données.
    Retourne les données formatées pour Chart.js.
    """
    pipeline = [
        {
            # Étape 1: Grouper par nom scientifique pour obtenir une entrée unique par espèce.
            # On prend le premier codeStatut rencontré pour cette espèce.
            "$group": {
                "_id": "$nomScientifiqueRef",
                "codeStatutSpecies": {"$first": "$codeStatut"}
            }
        },
        {
            # Étape 2: Grouper ces espèces uniques par leur codeStatut pour les compter.
            "$group": {
                "_id": "$codeStatutSpecies",
                "nombreEspeces": {"$sum": 1}
            }
        },
        {
            # Étape 3: Reformater le document de sortie
            "$project": {
                "_id": 0,
                "statut": "$_id",
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            # Étape 4 (Optionnel): Trier par statut pour la cohérence
            "$sort": {"statut": 1}
        }
    ]

    resultats_aggregation = list(col.aggregate(pipeline))

    # --- Post-traitement Python pour formater les données Chart.js ---
    chart_data_raw = []
    total_global_species = 0

    for res in resultats_aggregation:
        statut = _format_key(res['statut'], "Sans codeStatut")
        nombre = res['nombreEspeces']
        total_global_species += nombre

        # Mapper "Sans codeStatut" à "Autre" pour l'affichage et l'ordre/couleur
        display_statut_key = "Autre" if statut == "Sans codeStatut" else statut
        info = STATUS_INFO.get(display_statut_key, {"order": 999, "color": "#CCCCCC", "full_name": statut})

        chart_data_raw.append({
            "code": statut, # Code original du statut
            "display_label": info["full_name"], # Nom complet pour l'affichage
            "count": nombre,
            "color": info["color"],
            "sort_order": info["order"]
        })

    # Trier les statuts selon l'ordre défini
    sorted_data = sorted(chart_data_raw, key=lambda x: x["sort_order"])

    # Préparer le format final pour Chart.js
    labels = []
    data = [] # Pourcentages
    background_colors = []
    counts_raw = [] # Nombres bruts pour les tooltips

    for item in sorted_data:
        percentage = (item['count'] / total_global_species) * 100 if total_global_species > 0 else 0
        labels.append(f"{item['display_label']}")  # {f" ({item['code']})" if item['code'] != "Sans codeStatut" else ""}
        data.append(percentage)
        background_colors.append(item['color'])
        counts_raw.append(item['count'])

    return {
        "labels": labels,
        "data": data,
        "backgroundColor": background_colors,
        "counts": counts_raw, # Nombres bruts
        "title": "Répartition des espèces par codeStatut (BFC)"
    }


# --- Nouvelle fonction d'agrégation globale par règne ---
def species_by_regne(col: Collection) -> dict:
    """
    Compte le nombre d'espèces uniques par règne sur l'ensemble de la base de données.
    Retourne les données formatées pour Chart.js.
    """
    pipeline = [
        {
            # Étape 1: Grouper par nom scientifique pour obtenir une entrée unique par espèce.
            # On récupère le premier règne associé à cette espèce.
            "$group": {
                "_id": "$nomScientifiqueRef",
                "regneSpecies": {"$first": "$regne"}
            }
        },
        {
            # Étape 2: Grouper ces espèces uniques par leur règne et compter le nombre d'espèces.
            "$group": {
                "_id": "$regneSpecies",
                "nombreEspeces": {"$sum": 1}
            }
        },
        {
            # Étape 3: Reformater le document de sortie pour faciliter le traitement Python
            "$project": {
                "_id": 0,
                "regne": "$_id",  # Renomme _id (qui est le règne) en 'regne'
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            # Étape 4 (Optionnel): Trier les résultats par règne pour une sortie cohérente
            "$sort": {"regne": 1}
        }
    ]

    resultats_aggregation = list(col.aggregate(pipeline))

    # --- Post-traitement Python pour formater les données pour Chart.js ---
    chart_data_raw = []
    total_global_species = 0

    for res in resultats_aggregation:
        # Utilisez _format_key pour gérer les valeurs None de 'regne'
        regne = _format_key(res['regne'], "Sans règne")  # 'Sans règne' sera l'étiquette par défaut
        nombre = res['nombreEspeces']
        total_global_species += nombre

        chart_data_raw.append({
            "label": regne,  # Le label sera le nom du règne (ou 'Sans règne')
            "count": nombre,
            "color": REGNE_COLORS.get(regne, '#CCCCCC')  # Récupère la couleur, ou gris par défaut
        })

    # Trier les données pour le graphique (ici alphabétiquement par label)
    # Si vous avez un ordre spécifique pour les règnes, vous pouvez ajouter
    # un "order" comme dans STATUS_INFO et trier dessus.
    sorted_data = sorted(chart_data_raw, key=lambda x: x["label"])

    # Préparer le format final que votre fonction `updateChart` JavaScript attend
    labels = []
    data = []  # Pourcentages
    background_colors = []
    counts_raw = []  # Nombres bruts pour les tooltips

    for item in sorted_data:
        percentage = (item['count'] / total_global_species) * 100 if total_global_species > 0 else 0
        labels.append(item['label'])
        data.append(percentage)
        background_colors.append(item['color'])
        counts_raw.append(item['count'])

    return {
        "labels": labels,
        "data": data,
        "backgroundColor": background_colors,
        "counts": counts_raw,  # Nombres bruts
        "title": "Répartition des espèces par Règne (BFC)" # Titre pour le graphique
    }


def species_by_code_statut_dep(col: Collection, departements: list) -> dict:
    """
    Compte le nombre d'espèces uniques par codeStatut pour chaque département donné.
    Retourne un dictionnaire où chaque clé est un code de département et la valeur
    est un dictionnaire formaté pour Chart.js pour ce département.
    """
    pipeline = [
        {
            "$match": {"codeInseeDepartement": {"$in": departements}}
        },
        {
            # Étape 1: Grouper par nom scientifique ET département pour obtenir
            # une entrée unique par espèce au sein de chaque département.
            # On prend le premier codeStatut rencontré pour cette espèce dans ce département.
            "$group": {
                "_id": {
                    "nomScientifiqueRef": "$nomScientifiqueRef",
                    "codeInseeDepartement": "$codeInseeDepartement"
                },
                "codeStatutSpecies": {"$first": "$codeStatut"}
            }
        },
        {
            # Étape 2: Grouper ces espèces uniques par leur codeStatut ET par département pour les compter.
            "$group": {
                "_id": {
                    "departement": "$_id.codeInseeDepartement",
                    "statut": "$codeStatutSpecies"
                },
                "nombreEspeces": {"$sum": 1}
            }
        },
        {
            # Étape 3: Reformater le document de sortie de l'agrégation
            "$project": {
                "_id": 0,
                "departement": "$_id.departement",
                "statut": "$_id.statut",
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            # Étape 4 (Optionnel): Trier pour un traitement Python plus facile si nécessaire
            "$sort": {"departement": 1, "statut": 1}
        }
    ]

    resultats_aggregation = list(col.aggregate(pipeline))

    # --- Post-traitement Python pour formater les données Chart.js par département ---

    # D'abord, regrouper les données brutes par département
    data_per_department_raw = defaultdict(list)
    for res in resultats_aggregation:
        dep = res['departement']
        statut_brut = res['statut']
        nombre = res['nombreEspeces']
        data_per_department_raw[dep].append({
            "statut_brut": statut_brut,
            "nombreEspeces": nombre
        })

    # Maintenant, traiter chaque département pour formater sa sortie Chart.js
    final_output_by_department = {}

    for dep_code, raw_items in data_per_department_raw.items():
        chart_data_raw_dep = []
        total_especes_departement = 0

        for item in raw_items:
            statut = _format_key(item['statut_brut'], "Sans codeStatut")
            nombre = item['nombreEspeces']
            total_especes_departement += nombre

            display_statut_key = "Autre" if statut == "Sans codeStatut" else statut
            info = STATUS_INFO.get(display_statut_key, {"order": 999, "color": "#CCCCCC", "full_name": statut})

            chart_data_raw_dep.append({
                "code": statut,
                "display_label": info["full_name"],
                "count": nombre,
                "color": info["color"],
                "sort_order": info["order"]
            })

        # Trier les statuts selon l'ordre défini pour ce département
        sorted_data_dep = sorted(chart_data_raw_dep, key=lambda x: x["sort_order"])

        # Préparer le format final pour Chart.js pour ce département
        labels_dep = []
        data_dep = []  # Pourcentages
        background_colors_dep = []
        counts_raw_dep = []

        for s_item in sorted_data_dep:
            percentage = (s_item['count'] / total_especes_departement) * 100 if total_especes_departement > 0 else 0
            # Vous pouvez choisir d'inclure ou non le code dans le label ici
            labels_dep.append(f"{s_item['display_label']}")
            data_dep.append(round(percentage, 2)) # Arrondir les pourcentages peut être une bonne idée
            background_colors_dep.append(s_item['color'])
            counts_raw_dep.append(s_item['count'])

        final_output_by_department[dep_code] = {
            "labels": labels_dep,
            "data": data_dep,
            "backgroundColor": background_colors_dep,
            "counts": counts_raw_dep,
            "title": f"Répartition des espèces par codeStatut"
            # Vous pouvez ajouter d'autres clés si nécessaire, comme le total_especes_departement
            # "totalEspeces": total_especes_departement
        }

    # S'assurer que tous les départements demandés ont une entrée, même vide
    for dep in departements:
        if dep not in final_output_by_department:
            final_output_by_department[dep] = {
                "labels": [], "data": [], "backgroundColor": [], "counts": [],
                "title": f"Répartition des espèces par codeStatut"
            }

    return final_output_by_department


def species_by_regne_dep(col: Collection, departements: list) -> dict:
    """
    Compte le nombre d'espèces uniques par règne pour chaque département donné.
    Retourne un dictionnaire où chaque clé est un code de département et la valeur
    est un dictionnaire formaté pour Chart.js pour ce département.
    """
    pipeline = [
        {
            "$match": {"codeInseeDepartement": {"$in": departements}}
        },
        {
            # Étape 1: Grouper par nom scientifique ET département pour obtenir
            # une entrée unique par espèce au sein de chaque département.
            # On prend le premier règne rencontré pour cette espèce dans ce département.
            "$group": {
                "_id": {
                    "nomScientifiqueRef": "$nomScientifiqueRef",
                    "codeInseeDepartement": "$codeInseeDepartement"
                },
                "regneSpecies": {"$first": "$regne"} # Assurez-vous que le champ est bien "$regne"
            }
        },
        {
            # Étape 2: Grouper ces espèces uniques par leur règne ET par département pour les compter.
            "$group": {
                "_id": {
                    "departement": "$_id.codeInseeDepartement",
                    "regne": "$regneSpecies"
                },
                "nombreEspeces": {"$sum": 1}
            }
        },
        {
            # Étape 3: Reformater le document de sortie de l'agrégation
            "$project": {
                "_id": 0,
                "departement": "$_id.departement",
                "regne": "$_id.regne",
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            # Étape 4 (Optionnel): Trier pour un traitement Python plus facile si nécessaire
            "$sort": {"departement": 1, "regne": 1}
        }
    ]

    resultats_aggregation = list(col.aggregate(pipeline))

    # --- Post-traitement Python pour formater les données Chart.js par département ---

    # D'abord, regrouper les données brutes par département
    data_per_department_raw = defaultdict(list)
    for res in resultats_aggregation:
        dep = res['departement']
        regne_brut = res['regne']
        nombre = res['nombreEspeces']
        data_per_department_raw[dep].append({
            "regne_brut": regne_brut,
            "nombreEspeces": nombre
        })

    # Maintenant, traiter chaque département pour formater sa sortie Chart.js
    final_output_by_department = {}

    for dep_code, raw_items in data_per_department_raw.items():
        chart_data_raw_dep = []
        total_especes_departement = 0

        for item in raw_items:
            regne_nom = _format_key(item['regne_brut'], "Sans règne")
            nombre = item['nombreEspeces']
            total_especes_departement += nombre

            # Si vous utilisez une structure REGNE_INFO avec "order" et "full_name":
            # info = REGNE_INFO.get(regne_nom, {"order": 999, "color": "#CCCCCC", "full_name": regne_nom})
            # chart_data_raw_dep.append({
            #     "label": info["full_name"],
            #     "count": nombre,
            #     "color": info["color"],
            #     "sort_order": info["order"]
            # })
            # Sinon, avec un simple REGNE_COLORS:
            chart_data_raw_dep.append({
                "label": regne_nom,
                "count": nombre,
                "color": REGNE_COLORS.get(regne_nom, '#CCCCCC') # Couleur par défaut si non trouvé
            })


        # Trier les règnes (alphabétiquement par label si REGNE_INFO n'est pas utilisé pour un tri par 'order')
        # Si REGNE_INFO est utilisé:
        # sorted_data_dep = sorted(chart_data_raw_dep, key=lambda x: x["sort_order"])
        # Sinon (tri alphabétique) :
        sorted_data_dep = sorted(chart_data_raw_dep, key=lambda x: x["label"])


        # Préparer le format final pour Chart.js pour ce département
        labels_dep = []
        data_dep = []  # Pourcentages
        background_colors_dep = []
        counts_raw_dep = []

        for s_item in sorted_data_dep:
            percentage = (s_item['count'] / total_especes_departement) * 100 if total_especes_departement > 0 else 0
            labels_dep.append(s_item['label'])
            data_dep.append(round(percentage, 2)) # Arrondir les pourcentages
            background_colors_dep.append(s_item['color'])
            counts_raw_dep.append(s_item['count'])

        final_output_by_department[dep_code] = {
            "labels": labels_dep,
            "data": data_dep,
            "backgroundColor": background_colors_dep,
            "counts": counts_raw_dep,
            "title": f"Répartition des espèces par Règne"
            # "totalEspeces": total_especes_departement # Optionnel
        }

    # S'assurer que tous les départements demandés ont une entrée, même vide
    for dep in departements:
        if dep not in final_output_by_department:
            final_output_by_department[dep] = {
                "labels": [], "data": [], "backgroundColor": [], "counts": [],
                "title": f"Répartition des espèces par Règne"
            }

    return final_output_by_department


def species_by_regne_and_statut_global(col: Collection) -> List[Dict]:
    """
    Compte le nombre d'espèces uniques par règne et codeStatut sur l'ensemble de la base de données,
    et formate les résultats en une liste de dictionnaires Chart.js (un par règne).
    """
    pipeline = [
        {
            # Étape 1: Grouper par nom scientifique unique pour s'assurer de ne compter
            # chaque espèce qu'une seule fois à l'échelle globale.
            # On prend le premier 'regne' et 'codeStatut' rencontrés pour cette espèce.
            "$group": {
                "_id": "$nomScientifiqueRef",
                "regneSpecies": {"$first": "$regne"},
                "codeStatutSpecies": {"$first": "$codeStatut"}
            }
        },
        {
            # Étape 2: Grouper les espèces uniques par leur règne et leur statut de conservation,
            # puis compter le nombre d'espèces dans chaque combinaison.
            "$group": {
                "_id": {
                    "regne": "$regneSpecies",
                    "statut": "$codeStatutSpecies"
                },
                "nombreEspeces": {"$sum": 1}
            }
        },
        {
            # Étape 3: Reformater le document de sortie pour faciliter le traitement Python.
            "$project": {
                "_id": 0,
                "regne": "$_id.regne",
                "statut": "$_id.statut",
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            # Étape 4: Trier les résultats pour une sortie cohérente.
            "$sort": {"regne": 1, "statut": 1}
        }
    ]

    resultats_aggregation = list(col.aggregate(pipeline))

    # Re-structuration des résultats pour faciliter le traitement par règne
    # {regne: {statut: count, ..., 'total_regne': X}}
    regne_status_counts = defaultdict(lambda: {'statuts': defaultdict(int), 'total_regne': 0})

    for res in resultats_aggregation:
        regne = _format_key(res['regne'], 'Sans Règne')
        statut_key_raw = res['statut']
        nombre = res['nombreEspeces']

        # Normalise la clé de statut pour la recherche dans STATUS_INFO
        effective_statut_key = 'Autre'
        if statut_key_raw in STATUS_INFO:
            effective_statut_key = statut_key_raw
        elif statut_key_raw is None or str(statut_key_raw).strip() == "" or _format_key(statut_key_raw, 'N/A Statut') == 'N/A Statut':
            effective_statut_key = 'Autre' # Normalise les "N/A Statut" en "Autre"
        else:
            effective_statut_key = statut_key_raw # Si c'est une autre valeur inattendue, on la garde ou la map à 'Autre'

        regne_status_counts[regne]['statuts'][effective_statut_key] += nombre
        regne_status_counts[regne]['total_regne'] += nombre

    # Préparation des données pour Chart.js
    charts_output = []

    # Iterer sur chaque règne pour créer un graphique séparé
    # On trie les règnes pour une sortie cohérente (ex: alphabétique)
    sorted_regnes = sorted(regne_status_counts.keys())

    for regne_name in sorted_regnes:
        regne_details = regne_status_counts[regne_name]
        total_species_in_regne = regne_details['total_regne']
        statuts_counts = regne_details['statuts']

        # Préparer les données de statut pour ce règne, en les triant selon STATUS_INFO['order']
        processed_statuts_for_chart = []
        for statut_key, count in statuts_counts.items():
            status_info = STATUS_INFO.get(statut_key, STATUS_INFO["Autre"]) # Fallback to Autre
            processed_statuts_for_chart.append({
                "label_full": status_info['full_name'],
                "label_short": statut_key,
                "count": count,
                "color": status_info['color'],
                "order": status_info['order']
            })

        # Trier les statuts pour le graphique
        sorted_statuts_for_chart = sorted(processed_statuts_for_chart, key=lambda x: x["order"])

        labels = []
        data = []  # Pourcentages
        background_colors = []
        counts_raw = []  # Nombres bruts

        for item in sorted_statuts_for_chart:
            percentage = (item['count'] / total_species_in_regne) * 100 if total_species_in_regne > 0 else 0
            labels.append(item['label_full']) # Utilisez le nom complet pour le label du graphique
            data.append(percentage)
            background_colors.append(item['color'])
            counts_raw.append(item['count'])

        charts_output.append({
            "labels": labels,
            "data": data,
            "backgroundColor": background_colors,
            "counts": counts_raw,
            "title": f"Statuts de conservation des espèces de {regne_name} (BFC)",
            "legendLabel": f"Statuts de conservation"
        })

    return charts_output


def species_by_regne_and_statut_dep(col: Collection, dep: int) -> List[Dict]:
    """
    Compte le nombre d'espèces uniques par règne et codeStatut pour un département donné,
    et formate les résultats en une liste de dictionnaires Chart.js (un par règne).
    """
    pipeline = [
        {
            "$match": {"codeInseeDepartement": dep}
        },
        {
            "$group": {
                "_id": {
                    "nomScientifiqueRef": "$nomScientifiqueRef",
                    "codeInseeDepartement": "$codeInseeDepartement"
                },
                "regneSpecies": {"$first": "$regne"},
                "codeStatutSpecies": {"$first": "$codeStatut"}
            }
        },
        {
            "$group": {
                "_id": {
                    "departement": "$_id.codeInseeDepartement",
                    "regne": "$regneSpecies",
                    "statut": "$codeStatutSpecies"
                },
                "nombreEspeces": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "departement": "$_id.departement",
                "regne": "$_id.regne",
                "statut": "$_id.statut",
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            "$sort": {"departement": 1, "regne": 1, "statut": 1}
        }
    ]

    resultats_aggregation = list(col.aggregate(pipeline))

    # Re-structuration des résultats pour faciliter le traitement par règne
    # {departement: {regne: {statut: count, ..., 'total_regne': X}}}
    department_regne_status_counts = defaultdict(lambda: defaultdict(lambda: {'statuts': defaultdict(int), 'total_regne': 0}))

    for res in resultats_aggregation:
        current_dep = res['departement']
        regne = _format_key(res['regne'], 'Sans Règne')
        statut_key_raw = res['statut'] # Garde la clé brute pour la correspondance STATUS_INFO
        nombre = res['nombreEspeces']

        # Map 'N/A Statut' ou autres valeurs non définies à 'Autre' pour la lookup dans STATUS_INFO
        # Mais garde la clé brute pour stocker si nécessaire, ou standardise-la dès le début.
        # Ici, on normalise la clé pour la recherche dans STATUS_INFO
        effective_statut_key = 'Autre'
        if statut_key_raw in STATUS_INFO:
            effective_statut_key = statut_key_raw
        elif statut_key_raw is None or str(statut_key_raw).strip() == "" or _format_key(statut_key_raw, 'N/A Statut') == 'N/A Statut':
            effective_statut_key = 'Autre' # Normalise les "N/A Statut" en "Autre"
        else:
            effective_statut_key = statut_key_raw # Si c'est une autre valeur inattendue, on la garde ou la map à 'Autre'

        department_regne_status_counts[current_dep][regne]['statuts'][effective_statut_key] += nombre
        department_regne_status_counts[current_dep][regne]['total_regne'] += nombre

    # Préparation des données pour Chart.js
    charts_output = []

    # Vérifie si le département est présent dans les résultats
    if dep not in department_regne_status_counts:
        return [] # Aucun résultat pour ce département

    regnes_data_for_dep = department_regne_status_counts[dep]

    # Iterer sur chaque règne pour créer un graphique séparé
    # On trie les règnes pour une sortie cohérente (ex: alphabétique)
    sorted_regnes = sorted(regnes_data_for_dep.keys())

    for regne_name in sorted_regnes:
        regne_details = regnes_data_for_dep[regne_name]
        total_species_in_regne = regne_details['total_regne']
        statuts_counts = regne_details['statuts']

        # Préparer les données de statut pour ce règne, en les triant selon STATUS_INFO['order']
        processed_statuts_for_chart = []
        for statut_key, count in statuts_counts.items():
            status_info = STATUS_INFO.get(statut_key, STATUS_INFO["Autre"]) # Fallback to Autre
            processed_statuts_for_chart.append({
                "label_full": status_info['full_name'],
                "label_short": statut_key,
                "count": count,
                "color": status_info['color'],
                "order": status_info['order']
            })

        # Trier les statuts pour le graphique
        sorted_statuts_for_chart = sorted(processed_statuts_for_chart, key=lambda x: x["order"])

        labels = []
        data = []  # Pourcentages
        background_colors = []
        counts_raw = []  # Nombres bruts

        for item in sorted_statuts_for_chart:
            percentage = (item['count'] / total_species_in_regne) * 100 if total_species_in_regne > 0 else 0
            labels.append(item['label_full']) # Utilisez le nom complet pour le label du graphique
            data.append(percentage)
            background_colors.append(item['color'])
            counts_raw.append(item['count'])

        charts_output.append({
            "labels": labels,
            "data": data,
            "backgroundColor": background_colors,
            "counts": counts_raw,
            "title": f"Statuts de conservation des espèces de {regne_name} (Dép. {dep})",
            "legendLabel": f"Statuts de conservation ({regne_name})" # Utile pour la légende
        })

    return charts_output


TAXO_GROUP_PALETTE = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
]


def species_by_regne_taxogroup_global(col: Collection) -> List[Dict]:
    """
    Compte le nombre d'espèces uniques par règne et groupe taxonomique simple
    sur l'ensemble de la base de données (globalement), et formate les résultats
    en une liste de dictionnaires Chart.js (un par règne).
    """
    pipeline = [
        {
            # Étape 1: Grouper par nom scientifique unique pour s'assurer de ne compter
            # chaque espèce qu'une seule fois à l'échelle globale.
            # On prend le premier 'regne' et 'groupeTaxoSimple' rencontrés pour cette espèce.
            "$group": {
                "_id": "$nomScientifiqueRef",
                "regneSpecies": {"$first": "$regne"},
                "groupeTaxoSimpleSpecies": {"$first": "$groupeTaxoAvance"},
            }
        },
        {
            # Étape 2: Grouper les espèces uniques par leur règne et leur groupe taxonomique,
            # puis compter le nombre d'espèces dans chaque combinaison.
            "$group": {
                "_id": {
                    "regne": "$regneSpecies",
                    "groupeTaxoSimple": "$groupeTaxoSimpleSpecies",
                },
                "nombreEspeces": {"$sum": 1}
            }
        },
        {
            # Étape 3: Reformater le document de sortie pour faciliter le traitement Python.
            "$project": {
                "_id": 0,
                "regne": "$_id.regne",
                "groupeTaxoSimple": "$_id.groupeTaxoSimple",
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            # Étape 4: Trier les résultats pour une sortie cohérente.
            "$sort": {"regne": 1, "groupeTaxoSimple": 1}
        }
    ]

    resultats_aggregation = list(col.aggregate(pipeline))

    # Re-structuration des résultats pour faciliter le traitement par règne
    # {regne: {groupe_taxo_simple: count, ..., 'total_regne': X}}
    regne_taxo_counts = defaultdict(lambda: {'groupes_taxo': defaultdict(int), 'total_regne': 0})

    for res in resultats_aggregation:
        regne = _format_key(res['regne'], 'Sans Règne')
        groupe_taxo = _format_key(res['groupeTaxoSimple'], 'Autres Groupes Taxo') # Nom par défaut si manquant
        nombre = res['nombreEspeces']

        regne_taxo_counts[regne]['groupes_taxo'][groupe_taxo] += nombre
        regne_taxo_counts[regne]['total_regne'] += nombre

    # Préparation des données pour Chart.js
    charts_output = []

    # Filtrer les règnes qui sont intéressants (Animalia, Fungi, Plantae) et les trier
    target_regnes_order = ["Animalia", "Fungi", "Plantae"] # Ordre désiré pour les charts

    # On s'assure d'inclure uniquement les règnes pour lesquels nous avons des données
    # et de les traiter dans l'ordre défini.
    available_regnes = [r for r in target_regnes_order if r in regne_taxo_counts]
    # Si d'autres règnes existent dans les données et que vous voulez les inclure,
    # ajoutez une étape pour les trier et les ajouter après les principaux
    other_regnes = sorted([r for r in regne_taxo_counts.keys() if r not in target_regnes_order])
    final_regnes_to_process = available_regnes + other_regnes


    for regne_name in final_regnes_to_process:
        regne_details = regne_taxo_counts[regne_name]
        total_species_in_regne = regne_details['total_regne']
        taxo_groups_counts = regne_details['groupes_taxo']

        # Préparer les données pour ce règne spécifique
        processed_taxo_groups_for_chart = []
        # Utiliser un index pour cycler les couleurs de la palette
        color_idx = 0
        for group_name, count in taxo_groups_counts.items():
            color = TAXO_GROUP_PALETTE[color_idx % len(TAXO_GROUP_PALETTE)]
            color_idx += 1

            processed_taxo_groups_for_chart.append({
                "label": group_name,
                "count": count,
                "color": color
            })

        # Trier les groupes taxonomiques (ex: par nombre d'espèces décroissant ou alphabétiquement)
        # Ici, tri alphabétique des labels pour une cohérence.
        sorted_taxo_groups_for_chart = sorted(processed_taxo_groups_for_chart, key=lambda x: x["label"])

        labels = []
        data = []  # Pourcentages
        background_colors = []
        counts_raw = []  # Nombres bruts

        for item in sorted_taxo_groups_for_chart:
            percentage = (item['count'] / total_species_in_regne) * 100 if total_species_in_regne > 0 else 0
            labels.append(item['label'])
            data.append(percentage)
            background_colors.append(item['color'])
            counts_raw.append(item['count'])

        charts_output.append({
            "labels": labels,
            "data": data,
            "backgroundColor": background_colors,
            "counts": counts_raw,
            "title": f"Répartition des espèces par groupe taxonomique ({regne_name}, Global)", # Titre global
            "legendLabel": f"Groupes taxonomiques ({regne_name})"
        })

    return charts_output


def species_by_regne_taxogroup(col: Collection, dep: int) -> List[Dict]:
    """
    Compte le nombre d'espèces uniques par règne et groupe taxonomique simple
    pour un département donné, et formate les résultats en une liste de dictionnaires
    Chart.js (un par règne).
    """
    pipeline = [
        {
            "$match": {"codeInseeDepartement": dep}
        },
        {
            "$group": {
                "_id": {
                    "nomScientifiqueRef": "$nomScientifiqueRef",
                    "codeInseeDepartement": "$codeInseeDepartement"
                },
                "regneSpecies": {"$first": "$regne"},
                "groupeTaxoSimpleSpecies": {"$first": "$groupeTaxoAvance"},
            }
        },
        {
            "$group": {
                "_id": {
                    "regne": "$regneSpecies",
                    "groupeTaxoSimple": "$groupeTaxoSimpleSpecies",
                },
                "nombreEspeces": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "regne": "$_id.regne",
                "groupeTaxoSimple": "$_id.groupeTaxoSimple",
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            "$sort": {"regne": 1, "groupeTaxoSimple": 1}
        }
    ]

    resultats_aggregation = list(col.aggregate(pipeline))

    # Re-structuration des résultats pour faciliter le traitement par règne
    # {regne: {groupe_taxo_simple: count, ..., 'total_regne': X}}
    regne_taxo_counts = defaultdict(lambda: {'groupes_taxo': defaultdict(int), 'total_regne': 0})

    for res in resultats_aggregation:
        regne = _format_key(res['regne'], 'Sans Règne')
        groupe_taxo = _format_key(res['groupeTaxoSimple'], 'Autres Groupes Taxo') # Nom par défaut si manquant
        nombre = res['nombreEspeces']

        regne_taxo_counts[regne]['groupes_taxo'][groupe_taxo] += nombre
        regne_taxo_counts[regne]['total_regne'] += nombre

    # Préparation des données pour Chart.js
    charts_output = []

    # Filtrer les règnes qui sont intéressants (Animalia, Fungi, Plantae) et les trier
    # Si vous voulez tous les règnes, utilisez `sorted(regne_taxo_counts.keys())`
    # Sinon, spécifiez l'ordre voulu
    target_regnes_order = ["Animalia", "Fungi", "Plantae"] # Ordre désiré pour les charts

    # On s'assure d'inclure uniquement les règnes pour lesquels nous avons des données
    # et de les traiter dans l'ordre défini.
    available_regnes = [r for r in target_regnes_order if r in regne_taxo_counts]
    # Si d'autres règnes existent dans les données et que vous voulez les inclure,
    # ajoutez une étape pour les trier et les ajouter après les principaux
    other_regnes = sorted([r for r in regne_taxo_counts.keys() if r not in target_regnes_order])
    final_regnes_to_process = available_regnes + other_regnes


    for regne_name in final_regnes_to_process:
        regne_details = regne_taxo_counts[regne_name]
        total_species_in_regne = regne_details['total_regne']
        taxo_groups_counts = regne_details['groupes_taxo']

        # Préparer les données pour ce règne spécifique
        processed_taxo_groups_for_chart = []
        # Utiliser un index pour cycler les couleurs de la palette
        color_idx = 0
        for group_name, count in taxo_groups_counts.items():
            # Vous pouvez utiliser TAXO_GROUP_COLORS.get(group_name, TAXO_GROUP_PALETTE[color_idx])
            # si vous avez des couleurs spécifiques pour certains groupes.
            color = TAXO_GROUP_PALETTE[color_idx % len(TAXO_GROUP_PALETTE)]
            color_idx += 1

            processed_taxo_groups_for_chart.append({
                "label": group_name,
                "count": count,
                "color": color
            })

        # Trier les groupes taxonomiques (ex: par nombre d'espèces décroissant ou alphabétiquement)
        # Ici, tri alphabétique des labels pour une cohérence.
        sorted_taxo_groups_for_chart = sorted(processed_taxo_groups_for_chart, key=lambda x: x["label"])

        labels = []
        data = []  # Pourcentages
        background_colors = []
        counts_raw = []  # Nombres bruts

        for item in sorted_taxo_groups_for_chart:
            percentage = (item['count'] / total_species_in_regne) * 100 if total_species_in_regne > 0 else 0
            labels.append(item['label'])
            data.append(percentage)
            background_colors.append(item['color'])
            counts_raw.append(item['count'])

        charts_output.append({
            "labels": labels,
            "data": data,
            "backgroundColor": background_colors,
            "counts": counts_raw,
            "title": f"Répartition des espèces par groupe taxonomique ({regne_name}, Dép. {dep})",
            "legendLabel": f"Groupes taxonomiques ({regne_name})"
        })

    return charts_output


def count_species_by_regne_taxogroup_simple_advanced(col: Collection, dep: int) -> tuple[dict, int]:
    """
    Compte le nombre d'espèces uniques par règne, groupe taxonomique simple et groupe taxonomique avancé
    pour un département donné.
    Retourne un tuple: (dictionnaire structuré avec les résultats, total d'espèces pour le département).
    """
    pipeline = [
        {
            "$match": {"codeInseeDepartement": dep}
        },
        {
            "$group": {
                "_id": {
                    "nomScientifiqueRef": "$nomScientifiqueRef",
                    "codeInseeDepartement": "$codeInseeDepartement"
                },
                "regneSpecies": {"$first": "$regne"},
                "groupeTaxoSimpleSpecies": {"$first": "$groupeTaxoSimple"},
                "groupeTaxoAvanceSpecies": {"$first": "$groupeTaxoAvance"}
            }
        },
        {
            "$group": {
                "_id": {
                    "regne": "$regneSpecies",
                    "groupeTaxoSimple": "$groupeTaxoSimpleSpecies",
                    "groupeTaxoAvance": "$groupeTaxoAvanceSpecies"
                },
                "nombreEspeces": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "regne": "$_id.regne",
                "groupeTaxoSimple": "$_id.groupeTaxoSimple",
                "groupeTaxoAvance": "$_id.groupeTaxoAvance",
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            "$sort": {"regne": 1, "groupeTaxoSimple": 1, "groupeTaxoAvance": 1}
        }
    ]

    resultats_aggregation = list(col.aggregate(pipeline))

    data_structure = {}
    total_especes_departement = 0

    for res in resultats_aggregation:
        regne = _format_key(res['regne'], 'N/A Règne')
        groupe_simple = _format_key(res['groupeTaxoSimple'], 'N/A Groupe Taxo Simple')
        groupe_avance = _format_key(res['groupeTaxoAvance'], 'N/A Groupe Taxo Avancé')
        nombre = res['nombreEspeces']

        if regne not in data_structure:
            data_structure[regne] = {'total_regne': 0, 'groupes_simple': {}}

        if groupe_simple not in data_structure[regne]['groupes_simple']:
            data_structure[regne]['groupes_simple'][groupe_simple] = {'total_groupe_simple': 0, 'groupes_avance': {}}

        data_structure[regne]['groupes_simple'][groupe_simple]['groupes_avance'][groupe_avance] = nombre

        data_structure[regne]['groupes_simple'][groupe_simple]['total_groupe_simple'] += nombre
        data_structure[regne]['total_regne'] += nombre
        total_especes_departement += nombre

    return data_structure, total_especes_departement


# --- Bloc d'exécution principal ---

if __name__ == '__main__':
    uri = "mongodb+srv://guest:guestpass@big-data.640be.mongodb.net/?retryWrites=true&w=majority&appName=Big-Data"
    db_name = 'LeGuideNaturel'
    collection_name = 'Nature'

    collection = None
    client = None  # Initialiser client à None

    try:
        # Récupérer la collection (le client est inclus dans l'objet collection via son attribut client)
        collection = get_mongo_collection(uri, db_name, collection_name)
        client = collection.database.client  # Récupérer le client pour le fermer plus tard

        departements_a_analyser = [21, 25, 39, 58, 71, 89, 90]

        # Test de chaque fonction et affichage des résultats
        print("\n--- Analyse par codeStatut pour plusieurs départements ---")
        results_statut = species_by_regne_dep(col=collection, departements=departements_a_analyser)
        print(results_statut)


    except Exception as e:
        print(f"Une erreur inattendue est survenue: {e}")
    finally:
        if client:
            client.close()
            print("\nConnexion à MongoDB fermée.")