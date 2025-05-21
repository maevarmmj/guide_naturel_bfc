from pymongo.mongo_client import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.server_api import ServerApi


def count_species_by_code_statut_for_multiple_deps(col: Collection, departements: list):
    # Pipeline d'agrégation pour compter les ESPÈCES par codeStatut POUR CHAQUE DÉPARTEMENT
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

    # Exécuter le pipeline
    resultats_aggregation = list(col.aggregate(pipeline))

    # Traiter les résultats pour organiser les données par département
    results_by_department = {}

    for res in resultats_aggregation:
        dep = res['departement']
        statut = res['statut']
        nombre = res['nombreEspeces']

        if dep not in results_by_department:
            results_by_department[dep] = {
                'comptes_statut': {},
                'nombre_especes_sans_codestatut': 0,
                'total_especes_avec_codestatut': 0,
                'total_especes_departement': 0
            }

        results_by_department[dep]['total_especes_departement'] += nombre

        if statut is None:
            results_by_department[dep]['nombre_especes_sans_codestatut'] = nombre
        else:
            results_by_department[dep]['comptes_statut'][statut] = nombre
            results_by_department[dep]['total_especes_avec_codestatut'] += nombre

    # Afficher les résultats pour chaque département
    for dep_key in sorted(results_by_department.keys()): # Trier par département pour l'affichage
        data = results_by_department[dep_key]
        print(f"\n--- Statistiques pour le département: {dep_key} ---")
        print("Nombre d'espèces par codeStatut:")
        for statut_key in sorted(data['comptes_statut'].keys()):
            print(f"\t{statut_key}: {data['comptes_statut'][statut_key]}")

        print(f"\nNombre d'espèces sans codeStatut: {data['nombre_especes_sans_codestatut']}")
        print(f"Nombre total d'espèces avec codeStatut: {data['total_especes_avec_codestatut']}")
        print(f"Nombre total d'espèces dans le département {dep_key}: {data['total_especes_departement']}")

        # Pourcentages
        if data['total_especes_departement'] > 0:
            print("\nPourcentage d'espèces par codeStatut:")
            if data['nombre_especes_sans_codestatut'] > 0:
                pourcentage_sans = (data['nombre_especes_sans_codestatut'] / data['total_especes_departement']) * 100
                print(f"\tSans codeStatut: {pourcentage_sans:.2f}%")

            for statut_key in sorted(data['comptes_statut'].keys()):
                pourcentage_statut = (data['comptes_statut'][statut_key] / data['total_especes_departement']) * 100
                print(f"\t{statut_key}: {pourcentage_statut:.2f}%")
        else:
            print(f"\nAucune espèce trouvée dans le département {dep_key}.")


def count_species_by_regne_for_multiple_deps(col: Collection, departements: list):
    # Pipeline d'agrégation pour compter les ESPÈCES par Règne POUR CHAQUE DÉPARTEMENT
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

    # Exécuter le pipeline
    resultats_aggregation = list(col.aggregate(pipeline))

    # Traiter les résultats pour organiser les données par département
    results_by_department = {}

    for res in resultats_aggregation:
        dep = res['departement']
        regne = res['regne']
        nombre = res['nombreEspeces']

        if dep not in results_by_department:
            results_by_department[dep] = {
                'comptes_regne': {},
                'nombre_especes_sans_regne': 0,
                'total_especes_departement': 0
            }

        results_by_department[dep]['total_especes_departement'] += nombre

        if regne is None:
            results_by_department[dep]['nombre_especes_sans_regne'] = nombre
        else:
            results_by_department[dep]['comptes_regne'][regne] = nombre

    # Afficher les résultats pour chaque département
    for dep_key in sorted(results_by_department.keys()):
        data = results_by_department[dep_key]
        print(f"\n--- Statistiques pour le département: {dep_key} ---")
        print("Nombre d'espèces par règne:")
        # Trie les règnes pour un affichage ordonné
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

            for regne_key in sorted(data['comptes_regne'].keys()):
                pourcentage_regne = (data['comptes_regne'][regne_key] / data['total_especes_departement']) * 100
                print(f"\t{regne_key}: {pourcentage_regne:.2f}%")
        else:
            print(f"\nAucune espèce trouvée dans le département {dep_key}.")


