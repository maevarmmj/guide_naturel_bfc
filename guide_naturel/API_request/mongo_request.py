from collections import defaultdict
from pymongo.mongo_client import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.server_api import ServerApi
from typing import Collection, Dict, List
import pprint

# --- Constantes pour l'ordre et les couleurs des statuts IUCN ---
STATUS_INFO = {
    "Autre": {"order": 0, "color": "#B9DDBA", "full_name": "Autres (DD/Non spécifié)"},
    "LC": {"order": 1, "color": "#4CAF50", "full_name": "Préoccupation mineure"},
    "NT": {"order": 3, "color": "#45C4EB", "full_name": "Quasi menacée"},
    "VU": {"order": 4, "color": "#FBC02D", "full_name": "Vulnérable"},
    "EN": {"order": 5, "color": "#F57C00", "full_name": "En danger"},
    "CR": {"order": 6, "color": "#D32F2F", "full_name": "En danger critique"},
    "EW": {"order": 7, "color": "#616161", "full_name": "Éteinte à l'état sauvage"},
    "EX": {"order": 8, "color": "#424242", "full_name": "Éteinte"}
}

REGNE_COLORS = {
    'Animalia': '#29C9B7',
    'Plantae': '#2DA03E',
    'Fungi': '#A06E2D',
    'Sans Règne': '#757575'   
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
        "title": "Répartition des espèces par état de conservation (BFC)"
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

        final_output_by_department[dep_code] = [{
            "labels": labels_dep,
            "data": data_dep,
            "backgroundColor": background_colors_dep,
            "counts": counts_raw_dep,
            "title": f"Répartition des espèces par état de conservation ({dep_code})"
        }]

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

        final_output_by_department[dep_code] = [{
            "labels": labels_dep,
            "data": data_dep,
            "backgroundColor": background_colors_dep,
            "counts": counts_raw_dep,
            "title": f"Répartition des espèces par Règne ({dep_code})"
        }]

    # S'assurer que tous les départements demandés ont une entrée, même vide
    for dep in departements:
        if dep not in final_output_by_department:
            final_output_by_department[dep] = {
                "labels": [], "data": [], "backgroundColor": [], "counts": [],
                "title": f"Répartition des espèces par Règne"
            }

    return final_output_by_department


def species_by_regne_and_statut(col: Collection) -> List[Dict]:
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


def species_by_regne_and_statut_dep(col: Collection, dep: List[int]) -> Dict[int, List[Dict]]:
    """
    Compte le nombre d'espèces uniques par département, règne et codeStatut,
    et formate les résultats en un dictionnaire où chaque clé est un code de département,
    et la valeur est une liste de dictionnaires Chart.js (un par règne pour ce département).
    """
    pipeline = [
        {
            # Étape 1: Grouper par nom scientifique ET département pour obtenir
            # une entrée unique par espèce au sein de chaque département.
            # On prend le premier règne et codeStatut rencontrés pour cette espèce dans ce département.
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
            # Étape 2: Grouper les espèces uniques par leur département, règne et statut de conservation,
            # puis compter le nombre d'espèces dans chaque combinaison.
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
            # Étape 3: Reformater le document de sortie pour faciliter le traitement Python.
            "$project": {
                "_id": 0,
                "departement": "$_id.departement",
                "regne": "$_id.regne",
                "statut": "$_id.statut",
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            # Étape 4: Trier les résultats pour une sortie cohérente.
            "$sort": {"departement": 1, "regne": 1, "statut": 1}
        }
    ]

    resultats_aggregation = list(col.aggregate(pipeline))

    # Re-structuration des résultats pour faciliter le traitement:
    full_data_structure = defaultdict(lambda: defaultdict(lambda: {'statuts': defaultdict(int), 'total_regne': 0}))

    for res in resultats_aggregation:
        current_dep = res['departement']
        regne = _format_key(res['regne'], 'Sans Règne')
        statut_key_raw = res['statut']
        nombre = res['nombreEspeces']

        # Normalise la clé de statut pour la recherche dans STATUS_INFO
        effective_statut_key = 'Autre'
        if statut_key_raw in STATUS_INFO:
            effective_statut_key = statut_key_raw
        elif statut_key_raw is None or str(statut_key_raw).strip() == "" or _format_key(statut_key_raw,
                                                                                        'N/A Statut') == 'N/A Statut':
            effective_statut_key = 'Autre'  # Normalise les "N/A Statut" en "Autre"
        else:
            effective_statut_key = statut_key_raw  # Si c'est une autre valeur inattendue, on la garde

        full_data_structure[current_dep][regne]['statuts'][effective_statut_key] += nombre
        full_data_structure[current_dep][regne]['total_regne'] += nombre

    # Préparation du dictionnaire final pour Chart.js, structuré par département
    final_output_by_department = {}

    departments_to_process = sorted(full_data_structure.keys())

    for dep_code in departments_to_process:
        charts_for_this_department = []
        regnes_data_for_dep = full_data_structure.get(dep_code, {})

        # Itérer sur chaque règne pour créer un graphique séparé pour ce département
        sorted_regnes = sorted(regnes_data_for_dep.keys())

        if not sorted_regnes:
            charts_for_this_department.append({
                "labels": ["Aucune donnée"],
                "data": [100],
                "backgroundColor": ["#CCCCCC"],
                "counts": [0],
                "title": f"Statuts de conservation (Dép. {dep_code})",
                "legendLabel": "Aucune donnée"
            })
        else:
            for regne_name in sorted_regnes:
                regne_details = regnes_data_for_dep[regne_name]
                total_species_in_regne = regne_details['total_regne']
                statuts_counts = regne_details['statuts']

                processed_statuts_for_chart = []
                for statut_key, count in statuts_counts.items():
                    status_info = STATUS_INFO.get(statut_key, STATUS_INFO["Autre"])
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
                    labels.append(item['label_full'])
                    data.append(round(percentage, 2))  # Arrondir les pourcentages pour un affichage plus propre
                    background_colors.append(item['color'])
                    counts_raw.append(item['count'])

                charts_for_this_department.append({
                    "labels": labels,
                    "data": data,
                    "backgroundColor": background_colors,
                    "counts": counts_raw,
                    "title": f"État de conservation des espèces de {regne_name} ({dep_code})",
                    "legendLabel": f"État de conservation"
                })

        final_output_by_department[dep_code] = charts_for_this_department

    return final_output_by_department
