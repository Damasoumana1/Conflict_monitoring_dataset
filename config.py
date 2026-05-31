"""
config.py — Configuration centralisée du projet Conflict Monitoring Dataset
===========================================================================
Modifiez les paramètres ici selon vos besoins de recherche.
"""

from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# CHEMINS DU PROJET
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
LOGS_DIR = BASE_DIR / "logs"

# Créer les dossiers si nécessaire
for folder in [RAW_DIR, PROCESSED_DIR, LOGS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# GDELT V2 — CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

GDELT_CONFIG = {
    # URL de la liste maîtresse des fichiers GDELT V2 (mis à jour toutes les 15 min)
    "master_file_url": "http://data.gdeltproject.org/gdeltv2/masterfilelist.txt",

    # URL de la liste des derniers fichiers (utile pour la collecte incrémentale)
    "last_update_url": "http://data.gdeltproject.org/gdeltv2/lastupdate.txt",

    # URL de base pour les téléchargements directs
    "base_url": "http://data.gdeltproject.org/gdeltv2/",

    # Nombre maximum de fichiers à télécharger par session (None = illimité)
    # ⚠️  GDELT est très volumineux. Commencez par un petit nombre pour tester.
    "max_files": 10,

    # Plage de dates pour la collecte (format: YYYY-MM-DD)
    # Laisser None pour prendre les données les plus récentes
    "date_start": "2024-01-01",
    "date_end": "2024-03-31",

    # Types de fichiers GDELT V2 à collecter
    # "events"   → Fichiers d'événements (GDELT 2.0 Event Database)
    # "mentions" → Fichiers de mentions (articles qui parlent des événements)
    # "gkg"      → Graph of Knowledge globale (thèmes, entités, tons)
    "file_types": ["events"],   # Modifier selon vos besoins

    # Filtres géographiques (codes pays ISO-Alpha2)
    # Exemples Afrique : "CI","SN","ML","BF","NG","CD","SO","ET","SD","LY"
    # Laisser vide [] pour ne PAS filtrer (téléchargement global)
    "country_filter": [],

    # Timeout en secondes pour les requêtes HTTP
    "request_timeout": 60,

    # Nombre de secondes à attendre entre deux téléchargements (politesse serveur)
    "sleep_between_downloads": 1,
}


# ─────────────────────────────────────────────────────────────────────────────
# COLONNES GDELT V2 — ÉVÉNEMENTS
# Référence: http://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf
# ─────────────────────────────────────────────────────────────────────────────

GDELT_EVENT_COLUMNS = [
    "GlobalEventID",       # ID unique de l'événement
    "Day",                 # Date (YYYYMMDD)
    "MonthYear",           # Mois (YYYYMM)
    "Year",                # Année
    "FractionDate",        # Date fractionnelle (pour tri)
    "Actor1Code",          # Code acteur 1
    "Actor1Name",          # Nom acteur 1
    "Actor1CountryCode",   # Pays acteur 1 (ISO Alpha-3)
    "Actor1Type1Code",     # Type acteur 1
    "Actor2Code",          # Code acteur 2
    "Actor2Name",          # Nom acteur 2
    "Actor2CountryCode",   # Pays acteur 2
    "Actor2Type1Code",     # Type acteur 2
    "IsRootEvent",         # Événement racine (1/0)
    "EventCode",           # Code CAMEO de l'événement
    "EventBaseCode",       # Code CAMEO de base
    "EventRootCode",       # Code CAMEO racine
    "QuadClass",           # Classe quadrant (1=Verbal Coop, 2=Mat Coop, 3=Verbal Conf, 4=Mat Conf)
    "GoldsteinScale",      # Score Goldstein (-10 à +10)
    "NumMentions",         # Nombre de mentions
    "NumSources",          # Nombre de sources
    "NumArticles",         # Nombre d'articles
    "AvgTone",             # Ton moyen de la couverture médiatique
    "Actor1Geo_Type",      # Type géo acteur 1
    "Actor1Geo_FullName",  # Nom géo complet acteur 1
    "Actor1Geo_CountryCode", # Code pays géo acteur 1
    "Actor1Geo_Lat",       # Latitude acteur 1
    "Actor1Geo_Long",      # Longitude acteur 1
    "Actor2Geo_Type",      # Type géo acteur 2
    "Actor2Geo_FullName",  # Nom géo complet acteur 2
    "Actor2Geo_CountryCode", # Code pays géo acteur 2
    "Actor2Geo_Lat",       # Latitude acteur 2
    "Actor2Geo_Long",      # Longitude acteur 2
    "ActionGeo_Type",      # Type géo action
    "ActionGeo_FullName",  # Nom géo complet action
    "ActionGeo_CountryCode", # Code pays géo action
    "ActionGeo_Lat",       # Latitude action ← clé pour la cartographie
    "ActionGeo_Long",      # Longitude action ← clé pour la cartographie
    "DATEADDED",           # Date d'ajout dans GDELT
    "SOURCEURL",           # URL de l'article source
]

# Colonnes à garder lors du nettoyage (subset pour économiser l'espace)
COLUMNS_TO_KEEP = [
    "GlobalEventID",
    "Day",
    "Year",
    "Actor1Name",
    "Actor1CountryCode",
    "Actor2Name",
    "Actor2CountryCode",
    "EventCode",
    "QuadClass",
    "GoldsteinScale",
    "NumMentions",
    "NumArticles",
    "AvgTone",
    "ActionGeo_FullName",
    "ActionGeo_CountryCode",
    "ActionGeo_Lat",
    "ActionGeo_Long",
    "SOURCEURL",
]


# ─────────────────────────────────────────────────────────────────────────────
# CODES CAMEO — QuadClass (pour filtrage des conflits)
# ─────────────────────────────────────────────────────────────────────────────

# QuadClass = 4 → Conflit matériel (violence physique, combats, etc.)
# QuadClass = 3 → Conflit verbal (menaces, accusations, protestations)
CONFLICT_QUAD_CLASSES = [3, 4]

# Codes CAMEO racines pour les événements violents
# Référence: https://www.gdeltproject.org/data/documentation/CAMEO.Manual.1.1b3.pdf
VIOLENT_EVENT_ROOT_CODES = [
    "13",  # Menacer
    "14",  # Protester
    "17",  # Réduire les relations
    "18",  # Assaut
    "19",  # Combattre
    "20",  # Violence de masse
]
