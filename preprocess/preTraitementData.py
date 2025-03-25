import os
import glob
import pandas as pd
from pathlib import Path


def agg_all_csvs(out: Path):
    base_dir = r"../extractINPN_bourgogneFrancheComte_04112024"

    csv_files = glob.glob(os.path.join(base_dir, "*.csv"))

    header = ["cdNom", "nomScientifiqueRef", "nomVernaculaire", "regne", "espece",
              "groupeTaxoSimple", "groupeTaxoAvance", "commune", "codeInseeDepartement"]

    first_file = True
    for file_path in csv_files:
        print("Extracting data from CSV file...")
        df = pd.read_csv(file_path, low_memory=False)

        df_filtered = df.filter(items=header)

        print("Writing to CSV file...")
        if first_file:
            df_filtered.to_csv(out, mode='w', index=False, header=True)
            first_file = False
        else:
            df_filtered.to_csv(out, mode='a', index=False, header=False)


def merge_espece(out: Path):
    csv = r"..\data\all_data.csv"
    print("Reading CSV file...")
    df = pd.read_csv(csv, low_memory=False)
    print("Done")
    df = df.dropna(subset=["commune", "nomScientifiqueRef"], how="any")
    df_grouped = df.groupby(["commune", "nomScientifiqueRef"], as_index=False).size().rename(
        columns={'size': 'nombreObservations'})
    # Merge the counts back into the original DataFrame
    df_final = pd.merge(df, df_grouped, on=["commune", "nomScientifiqueRef"], how="left")
    df_final = df_final.drop_duplicates(subset=["commune", "nomScientifiqueRef"])
    print("Writing merged CSV file...")
    df_final.to_csv(out, index=False)
    print("Done")


def add_code_statut(out: Path):
    main_csv = r"..\data\merge_espece.csv"
    code_csv = r"..\BDC-Statuts-v18 1\bdc_statuts_18.csv"
    main_df = pd.read_csv(main_csv, low_memory=False)
    codes_df = pd.read_csv(code_csv, low_memory=False)

    print("Adding code statut...")
    codes_df.dropna(subset=['CODE_STATUT'], inplace=True)
    codes_df = codes_df[codes_df['CODE_STATUT'] != 'true']
    codes_df_unique = codes_df.drop_duplicates(subset='CD_NOM', keep='first')
    codes_df_unique = codes_df_unique[['CD_NOM', 'CODE_STATUT']]
    codes_df_unique.rename(columns={'CD_NOM': 'cdNom', 'CODE_STATUT': 'codeStatut'}, inplace=True)

    merged_df = pd.merge(main_df, codes_df_unique, on='cdNom', how='left')
    merged_df = merged_df.drop('cdNom', axis=1)

    print("Writing merged CSV file...")
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

