import os
import glob
import pandas as pd
from pathlib import Path


# aggrège tous les csv du dossier BFC
def agg_all_csvs(out: Path):
    base_dir = r"../data/extractINPN_bourgogneFrancheComte_04112024"

    csv_files = glob.glob(os.path.join(base_dir, "*.csv"))

    # récupère juste les colones d'intérêts
    header = ["cdNom", "nomScientifiqueRef", "nomVernaculaire", "regne",
              "groupeTaxoSimple", "groupeTaxoAvance", "commune", "codeInseeDepartement"]

    first_file = True
    for file_path in csv_files:
        print("Extracting data from CSV file...")
        df = pd.read_csv(file_path, low_memory=False)

        # retire tous les code de département unique et valable
        masque = ~df['codeInseeDepartement'].str.contains(" ", na=False)
        df = df[masque]

        df_filtered = df.filter(items=header)

        print("Writing to CSV file...")
        if first_file:
            df_filtered.to_csv(out, mode='w', index=False, header=True)
            first_file = False
        else:
            df_filtered.to_csv(out, mode='a', index=False, header=False)


# Compte les observations de chaque espèce dans chaque commune pour en faire une ligne unique qui contient
# une nouvelle colone avec le nombre d'observations dans cette commune
def merge_espece(out: Path):
    csv = r"..\data\all_data.csv"
    print("Reading CSV file...")
    df = pd.read_csv(csv, low_memory=False)
    print("Done")
    # retire toutes les communes vide et nom scientifiques vide
    df = df.dropna(subset=["commune", "nomScientifiqueRef"], how="any")
    # retire les regnes qui n'ont pas d'intérêt pour notre site
    df = df[~df['regne'].isin(["Bacteria", "Chromista", "Protozoa"])]
    # compte le nombre d'observation d'une espèce dans une commune
    df_grouped = df.groupby(["commune", "nomScientifiqueRef"], as_index=False).size().rename(
        columns={'size': 'nombreObservations'})
    df_final = pd.merge(df, df_grouped, on=["commune", "nomScientifiqueRef"], how="left")
    # supprime les duplicata
    df_final = df_final.drop_duplicates(subset=["commune", "nomScientifiqueRef"])
    print("Writing CSV file...")
    df_final.to_csv(out, index=False)
    print("Done")


# ajout du code statut depuis le second csv
def add_code_statut(out: Path):
    main_csv = r"..\data\merge_espece.csv"
    code_csv = r"..\data\bdc_statuts_18.csv"
    main_df = pd.read_csv(main_csv, low_memory=False)
    codes_df = pd.read_csv(code_csv, low_memory=False)

    print("Adding code statut...")
    # supprime les codes statuts vide
    codes_df.dropna(subset=['CODE_STATUT'], inplace=True)
    codes_df = codes_df[codes_df['CODE_STATUT'] != 'true']
    codes_df_unique = codes_df.drop_duplicates(subset='CD_NOM', keep='first')
    codes_df_unique = codes_df_unique[['CD_NOM', 'CODE_STATUT']]
    codes_df_unique.rename(columns={'CD_NOM': 'cdNom', 'CODE_STATUT': 'codeStatut'}, inplace=True)

    merged_df = pd.merge(main_df, codes_df_unique, on='cdNom', how='left')

    # si jamais les code statuts ne sont plus dans la liste
    codes_officiel = ['LC', 'NT', 'VU', 'EN', 'CR', 'EW', 'EX']
    merged_df.loc[~merged_df['codeStatut'].isin(codes_officiel), 'codeStatut'] = None

    merged_df = merged_df.drop('cdNom', axis=1)

    print("Writing CSV file...")
    merged_df.to_csv(out, index=False)
    print("Done")


if __name__ == '__main__':
    allDataPath: Path = Path(r"..\data\all_data.csv")
    if not allDataPath.is_file():
        agg_all_csvs(allDataPath)
    mergeEspecePath: Path = Path(r"..\data\merge_espece.csv")
    if not mergeEspecePath.is_file():
        merge_espece(mergeEspecePath)
    FinalPath: Path = Path(r"..\data\Final_data.csv")
    if not FinalPath.is_file():
        add_code_statut(FinalPath)
    exit(0)
