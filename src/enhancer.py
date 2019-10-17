# ================================= ENHANCER ================================= #
# Projet :          analyse-cadastre-dvf
# Fichier :         enhancer.py
# Description :     Augmentation des données par analyse du cadastre
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
import json
import time
import wget
import base64
import pyproj
import shutil
import tarfile
# Aliases
import numpy as np
import shapely as sp
import datetime as dt
import shapely.geometry as geom
import shapely.ops as spops
import shapely.affinity as spaff
import shapely.strtree as sptree
import xml.etree.ElementTree as et
# Modules
from datetime import datetime
from selenium import webdriver
from geographiclib.geodesic import Geodesic
from geographiclib.polygonarea import PolygonArea
# ============================================================================ #



# ================================ PARAMETRES ================================ #
# Dossiers
root_directory = "analyse-cadastre-dvf"
cadastre_directory = "etalab-cadastre"
# ============================================================================ #



# ================================= DOSSIERS ================================= #
# Trouves le nom de dossier complet pour les données
def get_data_directory(root = root_directory):
    current = os.path.realpath('.')
    path = current.partition(root)[0] + os.sep + root + os.sep + "data" + os.sep
    return path
# ============================================================================ #



# ================================= DONNEES ================================== #
# Charge un fichier json du cadastre
def load_file(directory, code, kind):
    filename = directory.rstrip("/") + "/" + "cadastre-" + str(code) + "-"
    filename += kind + ".json"
    with open(filename) as stream:
        features = json.load(stream)["features"]
    return features
# ---------------------------------------------------------------------------- #
# Charge les données liées à une ville
def load_city(insee):
    code = str(insee)
    department = code[0:2]
    directory = get_data_directory().rstrip("/") + "/"
    directory += cadastre_directory + "/"
    directory += "2017-07-06" + "/" + "geojson" + "/" + "communes" + "/"
    directory += department + "/" + code + "/"
    directory = directory.replace("//", "/")
    files = {
        "batiments": load_file(directory, code, "batiments"),
        "communes": load_file(directory, code, "communes"),
        "feuilles": load_file(directory, code, "feuilles"),
        "parcelles": load_file(directory, code, "parcelles"),
        "sections": load_file(directory, code, "sections"),
    }
    return files
# ---------------------------------------------------------------------------- #
# Créé un tableau associatif associant un numero de parcelle a un element json
def make_land_mapping(json):
    mapping = {}
    for land in json:
        mapping[land["id"]] = land
    return mapping
# ---------------------------------------------------------------------------- #
# Créé un arbre pour l'analyse des bâtiments
def make_buildings_tree(json):
    shapes = [geom.shape(element["geometry"]).buffer(0) for element in json]
    collection = geom.GeometryCollection(shapes)
    return sptree.STRtree(collection)
# ============================================================================ #



# ================================= POLYGONE ================================= #
# Defini un polygone et calcule ses propriétés
class Polygon:
    # Constructeur
    def __init__(self, poly):
        # Converti le polygone en liste de points
        points_lon_lat = list(poly.exterior.coords)
        points_lat_lon = [(point[1], point[0]) for point in points_lon_lat]
        # Converti le rectangle en liste de points
        rectangle = poly.minimum_rotated_rectangle
        rpoints_lon_lat = list(rectangle.exterior.coords)
        rpoints_lat_lon = [(point[1], point[0]) for point in rpoints_lon_lat]
        # Converti le polygone dans la bonne projection
        wgs84 = Geodesic.WGS84
        geopoly = PolygonArea(wgs84)
        for point in points_lat_lon[0:-1]:
            geopoly.AddPoint(point[0], point[1])
        geopoly_result = geopoly.Compute()
        # Converti le rectangle dans la bonne projection
        georectangle = PolygonArea(wgs84)
        for point in rpoints_lat_lon[0:-1]:
            georectangle.AddPoint(point[0], point[1])
        georectangle_result = georectangle.Compute()
        # Calcule les dimensions du rectangle
        rdistance = []
        for i in range(0, 4):
            rdistance.append(wgs84.Inverse(
                rpoints_lat_lon[i % 4][0],
                rpoints_lat_lon[i % 4][1],
                rpoints_lat_lon[(i + 1) % 4][0],
                rpoints_lat_lon[(i + 1) % 4][1]
            )["s12"])
        rdistance = [
            abs((rdistance[0] + rdistance[2])/2.0),
            abs((rdistance[1] + rdistance[3])/2.0)
        ]
        # Données membres
        self.polygon = poly
        self.centroid = poly.centroid
        self.rectangle = poly.minimum_rotated_rectangle
        self.perimeter = abs(geopoly_result[1])
        self.area = abs(geopoly_result[2])
        self.rectangle_min = min(rdistance)
        self.rectangle_max = max(rdistance)
        self.rectangle_perimeter = abs(georectangle_result[1])
        self.rectangle_area = abs(georectangle_result[2])
        self.ratio = self.area / self.rectangle_area
        self.polygon_conversion = self.area / self.polygon.area
        self.rectangle_conversion = self.rectangle_area / self.rectangle.area
        self.nvertices = len(points_lon_lat) - 1
        self.nedges = self.nvertices
    # Retourne une version agrandie approximée du polygone
    def scaled(self, distance = 1):
        new_area = self.area + self.perimeter * distance
        new_area += self.nvertices * distance * distance
        ratio = new_area / self.area
        scaling = ratio ** (1./2.)
        new_polygon = spaff.scale(
            self.polygon,
            xfact = scaling,
            yfact = scaling,
            origin = "centroid"
        )
        return Polygon(new_polygon)
