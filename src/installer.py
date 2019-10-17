# ================================ INSTALLER ================================= #
# Projet :          analyse-cadastre-dvf
# Fichier :         installer.py
# Description :     Téléchargement et installation des bases de données
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
import time
import wget
import base64
import shutil
import tarfile
# Aliases
import numpy as np
import datetime as dt
import xml.etree.ElementTree as et
# Modules
from datetime import datetime
from selenium import webdriver
# ============================================================================ #



# ================================ PARAMETRES ================================ #
# Dossiers
root_directory = "analyse-cadastre-dvf"
tmp_directory = "tmp"
# Options driver internet
headless = False
driver_path = "/usr/lib/chromium-browser/chromedriver"
# Addresses web des données
link_etalab_cadastre = "https://cadastre.data.gouv.fr/data/etalab-cadastre"
link_etalab_dvf = "https://cadastre.data.gouv.fr/data/etalab-dvf"
# ============================================================================ #



# ================================= DOSSIERS ================================= #
# Trouves le noms de dossier complet pour les données
def get_data_directory(root = root_directory):
    current = os.path.realpath('.')
    path = current.partition(root)[0] + os.sep + root + os.sep + "data" + os.sep
    return path
# ============================================================================ #



# ================================== OUTILS ================================== #
# Fais une pause variable et attend qu'une page internet soit chargée
def sleep(duration = None):
    if not duration:
        duration = 0.5 + np.abs(np.random.normal(0.5, 0.5))
    time.sleep(duration)
    return duration
# ---------------------------------------------------------------------------- #
# Navigation via hyperliens et xpath
def click_on_href(driver, href, slash = "/"):
    sleep()
    driver.find_element_by_xpath('//a[@href="' + href + slash + '"]').click()
# ---------------------------------------------------------------------------- #
# Calcules le préfixe commun à des chaines de caractères
def common_prefix(strings):
    return os.path.commonprefix(strings)
# ---------------------------------------------------------------------------- #
# Sauvegarde la liste dans le fichier
def save_list(links, root = None, filename = None):
    if (not filename):
        directory = get_data_directory()
        directory = directory.rstrip(os.sep) + os.sep + tmp_directory + os.sep
        if (not os.path.isdir(directory)):
            os.mkdir(directory)
        filename = common_prefix(links).rpartition("/")[0].rstrip("/")
        filename = filename.partition("://")[2].strip("/")
        if (root):
            filename = root.strip("/") + "_" + filename.partition(root)[2]
        filename = directory + filename.replace("/", "_") + ".txt"
        filename = filename.replace("//", "/").replace("__", "_")
    stream = open(filename, "w+")
    for element in links:
        stream.write(element + "\n")
    stream.close()
# ---------------------------------------------------------------------------- #
# Process une liste de fichiers
def download_list(links, root = None):
    directory = get_data_directory().rstrip(os.sep)
    for link in links:
        name = link.strip()
        path = name.partition("://")[2].strip("/")
        if (root and path.find(root) >= 0):
            root = root.strip("/")
            path = root + os.sep + path.rpartition(root)[2].rstrip("/")
        full_path = (directory + os.sep + path).replace("//", "/")
        full_file = full_path.replace(".gz", "")
        full_directory = full_path.rpartition("/")[0] + "/"
        full_directory = full_directory.replace("//", "/")
        if (not (os.path.exists(full_path) or os.path.exists(full_file))):
            os.makedirs(full_directory, exist_ok = True)
            wget.download(name, out = full_directory)
        if (os.path.exists(full_path) and not os.path.exists(full_file)):
            stream = gzip.open(full_path, 'rb')
            content = stream.read()
            stream.close()
            stream = open(full_file, "wb")
            stream.write(content)
            stream.close()
            os.remove(full_path)
# ============================================================================ #



