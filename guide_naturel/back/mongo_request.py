from pymongo.mongo_client import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.server_api import ServerApi
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
    # Pour les statuts, on veut que None devienne une étiquette spécifique avant le mapping
    # afin que la logique de traitement puisse l'identifier.
    # On le mappera ensuite à "Autre" pour l'affichage final.
    if key is None:
        return "Sans codeStatut" # Étiquette interne pour les statuts non spécifiés
    return str(key)


# --- Fonctions d'Agrégation (retournent les données structurées) ---

def count_species_by_code_statut(col: Collection, departements: list) -> dict:
    """
    Compte le nombre d'espèces uniques par codeStatut pour chaque département donné.
    Retourne un dictionnaire structuré avec les résultats.
    """
    pipeline = [
        {
            "$match": {"codeInseeDepartement": {"$in": departements}}
        },
        {
            "$group": {
                "_id": {
                    "nomScientifiqueRef": "$nomScientifiqueRef",
                    "codeInseeDepartement": "$codeInseeDepartement"
                },
                "codeStatutSpecies": {"$first": "$codeStatut"}
            }
        },
        {
            "$group": {
                "_id": {
                    "departement": "$_id.codeInseeDepartement",
                    "statut": "$codeStatutSpecies"
                },
                "nombreEspeces": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "departement": "$_id.departement",
                "statut": "$_id.statut",
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            "$sort": {"departement": 1, "statut": 1}
        }
    ]

    resultats_aggregation = list(col.aggregate(pipeline))

    results_by_department = {}

    for res in resultats_aggregation:
        dep = res['departement']
        statut = _format_key(res['statut'], "Sans codeStatut")  # Utiliser la fonction utilitaire
        nombre = res['nombreEspeces']

        if dep not in results_by_department:
            results_by_department[dep] = {
                'comptes_statut': {},
                'nombre_especes_sans_codestatut': 0,
                'total_especes_departement': 0
            }

        results_by_department[dep]['total_especes_departement'] += nombre

        if statut == "Sans codeStatut":
            results_by_department[dep]['nombre_especes_sans_codestatut'] = nombre
        else:
            results_by_department[dep]['comptes_statut'][statut] = nombre

    return results_by_department


def count_species_by_regne_for_multiple_deps(col: Collection, departements: list) -> dict:
    """
    Compte le nombre d'espèces uniques par règne pour chaque département donné.
    Retourne un dictionnaire structuré avec les résultats.
    """
    pipeline = [
        {
            "$match": {"codeInseeDepartement": {"$in": departements}}
        },
        {
            "$group": {
                "_id": {
                    "nomScientifiqueRef": "$nomScientifiqueRef",
                    "codeInseeDepartement": "$codeInseeDepartement"
                },
                "regneSpecies": {"$first": "$regne"}
            }
        },
        {
            "$group": {
                "_id": {
                    "departement": "$_id.codeInseeDepartement",
                    "regne": "$regneSpecies"
                },
                "nombreEspeces": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "departement": "$_id.departement",
                "regne": "$_id.regne",
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            "$sort": {"departement": 1, "regne": 1}
        }
    ]

    resultats_aggregation = list(col.aggregate(pipeline))

    results_by_department = {}

    for res in resultats_aggregation:
        dep = res['departement']
        regne = _format_key(res['regne'], "Sans règne")
        nombre = res['nombreEspeces']

        if dep not in results_by_department:
            results_by_department[dep] = {
                'comptes_regne': {},
                'nombre_especes_sans_regne': 0,
                'total_especes_departement': 0
            }

        results_by_department[dep]['total_especes_departement'] += nombre

        if regne == "Sans règne":
            results_by_department[dep]['nombre_especes_sans_regne'] = nombre
        else:
            results_by_department[dep]['comptes_regne'][regne] = nombre

    return results_by_department


def count_species_by_regne_and_statut_for_multiple_deps(col: Collection, departements: list) -> dict:
    """
    Compte le nombre d'espèces uniques par règne et codeStatut pour chaque département donné.
    Retourne un dictionnaire structuré avec les résultats.
    """
    pipeline = [
        {
            "$match": {"codeInseeDepartement": {"$in": departements}}
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

    results_by_department = {}

    for res in resultats_aggregation:
        dep = res['departement']
        regne = _format_key(res['regne'], 'N/A Règne')
        statut = _format_key(res['statut'], 'N/A Statut')
        nombre = res['nombreEspeces']

        if dep not in results_by_department:
            results_by_department[dep] = {
                'total_especes_departement': 0,
                'regnes': {}
            }

        if regne not in results_by_department[dep]['regnes']:
            results_by_department[dep]['regnes'][regne] = {
                'total_especes_regne': 0,
                'statuts': {}
            }

        results_by_department[dep]['regnes'][regne]['statuts'][statut] = nombre

        results_by_department[dep]['regnes'][regne]['total_especes_regne'] += nombre
        results_by_department[dep]['total_especes_departement'] += nombre

    return results_by_department


def count_species_by_regne_taxogroup_and_statut_for_one_dep(col: Collection, dep: int) -> tuple[dict, int]:
    """
    Compte le nombre d'espèces uniques par règne, groupe taxonomique simple et codeStatut
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
                "codeStatutSpecies": {"$first": "$codeStatut"}
            }
        },
        {
            "$group": {
                "_id": {
                    "regne": "$regneSpecies",
                    "groupeTaxoSimple": "$groupeTaxoSimpleSpecies",
                    "statut": "$codeStatutSpecies"
                },
                "nombreEspeces": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "regne": "$_id.regne",
                "groupeTaxoSimple": "$_id.groupeTaxoSimple",
                "statut": "$_id.statut",
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            "$sort": {"regne": 1, "groupeTaxoSimple": 1, "statut": 1}
        }
    ]

    resultats_aggregation = list(col.aggregate(pipeline))

    data_structure = {}
    total_especes_departement = 0

    for res in resultats_aggregation:
        regne = _format_key(res['regne'], 'N/A Règne')
        groupe_taxo = _format_key(res['groupeTaxoSimple'], 'N/A Groupe Taxo Simple')
        statut = _format_key(res['statut'], 'N/A Statut')
        nombre = res['nombreEspeces']

        if regne not in data_structure:
            data_structure[regne] = {'total_regne': 0, 'groupes_taxo': {}}

        if groupe_taxo not in data_structure[regne]['groupes_taxo']:
            data_structure[regne]['groupes_taxo'][groupe_taxo] = {'total_groupe': 0, 'statuts': {}}

        data_structure[regne]['groupes_taxo'][groupe_taxo]['statuts'][statut] = nombre

        data_structure[regne]['groupes_taxo'][groupe_taxo]['total_groupe'] += nombre
        data_structure[regne]['total_regne'] += nombre
        total_especes_departement += nombre

    return data_structure, total_especes_departement


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


# --- Fonctions d'affichage (utilisent les données structurées) ---

def display_statut_results(results_by_department: dict):
    """Affiche les résultats de count_species_by_code_statut_for_multiple_deps."""
    for dep_key in sorted(results_by_department.keys()):
        data = results_by_department[dep_key]
        print(f"\n--- Statistiques pour le département: {dep_key} ---")
        print("Nombre d'espèces par codeStatut:")

        # Afficher le statut "Sans codeStatut" en premier si présent
        if 'Sans codeStatut' in data['comptes_statut']:
            print(f"\tSans codeStatut: {data['comptes_statut']['Sans codeStatut']}")
            del data['comptes_statut']['Sans codeStatut']  # Supprimer pour ne pas le trier avec les autres

        for statut_key in sorted(data['comptes_statut'].keys()):
            print(f"\t{statut_key}: {data['comptes_statut'][statut_key]}")

        print(f"\nNombre d'espèces sans codeStatut: {data['nombre_especes_sans_codestatut']}")
        print(f"Nombre total d'espèces dans le département {dep_key}: {data['total_especes_departement']}")

        # Pourcentages
        if data['total_especes_departement'] > 0:
            print("\nPourcentage d'espèces par codeStatut:")
            if data['nombre_especes_sans_codestatut'] > 0:
                pourcentage_sans = (data['nombre_especes_sans_codestatut'] / data['total_especes_departement']) * 100
                print(f"\tSans codeStatut: {pourcentage_sans:.2f}%")

            # Ré-ajouter "Sans codeStatut" pour le calcul du pourcentage si nécessaire
            if 'Sans codeStatut' not in data['comptes_statut'] and data['nombre_especes_sans_codestatut'] > 0:
                data['comptes_statut']['Sans codeStatut'] = data['nombre_especes_sans_codestatut']

            for statut_key in sorted(data['comptes_statut'].keys()):
                pourcentage_statut = (data['comptes_statut'][statut_key] / data['total_especes_departement']) * 100
                print(f"\t{statut_key}: {pourcentage_statut:.2f}%")
        else:
            print(f"\nAucune espèce trouvée dans le département {dep_key}.")


def display_regne_results(results_by_department: dict):
    """Affiche les résultats de count_species_by_regne_for_multiple_deps."""
    for dep_key in sorted(results_by_department.keys()):
        data = results_by_department[dep_key]
        print(f"\n--- Statistiques pour le département: {dep_key} ---")
        print("Nombre d'espèces par règne:")

        if 'Sans règne' in data['comptes_regne']:
            print(f"\tSans règne: {data['comptes_regne']['Sans règne']}")
            del data['comptes_regne']['Sans règne']

        for regne_key in sorted(data['comptes_regne'].keys()):
            print(f"\t{regne_key}: {data['comptes_regne'][regne_key]}")

        print(f"\nNombre d'espèces sans règne: {data['nombre_especes_sans_regne']}")
        print(f"Nombre total d'espèces dans le département {dep_key}: {data['total_especes_departement']}")

        # Pourcentages
        if data['total_especes_departement'] > 0:
            print("\nPourcentage d'espèces par règne:")
            if data['nombre_especes_sans_regne'] > 0:
                pourcentage_sans = (data['nombre_especes_sans_regne'] / data['total_especes_departement']) * 100
                print(f"\tSans règne: {pourcentage_sans:.2f}%")

            if 'Sans règne' not in data['comptes_regne'] and data['nombre_especes_sans_regne'] > 0:
                data['comptes_regne']['Sans règne'] = data['nombre_especes_sans_regne']

            for regne_key in sorted(data['comptes_regne'].keys()):
                pourcentage_regne = (data['comptes_regne'][regne_key] / data['total_especes_departement']) * 100
                print(f"\t{regne_key}: {pourcentage_regne:.2f}%")
        else:
            print(f"\nAucune espèce trouvée dans le département {dep_key}.")


def display_regne_statut_results(results_by_department: dict):
    """Affiche les résultats de count_species_by_regne_and_statut_for_multiple_deps."""
    for dep_key in sorted(results_by_department.keys()):
        data_dep = results_by_department[dep_key]
        print(f"\n--- Statistiques pour le département: {dep_key} ---")
        print(f"Total espèces dans le département: {data_dep['total_especes_departement']}")

        for regne_key in sorted(data_dep['regnes'].keys()):
            data_regne = data_dep['regnes'][regne_key]
            print(f"\n  Règne: {regne_key} (Total: {data_regne['total_especes_regne']} espèces)")
            print("    Nombre d'espèces par codeStatut:")

            if data_regne['total_especes_regne'] > 0:
                for statut_key in sorted(data_regne['statuts'].keys()):
                    count = data_regne['statuts'][statut_key]
                    percentage = (count / data_regne['total_especes_regne']) * 100
                    print(f"      {statut_key}: {count} espèces ({percentage:.2f}%)")
            else:
                print("      Aucune espèce pour ce règne.")

    print("\n--- Récapitulatif global par département et par règne (pourcentage du total du département) ---")
    for dep_key in sorted(results_by_department.keys()):
        data_dep = results_by_department[dep_key]
        print(f"\nDépartement: {dep_key} (Total espèces: {data_dep['total_especes_departement']})")
        if data_dep['total_especes_departement'] > 0:
            for regne_key in sorted(data_dep['regnes'].keys()):
                data_regne = data_dep['regnes'][regne_key]
                percentage_of_dep = (data_regne['total_especes_regne'] / data_dep['total_especes_departement']) * 100
                print(
                    f"  {regne_key}: {data_regne['total_especes_regne']} espèces ({percentage_of_dep:.2f}% du département)")
        else:
            print("  Aucune espèce trouvée.")


def display_regne_taxogroup_statut_results(data_structure: dict, total_especes_departement: int, dep: int):
    """Affiche les résultats de count_species_by_regne_taxogroup_and_statut_for_one_dep."""
    print(f"\n--- Statistiques pour le département: {dep} ---")
    print(f"Total espèces dans le département: {total_especes_departement}")

    if total_especes_departement == 0:
        print("Aucune espèce trouvée pour ce département.")
        return

    for regne_key in sorted(data_structure.keys()):
        data_regne = data_structure[regne_key]
        perc_regne_dep = (data_regne['total_regne'] / total_especes_departement) * 100
        print(
            f"\n  Règne: {regne_key} (Total: {data_regne['total_regne']} espèces, {perc_regne_dep:.2f}% du département)")

        for groupe_key in sorted(data_regne['groupes_taxo'].keys()):
            data_groupe = data_regne['groupes_taxo'][groupe_key]
            perc_groupe_regne = (data_groupe['total_groupe'] / data_regne['total_regne']) * 100 if data_regne[
                                                                                                       'total_regne'] > 0 else 0
            print(
                f"\n    Groupe Taxonomique: {groupe_key} (Total: {data_groupe['total_groupe']} espèces, {perc_groupe_regne:.2f}% du règne)")
            print("      Nombre d'espèces par codeStatut:")

            if data_groupe['total_groupe'] > 0:
                for statut_key in sorted(data_groupe['statuts'].keys()):
                    count = data_groupe['statuts'][statut_key]
                    percentage_statut_groupe = (count / data_groupe['total_groupe']) * 100
                    print(f"        {statut_key}: {count} espèces ({percentage_statut_groupe:.2f}%)")
            else:
                print("        Aucune espèce pour ce groupe taxonomique.")


def display_regne_taxogroup_simple_advanced_results(data_structure: dict, total_especes_departement: int, dep: int):
    """Affiche les résultats de count_species_by_regne_taxogroup_simple_advanced."""
    print(f"\n--- Statistiques pour le département: {dep} ---")
    print(f"Total espèces dans le département: {total_especes_departement}")

    if total_especes_departement == 0:
        print("Aucune espèce trouvée pour ce département.")
        return

    for regne_key in sorted(data_structure.keys()):
        data_regne = data_structure[regne_key]
        perc_regne_dep = (data_regne['total_regne'] / total_especes_departement) * 100
        print(
            f"\n  Règne: {regne_key} (Total: {data_regne['total_regne']} espèces, {perc_regne_dep:.2f}% du département)")

        for groupe_simple_key in sorted(data_regne['groupes_simple'].keys()):
            data_groupe_simple = data_regne['groupes_simple'][groupe_simple_key]
            perc_groupe_simple_regne = (data_groupe_simple['total_groupe_simple'] / data_regne['total_regne']) * 100 if \
            data_regne['total_regne'] > 0 else 0
            print(
                f"\n    Groupe Taxonomique Simple: {groupe_simple_key} (Total: {data_groupe_simple['total_groupe_simple']} espèces, {perc_groupe_simple_regne:.2f}% du règne)")
            print("      Nombre d'espèces par Groupe Taxonomique Avancé:")

            if data_groupe_simple['total_groupe_simple'] > 0:
                for groupe_avance_key in sorted(data_groupe_simple['groupes_avance'].keys()):
                    count = data_groupe_simple['groupes_avance'][groupe_avance_key]
                    percentage_groupe_avance_simple = (count / data_groupe_simple['total_groupe_simple']) * 100
                    print(f"        {groupe_avance_key}: {count} espèces ({percentage_groupe_avance_simple:.2f}%)")
            else:
                print("        Aucune espèce pour ce groupe taxonomique simple.")


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
        results_statut = count_species_by_code_statut(col=collection, departements=departements_a_analyser)
        display_statut_results(results_statut)

        # print("\n\n--- Analyse par règne pour plusieurs départements ---")
        # results_regne = count_species_by_regne_for_multiple_deps(col=collection, departements=departements_a_analyser)
        # display_regne_results(results_regne)

        # print("\n\n--- Analyse par règne et codeStatut pour plusieurs départements ---")
        # results_regne_statut = count_species_by_regne_and_statut_for_multiple_deps(col=collection, departements=departements_a_analyser)
        # display_regne_statut_results(results_regne_statut)

        # print("\n\n--- Analyse par règne, groupe taxonomique simple et codeStatut pour le département 25 ---")
        # dep_single = 25
        # data_regne_taxo_statut, total_regne_taxo_statut = count_species_by_regne_taxogroup_and_statut_for_one_dep(col=collection, dep=dep_single)
        # display_regne_taxogroup_statut_results(data_regne_taxo_statut, total_regne_taxo_statut, dep_single)
        # # Pour voir la structure des données retournées (utile pour Flask)
        # # print("\nStructure des données (regne_taxo_statut) :")
        # # pprint.pprint(data_regne_taxo_statut)

        # print("\n\n--- Analyse par règne, groupe taxonomique simple et avancé pour le département 25 ---")
        # data_regne_taxo_simple_advanced, total_regne_taxo_simple_advanced = count_species_by_regne_taxogroup_simple_advanced(col=collection, dep=dep_single)
        # display_regne_taxogroup_simple_advanced_results(data_regne_taxo_simple_advanced, total_regne_taxo_simple_advanced, dep_single)
        # # Pour voir la structure des données retournées (utile pour Flask)
        # # print("\nStructure des données (regne_taxo_simple_advanced) :")
        # # pprint.pprint(data_regne_taxo_simple_advanced)

    except Exception as e:
        print(f"Une erreur inattendue est survenue: {e}")
    finally:
        if client:
            client.close()
            print("\nConnexion à MongoDB fermée.")