# ============================================================================ #



# ================================= ANALYSE ================================== #
# Analyse les données cadastrales d'une parcelle
def land_analyzer(name, json, mapping = None):
    # Initialisation
    land_json = None
    # Récupération du json de la parcelle
    if (mapping):
        land_json = mapping[name]
    else:
        for element in json:
            if (element["id"] == name):
                land_json = element
                break
    # Si la parcelle a été trouvée
    if (land_json):
        land_shape = geom.shape(land_json["geometry"])
        polygon = Polygon(land_shape)
        print(polygon.rectangle_min, polygon.rectangle_max, polygon.rectangle_min*polygon.rectangle_max, polygon.rectangle_area)
# -----------------------------------------------------------------------------#
# Trouve les batiments qui intersectent une parcelle
def find_buildings_on_land(land_polygon, buildings_tree):
    intersecting = []
    if (type(buildings_tree) != list):
        query = buildings_tree.query(land_polygon)
        for building_polygon in query:
            if (building_polygon.intersects(land_polygon)):
                intersecting.append(building_polygon)
    else:
        for building in buildings_tree:
            building_polygon = geom.shape(building["geometry"])
            if (building_polygon.intersects(land_polygon)):
                intersecting.append(building_polygon)
    return intersecting
# -----------------------------------------------------------------------------#
# Merge les batiments qui ont une frontiere commune
def merge_buildings(buildings_list):
    output = buildings_list
    if (buildings_list and len(buildings_list) > 0):
        output = spops.cascaded_union(buildings_list)
        if (type(output) == geom.multipolygon.MultiPolygon):
            output = list(output)
        elif (type(output) == geom.polygon.Polygon):
            output = [output]
        else:
            print("ERROR")
    return output
# -----------------------------------------------------------------------------#
# Découpe la partie des bâtiments qui intersecte le terrain
def crop_buildings(land_polygon, buildings_list, threshold = 1):
    output = buildings_list
    if (buildings_list and len(buildings_list) > 0):
        output = []
        tmp = [x.intersection(land_polygon) for x in buildings_list]
        for building in tmp:
            if (type(building) == geom.polygon.Polygon):
                polygon = Polygon(building)
                if (polygon.area > threshold):
                    output.append(building)
            elif (type(building) == geom.multipolygon.MultiPolygon):
                for b in building:
                    polygon = Polygon(b)
                    if (polygon.area > threshold):
                        output.append(b)
    return output
# -----------------------------------------------------------------------------#
# Tri une liste de polygones par taille
def sort_polygons(polygons_list):
    output = sorted(
        polygons_list,
        key = lambda polygon: Polygon(polygon).area,
        reverse = True
    )
    return output
# ============================================================================ #



# ================================= PROGRAMME ================================ #
# Programme principal
def main():
    city = load_city("01001")
    land_mapping = make_land_mapping(city["parcelles"])
    #land_analyzer("010010000A0002", city["parcelles"], land_mapping)
    buildings_tree = make_buildings_tree(city["batiments"])
    results = {}
    i = 0
    for land in city["parcelles"]:
        land_polygon = geom.shape(land["geometry"])
        intersecting = find_buildings_on_land(land_polygon, buildings_tree)
        grouped = merge_buildings(intersecting)
        cropped = crop_buildings(land_polygon, grouped)
        if (len(cropped) == 1):
            building_area = Polygon(cropped[0]).area
            land_area = Polygon(land_polygon).area
            if (land_area > 600 and land_area < 1000):
                if (building_area > 100 and building_area < 140):
                    print(land["id"], land_area, building_area)
        #if (len(grouped) > len(cropped)):
        #    print(i, land["id"], len(intersecting), len(grouped), len(cropped))
        #    i += 1
        #if (land["id"] == "01001000ZM0122"):
        #    print(land)
            #query = buildings_tree.query(land_polygon)
            #for element in query:
            #    points = list(element.exterior.coords)
            #    print(points)
            #    print(list(land_polygon.exterior.coords))
            #    break
# ---------------------------------------------------------------------------- #
main()
# ============================================================================ #
