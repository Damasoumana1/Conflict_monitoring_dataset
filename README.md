# 🌍 Conflict Monitoring Dataset

> **Projet académique** — Collecte et analyse des données de conflits en Afrique de l'Ouest.  
> Sources : [GDELT Project](https://www.gdeltproject.org/) · [ACLED](https://acleddata.com/) *(à venir)*

---

## 📁 Structure du projet

```
Conflict_monitoring_dataset/
│
├── main.py                     ← Point d'entrée principal (lancer ici)
├── config.py                   ← ⚙️  Configuration (dates, pays, filtres...)
├── requirements.txt            ← Dépendances Python
│
├── collectors/
│   ├── __init__.py
│   └── gdelt_collector.py      ← Collecteur GDELT V2 complet
│
├── utils/
│   ├── __init__.py
│   └── helpers.py              ← Fonctions utilitaires
│
├── data/
│   ├── raw/                    ← Données brutes (ignorées par git)
│   └── processed/              ← Données nettoyées (CSV + Parquet)
│
└── logs/                       ← Logs d'exécution
```

---

## 🚀 Installation & Démarrage rapide

### 1. Cloner le dépôt

```bash
git clone https://github.com/VOTRE_USERNAME/Conflict_monitoring_dataset.git
cd Conflict_monitoring_dataset
```

### 2. Créer un environnement virtuel Python

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer la collecte

Ouvrez [`config.py`](config.py) et ajustez selon vos besoins :

| Paramètre | Description | Valeur par défaut |
|---|---|---|
| `date_start` | Début de la période | `"2024-01-01"` |
| `date_end` | Fin de la période | `"2024-03-31"` |
| `max_files` | Limite de fichiers | `10` |
| `country_filter` | Codes pays ISO (Afrique de l'Ouest) | 15 pays pré-configurés |
| `file_types` | Types de données GDELT | `["events"]` |

### 5. Lancer la collecte

```bash
# Collecte standard (selon config.py)
python main.py

# Mode test rapide (3 fichiers seulement, pour vérifier l'installation)
python main.py --test

# Plage de dates personnalisée
python main.py --start 2024-06-01 --end 2024-06-30

# Limiter à 5 fichiers
python main.py --max-files 5
```

---

## 📊 Données collectées

### Source : GDELT V2 (Global Database of Events, Language, and Tone)

GDELT est mis à jour **toutes les 15 minutes** et surveille les actualités mondiales.  
Chaque fichier d'événements contient les colonnes suivantes (sélection) :

| Colonne | Description |
|---|---|
| `GlobalEventID` | Identifiant unique de l'événement |
| `Day` | Date (format YYYYMMDD) |
| `Actor1Name` / `Actor2Name` | Acteurs impliqués |
| `ActionGeo_CountryCode` | Pays de l'action |
| `ActionGeo_Lat` / `ActionGeo_Long` | **Coordonnées GPS** ← clé pour la cartographie |
| `EventCode` | Code CAMEO de l'événement |
| `QuadClass` | Catégorie (3=Conflit verbal, 4=Conflit matériel) |
| `GoldsteinScale` | Score d'impact (-10 à +10) |
| `AvgTone` | Ton médiatique moyen |
| `SOURCEURL` | URL de l'article source |

### Fichiers de sortie

Après collecte, les fichiers sont sauvegardés dans `data/processed/` :
- `gdelt_events_YYYYMMDD_HHMMSS.csv` — Format CSV (compatible Excel)
- `gdelt_events_YYYYMMDD_HHMMSS.parquet` — Format optimisé (analyse Python/R)

---

## 🌐 Codes CAMEO — QuadClass

| Code | Catégorie | Exemples |
|---|---|---|
| 1 | Coopération verbale | Déclarations diplomatiques |
| 2 | Coopération matérielle | Aide humanitaire |
| **3** | **Conflit verbal** | Menaces, accusations, protestations |
| **4** | **Conflit matériel** | Combats, attaques, violence |

> Le collecteur filtre par défaut sur `QuadClass = [3, 4]` pour les événements de conflit.

---

## 🗺️ Pays préconfigurés (Afrique de l'Ouest)

| Code | Pays | Code | Pays |
|---|---|---|---|
| CI | Côte d'Ivoire | SN | Sénégal |
| ML | Mali | NG | Nigeria |
| BF | Burkina Faso | GH | Ghana |
| NE | Niger | GN | Guinée |
| TG | Togo | BJ | Bénin |
| MR | Mauritanie | GM | Gambie |
| GW | Guinée-Bissau | SL | Sierra Leone |
| LR | Liberia | | |

Pour ajouter d'autres pays, modifiez `country_filter` dans [`config.py`](config.py).

---

## 📚 Ressources & Documentation

- 📖 [Codebook GDELT V2](http://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf)
- 📖 [Manuel CAMEO](https://www.gdeltproject.org/data/documentation/CAMEO.Manual.1.1b3.pdf)
- 🔗 [Liste maîtresse des fichiers GDELT](http://data.gdeltproject.org/gdeltv2/masterfilelist.txt)
- 🔗 [ACLED Data Export Tool](https://acleddata.com/conflict-data/data-export-tool)

---

## 👥 Équipe

Projet académique — *Conflict Monitoring in West Africa*

---

## 📝 Licence

Usage académique uniquement. Les données GDELT sont sous licence Creative Commons.