# ============================= CADASTRE ETALAB ============================== #
# Récupère récursivement le nom de tous les fichiers
def explore_etalab_cadastre_recursively(
    driver,
    root,
    links,
):
    # Initialisation
    parent = None
    filenames = []
    affixes = []
    subdirectories = []
    url = driver.current_url
    directory = url.strip("/").rpartition("/")[2].strip()
    bulk = False
    # Boucle sur les liens contenus dans la page
    elements = driver.find_elements_by_tag_name('a')
    for element in elements:
        href = element.get_attribute("href")
        # Si le lien descend dans l'arborescence
        if (len(href.strip("/")) > len(url.strip("/"))):
            # Isole le nom de l'élément
            name = href.strip("/").rpartition("/")[2]
            # Si il s'agit d'un fichier
            if (name.count(".") > 0):
                filenames.append(href)
            # Si il s'agit d'un dossier
            else:
                subdirectories.append(href)
        # Si le lien remonte dans l'arborescence
        else:
            parent = element.get_attribute("href")
    # Si il ne s'agit que de fichiers et d'aucun dossiers
    if (len(filenames) > 0 and len(subdirectories) == 0):
        # Calcules les préfixes et les suffixes de chaque nom de fichier
        for filename in filenames:
            name = filename.rpartition("/")[2]
            if (name.find(directory) >= 0):
                prefix = name.partition(directory)[0]
                suffix = name.partition(directory)[2]
                affixes.append((prefix, suffix))
        # Si tous les fichiers sont dans le même format
        if (len(affixes) != len(filenames)):
            affixes = []
    # Si la liste d'affixes n'est pas vide
    if (len(affixes) > 0):
        # Remonter d'un répertoire
        if (len(parent.strip("/")) >= len(root.strip("/"))):
            sleep()
            driver.get(parent)
            url = driver.current_url
            subdirectories = []
            filenames = []
            # Boucle sur les liens contenus dans la page
            elements = driver.find_elements_by_tag_name('a')
            for element in elements:
                href = element.get_attribute("href")
                # Si le lien descend dans l'arborescence
                if (len(href.strip("/")) > len(url.strip("/"))):
                    subdirectories.append(href)
                # Si le lien remonte dans l'arborescence
                else:
                    parent = element.get_attribute("href")
            # Calcules tous les noms de fichiers en fonction des répertoires
            for subdirectory in subdirectories:
                name = subdirectory.strip("/").rpartition("/")[2]
                for affix in affixes:
                    filename = subdirectory.strip("/") + "/"
                    filename += affix[0] + name + affix[1]
                    filenames.append(filename)
            # Merge les noms de fichiers avec la liste des liens
            links += filenames
            bulk = True
    # Si la liste d'affixes est vide, continuer à processer normalement
    else:
        # Descente dans les sous-répertoires
        links += filenames
        for subdirectory in subdirectories:
            sleep()
            driver.get(subdirectory)
            if(explore_etalab_cadastre_recursively(driver, root, links)):
                break
        # Remontée d'un répertoire
        sleep()
        if (len(parent.strip("/")) >= len(root.strip("/"))):
            driver.get(parent)
    # Retourne si les données on été traitées en bulk
    return bulk
# ---------------------------------------------------------------------------- #    
# Récupère les noms de tous les fichiers du cadastre
def explore_etalab_cadastre(
    driver,
    link = link_etalab_cadastre,
    version = "2017-07-06",
    extension = "geojson",
    level = "communes"
):
    # Initialisation
    files = []
    # Ouverture de la bonne page
    driver.get(link_etalab_cadastre)
    click_on_href(driver, version)
    click_on_href(driver, extension)
    click_on_href(driver, level)
    # Exploration récursive de tous les fichiers
    explore_etalab_cadastre_recursively(driver, driver.current_url, files)
    # Retourne la liste de tous les fichiers
    return files
# ============================================================================ #



# ================================= PROGRAMME ================================ #
# Programme principal
def main():
    # Création du driver internet
    options = webdriver.ChromeOptions()
    options.add_argument("--incognito")
    if (headless):
        options.add_argument('headless')
    driver = webdriver.Chrome(driver_path, chrome_options = options)
    # Obtiens la liste des fichiers du cadastre
    files = explore_etalab_cadastre(driver)
    # Sauvegarde la liste des fichiers
    save_list(files, link_etalab_cadastre.strip("/").rpartition("/")[2])
    sleep(60)
# ---------------------------------------------------------------------------- #
stream = open((get_data_directory() + os.sep + tmp_directory + os.sep + "etalab-cadastre_2017-07-06_geojson_communes_75.txt").replace("//", "/"), "r+")
links = stream.readlines()
stream.close()
download_list(links, "etalab-cadastre")
#main()
# ============================================================================ #