def count_species_by_regne_and_statut_for_multiple_deps(col: Collection, departements: list):
    # Pipeline d'agrégation
    pipeline = [
        {
            # Étape 1: Filtrer les observations pour inclure uniquement les départements souhaités
            "$match": {"codeInseeDepartement": {"$in": departements}}
        },
        {
            # Étape 2: Grouper les observations par espèce ET par département.
            # On récupère le règne et le statut de chaque espèce unique.
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
            # Étape 3: Grouper les espèces uniques par département, règne et statut
            # pour compter le nombre d'espèces dans chaque combinaison.
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
            # Étape 4: Reformater le document de sortie pour faciliter le traitement Python
            "$project": {
                "_id": 0,  # Exclut l'ID généré par MongoDB
                "departement": "$_id.departement",
                "regne": "$_id.regne",
                "statut": "$_id.statut",
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            # Étape 5 (Optionnel): Trier les résultats pour une meilleure lisibilité
            # Tri par département, puis par règne, puis par statut.
            "$sort": {"departement": 1, "regne": 1, "statut": 1}
        }
    ]

    # Exécuter le pipeline
    resultats_aggregation = list(col.aggregate(pipeline))

    # Traiter les résultats pour organiser les données par département, règne et statut
    results_by_department = {}

    for res in resultats_aggregation:
        dep = res['departement']
        regne = res['regne'] if res['regne'] is not None else 'N/A Règne'  # Gérer les règnes None
        statut = res['statut'] if res['statut'] is not None else 'N/A Statut'  # Gérer les statuts None
        nombre = res['nombreEspeces']

        if dep not in results_by_department:
            results_by_department[dep] = {
                'total_especes_departement': 0,
                'regnes': {}
            }

        # S'assurer que le règne existe dans la structure
        if regne not in results_by_department[dep]['regnes']:
            results_by_department[dep]['regnes'][regne] = {
                'total_especes_regne': 0,
                'statuts': {}
            }

        # Ajouter le nombre d'espèces pour cette combinaison règne/statut
        results_by_department[dep]['regnes'][regne]['statuts'][statut] = nombre

        # Mettre à jour les totaux
        results_by_department[dep]['regnes'][regne]['total_especes_regne'] += nombre
        results_by_department[dep]['total_especes_departement'] += nombre

    # Afficher les résultats
    for dep_key in sorted(results_by_department.keys()):
        data_dep = results_by_department[dep_key]
        print(f"\n--- Statistiques pour le département: {dep_key} ---")
        print(f"Total espèces dans le département: {data_dep['total_especes_departement']}")

        for regne_key in sorted(data_dep['regnes'].keys()):
            data_regne = data_dep['regnes'][regne_key]
            print(f"\n  Règne: {regne_key} (Total: {data_regne['total_especes_regne']} espèces)")
            print("    Nombre d'espèces par codeStatut:")

            # Calculer le pourcentage de chaque statut par rapport au total du règne
            if data_regne['total_especes_regne'] > 0:
                for statut_key in sorted(data_regne['statuts'].keys()):
                    count = data_regne['statuts'][statut_key]
                    percentage = (count / data_regne['total_especes_regne']) * 100
                    print(f"      {statut_key}: {count} espèces ({percentage:.2f}%)")
            else:
                print("      Aucune espèce pour ce règne.")

    # Optionnel: Calculer les pourcentages par rapport au total du département
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


def count_species_by_regne_taxogroup_and_statut_for_one_dep(col: Collection, dep: int):
    # Pipeline d'agrégation
    pipeline = [
        {
            # Étape 1: Filtrer les observations pour le département spécifié
            "$match": {"codeInseeDepartement": dep}
        },
        {
            # Étape 2: Grouper les observations par espèce ET par département.
            # On récupère le règne, le groupe taxonomique simple et le statut de chaque espèce unique.
            # L'ID de groupe est composite pour garantir l'unicité de l'espèce au sein du département.
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
            # Étape 3: Grouper les espèces uniques par règne, groupe taxonomique et statut
            # pour compter le nombre d'espèces dans chaque combinaison.
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
            # Étape 4: Reformater le document de sortie pour faciliter le traitement Python
            "$project": {
                "_id": 0,  # Exclut l'ID généré par MongoDB
                "regne": "$_id.regne",
                "groupeTaxoSimple": "$_id.groupeTaxoSimple",
                "statut": "$_id.statut",
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            # Étape 5 (Optionnel): Trier les résultats pour une meilleure lisibilité
            # Tri par règne, puis par groupe taxonomique, puis par statut.
            "$sort": {"regne": 1, "groupeTaxoSimple": 1, "statut": 1}
        }
    ]

    # Exécuter le pipeline
    resultats_aggregation = list(col.aggregate(pipeline))

    # Traiter les résultats pour organiser les données par règne, groupe taxonomique et statut
    # La structure sera : regne -> groupeTaxoSimple -> statut -> nombre d'espèces
    data_structure = {}
    total_especes_departement = 0

    for res in resultats_aggregation:
        regne = res['regne'] if res['regne'] is not None else 'N/A Règne'
        groupe_taxo = res['groupeTaxoSimple'] if res['groupeTaxoSimple'] is not None else 'N/A Groupe Taxo'
        statut = res['statut'] if res['statut'] is not None else 'N/A Statut'
        nombre = res['nombreEspeces']

        if regne not in data_structure:
            data_structure[regne] = {'total_regne': 0, 'groupes_taxo': {}}

        if groupe_taxo not in data_structure[regne]['groupes_taxo']:
            data_structure[regne]['groupes_taxo'][groupe_taxo] = {'total_groupe': 0, 'statuts': {}}

        data_structure[regne]['groupes_taxo'][groupe_taxo]['statuts'][statut] = nombre

        # Mise à jour des totaux
        data_structure[regne]['groupes_taxo'][groupe_taxo]['total_groupe'] += nombre
        data_structure[regne]['total_regne'] += nombre
        total_especes_departement += nombre # Total global pour le département

    # Afficher les résultats pour le département unique
    print(f"\n--- Statistiques pour le département: {dep} ---")
    print(f"Total espèces dans le département: {total_especes_departement}")

    if total_especes_departement == 0:
        print("Aucune espèce trouvée pour ce département.")
        return

    for regne_key in sorted(data_structure.keys()):
        data_regne = data_structure[regne_key]
        # Pourcentage du règne par rapport au total du département
        perc_regne_dep = (data_regne['total_regne'] / total_especes_departement) * 100
        print(f"\n  Règne: {regne_key} (Total: {data_regne['total_regne']} espèces, {perc_regne_dep:.2f}% du département)")

        for groupe_key in sorted(data_regne['groupes_taxo'].keys()):
            data_groupe = data_regne['groupes_taxo'][groupe_key]
            # Pourcentage du groupe par rapport au total du règne
            perc_groupe_regne = (data_groupe['total_groupe'] / data_regne['total_regne']) * 100 if data_regne['total_regne'] > 0 else 0
            print(f"\n    Groupe Taxonomique: {groupe_key} (Total: {data_groupe['total_groupe']} espèces, {perc_groupe_regne:.2f}% du règne)")
            print("      Nombre d'espèces par codeStatut:")

            if data_groupe['total_groupe'] > 0:
                for statut_key in sorted(data_groupe['statuts'].keys()):
                    count = data_groupe['statuts'][statut_key]
                    # Pourcentage du statut par rapport au total du groupe taxonomique
                    percentage_statut_groupe = (count / data_groupe['total_groupe']) * 100
                    print(f"        {statut_key}: {count} espèces ({percentage_statut_groupe:.2f}%)")
            else:
                print("        Aucune espèce pour ce groupe taxonomique.")


def count_species_by_regne_taxogroup_simple_advanced(col: Collection, dep: int):
    # Pipeline d'agrégation
    pipeline = [
        {
            # Étape 1: Filtrer les observations pour le département spécifié
            "$match": {"codeInseeDepartement": dep}
        },
        {
            # Étape 2: Grouper les observations par espèce ET par département.
            # On récupère le règne, le groupe taxonomique simple et le groupe taxonomique avancé
            # de chaque espèce unique.
            "$group": {
                "_id": {
                    "nomScientifiqueRef": "$nomScientifiqueRef",
                    "codeInseeDepartement": "$codeInseeDepartement"
                },
                "regneSpecies": {"$first": "$regne"},
                "groupeTaxoSimpleSpecies": {"$first": "$groupeTaxoSimple"},
                "groupeTaxoAvanceSpecies": {"$first": "$groupeTaxoAvance"}
                # codeStatut n'est plus capturé ici car on ne l'utilise pas dans ce décompte
            }
        },
        {
            # Étape 3: Grouper les espèces uniques par règne, groupe taxonomique simple et groupe taxonomique avancé
            # pour compter le nombre d'espèces dans chaque combinaison.
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
            # Étape 4: Reformater le document de sortie pour faciliter le traitement Python
            "$project": {
                "_id": 0,  # Exclut l'ID généré par MongoDB
                "regne": "$_id.regne",
                "groupeTaxoSimple": "$_id.groupeTaxoSimple",
                "groupeTaxoAvance": "$_id.groupeTaxoAvance",
                "nombreEspeces": "$nombreEspeces"
            }
        },
        {
            # Étape 5 (Optionnel): Trier les résultats pour une meilleure lisibilité
            # Tri par règne, puis par groupe taxonomique simple, puis par groupe taxonomique avancé.
            "$sort": {"regne": 1, "groupeTaxoSimple": 1, "groupeTaxoAvance": 1}
        }
    ]

    # Exécuter le pipeline
    resultats_aggregation = list(col.aggregate(pipeline))

    # Traiter les résultats pour organiser les données dans une structure arborescente
    # Structure : regne -> groupe_taxo_simple -> groupe_taxo_avance -> nombre d'espèces
    data_structure = {}
    total_especes_departement = 0

    for res in resultats_aggregation:
        regne = res['regne'] if res['regne'] is not None else 'N/A Règne'
        groupe_simple = res['groupeTaxoSimple'] if res['groupeTaxoSimple'] is not None else 'N/A Groupe Taxo Simple'
        groupe_avance = res['groupeTaxoAvance'] if res['groupeTaxoAvance'] is not None else 'N/A Groupe Taxo Avancé'
        nombre = res['nombreEspeces']

        if regne not in data_structure:
            data_structure[regne] = {'total_regne': 0, 'groupes_simple': {}}

        if groupe_simple not in data_structure[regne]['groupes_simple']:
            data_structure[regne]['groupes_simple'][groupe_simple] = {'total_groupe_simple': 0, 'groupes_avance': {}}

        data_structure[regne]['groupes_simple'][groupe_simple]['groupes_avance'][groupe_avance] = nombre

        # Mise à jour des totaux
        data_structure[regne]['groupes_simple'][groupe_simple]['total_groupe_simple'] += nombre
        data_structure[regne]['total_regne'] += nombre
        total_especes_departement += nombre # Total global pour le département

    # Afficher les résultats pour le département unique
    print(f"\n--- Statistiques pour le département: {dep} ---")
    print(f"Total espèces dans le département: {total_especes_departement}")

    if total_especes_departement == 0:
        print("Aucune espèce trouvée pour ce département.")
        return

    for regne_key in sorted(data_structure.keys()):
        data_regne = data_structure[regne_key]
        # Pourcentage du règne par rapport au total du département
        perc_regne_dep = (data_regne['total_regne'] / total_especes_departement) * 100
        print(f"\n  Règne: {regne_key} (Total: {data_regne['total_regne']} espèces, {perc_regne_dep:.2f}% du département)")

        for groupe_simple_key in sorted(data_regne['groupes_simple'].keys()):
            data_groupe_simple = data_regne['groupes_simple'][groupe_simple_key]
            # Pourcentage du groupe simple par rapport au total du règne
            perc_groupe_simple_regne = (data_groupe_simple['total_groupe_simple'] / data_regne['total_regne']) * 100 if data_regne['total_regne'] > 0 else 0
            print(f"\n    Groupe Taxonomique Simple: {groupe_simple_key} (Total: {data_groupe_simple['total_groupe_simple']} espèces, {perc_groupe_simple_regne:.2f}% du règne)")
            print("      Nombre d'espèces par Groupe Taxonomique Avancé:")

            if data_groupe_simple['total_groupe_simple'] > 0:
                for groupe_avance_key in sorted(data_groupe_simple['groupes_avance'].keys()):
                    count = data_groupe_simple['groupes_avance'][groupe_avance_key]
                    # Pourcentage du groupe avancé par rapport au total du groupe simple
                    percentage_groupe_avance_simple = (count / data_groupe_simple['total_groupe_simple']) * 100
                    print(f"        {groupe_avance_key}: {count} espèces ({percentage_groupe_avance_simple:.2f}%)")
            else:
                print("        Aucune espèce pour ce groupe taxonomique simple.")


if __name__ == '__main__':
    uri = "mongodb+srv://guest:guestpass@big-data.640be.mongodb.net/?retryWrites=true&w=majority&appName=Big-Data"
    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client['LeGuideNaturel']
    collection = db['Nature']

    departements_a_analyser = [21, 25, 39, 58, 71, 89, 90]

    # count_species_by_code_statut_for_multiple_deps(col=collection, departements=departements_a_analyser)
    count_species_by_regne_for_multiple_deps(col=collection, departements=departements_a_analyser)
    # count_species_by_regne_and_statut_for_multiple_deps(col=collection, departements=departements_a_analyser)
    # count_species_by_regne_taxogroup_and_statut_for_one_dep(col=collection, dep=25)
    # count_species_by_regne_taxogroup_simple_advanced(col=collection, dep=25)
    client.close()
