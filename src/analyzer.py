# ================================= ANALYZER ================================= #
# Projet :          analyse-cadastre-dvf
# Fichier :         analyzer.py
# Description :     Augmentation des données du cadastre et des bases dvf
# Auteur :          Vincent Reverdy
# Contributeur(s) : Vincent Reverdy [2019]
# Licence :         GNU General Public License 3
# ============================================================================ #



# ================================ PREAMBULE ================================= #
# Packages
import os
import re
import sys
import copy
import gzip
# Aliases
import numpy as np
import pandas as pd
import datetime as dt
import seaborn as sns
import matplotlib.pyplot as plt
# ============================================================================ #



# ================================ PARAMETRES ================================ #
# Date
death_date = dt.date(2017,5,20)
# Fichiers
preprocessed_file = "dvf_maison.csv"
# Dossiers
root_directory = "analyse-cadastre-dvf"
dvf_directory = "dvf"
# ============================================================================ #



# ================================= DOSSIERS ================================= #
# Trouves le nom de dossier complet pour les données
def get_data_directory(root = root_directory):
    current = os.path.realpath('.')
    path = current.partition(root)[0] + os.sep + root + os.sep + "data" + os.sep
    return path
# ---------------------------------------------------------------------------- #
# Retourne le nom de dossier complet pour les fichiers dvf
def get_dvf_directory(root = root_directory, dvf = dvf_directory):
    path = get_data_directory(root) + os.sep + dvf_directory + os.sep
    path = path.replace("//", "/")
    return path
# ---------------------------------------------------------------------------- #
# Retourne les noms de fichiers dvf
def get_dvf_files(root = root_directory, dvf = dvf_directory):
    path = get_dvf_directory(root, dvf)
    files = sorted([path + f for f in os.listdir(path)])
    files = [f for f in files if os.path.isfile(f)]
    files = [f for f in files if f.count(".txt")]
    return files
# ============================================================================ #



# =============================== PRETRAITEMENT ============================== #
# Pretraite les fichiers dvf
def preprocess_dvf_files(files):
    file_list = [files] if (type(files) == str) else [x for x in files]
    df_list = [pd.read_csv(f, sep = "|" , dtype = str) for f in file_list]
    df = pd.concat(df_list, axis = 0, ignore_index = True)
    df.drop(
        columns = [c for c in df.columns if df[c].nunique() == 0],
        inplace = True
    )
    # Date
    df["Jour"] = [x.split("/")[0] for x in df["Date mutation"]]
    df["Mois"] = [x.split("/")[1] for x in df["Date mutation"]]
    df["Annee"] = [x.split("/")[2] for x in df["Date mutation"]]
    # Valeurs flotantes
    df["Valeur fonciere"].fillna("0", inplace = True)
    df["Valeur fonciere"] = [str(x).replace(",", ".") for x in df["Valeur fonciere"]]
    df["Surface reelle bati"].fillna("0", inplace = True)
    df["Surface reelle bati"] = [str(x).replace(",", ".") for x in df["Surface reelle bati"]]
    df["Surface terrain"].fillna("0", inplace = True)
    df["Surface terrain"] = [str(x).replace(",", ".") for x in df["Surface terrain"]]
    df["Nombre de lots"].fillna("0", inplace = True)
    # Code parcelle
    df["Code departement"].fillna("00", inplace = True)
    df["Code departement"] = [str(x).rjust(2, "0") for x in df["Code departement"]]
    df["Code commune"].fillna("000", inplace = True)
    df["Code commune"] = [str(x).rjust(3, "0") for x in df["Code commune"]]
    df["Prefixe de section"].fillna("000", inplace = True)
    df["Prefixe de section"] = [str(x).rjust(3, "0") for x in df["Prefixe de section"]]
    df["Section"].fillna("00", inplace = True)
    df["Section"] = [str(x).rjust(2, "0") for x in df["Section"]]
    df["No plan"].fillna("0000", inplace = True)
    df["No plan"] = [str(x).rjust(4, "0") for x in df["No plan"]]
    df["No Volume"].fillna("", inplace = True)
    df["No Volume"] = [str(x) for x in df["No Volume"]]
    # Numero parcelle
    df["id"] = df["Code departement"] + df["Code commune"] + df["Prefixe de section"] + df["Section"] + df["No plan"] + df["No Volume"]
    return df
# ---------------------------------------------------------------------------- #
# Sauvegarde le fichier pretraite
def save_preprocessed_file(filename = preprocessed_file):
    files = get_dvf_files()
    df = preprocess_dvf_files(files)
    df = df[df["Type local"] == "Maison"]
    df["Date"] = [
        dt.date(
            int(str(x).split("/")[2]),
            int(str(x).split("/")[1]),
            int(str(x).split("/")[0])
        ) for x in df["Date mutation"]
    ]
    df = df[df["Date"] < death_date]
    df.drop(columns = ["Date"], inplace = True)
    df = df[df["Nombre de lots"].apply(lambda x: int(x)) == 0]
    df = df[df["Valeur fonciere"].apply(lambda x: float(x)) > 0.]
    df = df[df["Surface reelle bati"].apply(lambda x: int(x)) > 0]
    df = df[df["Surface terrain"].apply(lambda x: int(x)) > 0]
    df.drop(columns = ["Nombre de lots"], inplace = True)
    df.drop(
        columns = [c for c in df.columns if df[c].nunique() == 0],
        inplace = True
    )
    path = get_dvf_directory() + filename
    df.to_csv(path, sep = ";", index = False)
# ---------------------------------------------------------------------------- #
def load_preprocessed_file(filename = preprocessed_file):
    path = get_dvf_directory() + filename
    df = pd.read_csv(path, sep = ";", dtype = {"Code departement": str, "Code commune": str})
    return df
# ============================================================================ #



# ================================= PROGRAMME ================================ #
# Programme principal
def main():
    df = load_preprocessed_file()
# ---------------------------------------------------------------------------- #
main()
# ============================================================================ #
