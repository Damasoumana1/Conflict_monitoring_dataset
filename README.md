# 🌍 Conflict Monitoring Dataset

> **Projet académique** — Collecte et analyse des données de conflits en Afrique de l'Ouest.  
> Sources : [GDELT Project](https://www.gdeltproject.org/) · [ACLED](https://acleddata.com/) · [UCDP](https://ucdp.uu.se/) · [ReliefWeb](https://reliefweb.int/) · [UN OCHA](https://data.humdata.org/)

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
│   ├── gdelt_collector.py      ← Collecteur GDELT V2 ✅ (implémenté)
│   ├── acled_collector.py      ← Collecteur ACLED 🔜 (à implémenter)
│   └── ucdp_collector.py       ← Collecteur UCDP 🔜 (à implémenter)
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
git clone https://github.com/Damasoumana1/Conflict_monitoring_dataset.git
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

## 🗃️ Autres sources de données — Comment les exploiter

### 1. 🔴 ACLED — Armed Conflict Location & Event Data

> Données géolocalisées sur les violences politiques et les protestations. Idéal pour les événements précis avec acteurs et victimes.

**Accès :**
1. Créer un compte sur [myACLED](https://developer.acleddata.com/) avec une adresse académique
2. Récupérer votre **clé API** et votre **email** dans le tableau de bord

**Téléchargement via API :**
```python
import requests
import pandas as pd

params = {
    "email":   "votre_email@univ.edu",
    "key":     "VOTRE_CLE_API",
    "country": "Burkina Faso|Mali|Niger",   # séparés par |
    "year":    "2024",
    "limit":   5000,
    "format":  "json",
}
r = requests.get("https://api.acleddata.com/acled/read", params=params)
df = pd.DataFrame(r.json()["data"])
df.to_csv("data/processed/acled_events.csv", index=False)
```

**Colonnes clés :**

| Colonne | Description |
|---|---|
| `event_date` | Date de l'événement |
| `event_type` | Type (Battles, Explosions, Violence against civilians…) |
| `country` / `location` | Pays et ville |
| `latitude` / `longitude` | Coordonnées GPS |
| `fatalities` | Nombre de morts |
| `actor1` / `actor2` | Groupes impliqués |

📖 [Documentation API ACLED](https://developer.acleddata.com/rehd/cms/views/acled_api/rulebook/)

---

### 2. 🔵 UCDP — Uppsala Conflict Data Program

> Base académique de référence sur les conflits armés depuis 1946. Données annuelles très fiables.

**Accès direct (pas de clé API nécessaire) :**
```python
import requests
import pandas as pd

# API GED (Georeferenced Event Dataset)
url = "https://ucdpapi.pcr.uu.se/api/gedevents/23.1"
params = {
    "pagesize": 1000,
    "page":     1,
    "Country":  "Burkina Faso",   # un pays à la fois
}
r = requests.get(url, params=params)
df = pd.DataFrame(r.json()["Result"])
df.to_csv("data/processed/ucdp_events.csv", index=False)
```

**Types de datasets UCDP :**

| Dataset | Description | Format |
|---|---|---|
| GED (Georeferenced Event) | Incidents individuels géolocalisés | CSV / API |
| PRIO-GRID | Données agrégées par grille géo | CSV |
| Dyadic Dataset | Conflits entre paires d'acteurs | CSV |

📖 [API UCDP](https://ucdpapi.pcr.uu.se/) · [Téléchargement direct](https://ucdp.uu.se/downloads/)

---

### 3. 🟠 ReliefWeb — Rapports humanitaires (OCHA/UN)

> Rapports de situation, alertes humanitaires, cartes de crises. Utile pour enrichir les données avec du contexte textuel.

**API gratuite, sans inscription :**
```python
import requests
import pandas as pd

url = "https://api.reliefweb.int/v1/reports"
params = {
    "appname":        "conflict-monitoring-research",
    "filter[field]":  "country.name",
    "filter[value]":  "Mali",
    "fields[include][]": ["title", "date", "url", "body-html"],
    "limit":          50,
}
r = requests.get(url, params=params)
data = r.json()["data"]
df = pd.json_normalize(data)
df.to_csv("data/processed/reliefweb_reports.csv", index=False)
```

📖 [Documentation API ReliefWeb](https://apidoc.reliefweb.int/)

---

### 4. 🟣 HDX — Humanitarian Data Exchange (UN OCHA)

> Jeux de données humanitaires ouverts : déplacements, population, infrastructures.

**Accès :** [data.humdata.org](https://data.humdata.org/)  
**Méthode :** Téléchargement direct CSV ou via l'API CKAN.

```python
import requests, pandas as pd

# Exemple : données de déplacements (IDP) au Mali
url = "https://data.humdata.org/api/3/action/datastore_search"
params = {"resource_id": "ID_RESSOURCE_HDX", "limit": 500}
r = requests.get(url, params=params)
df = pd.DataFrame(r.json()["result"]["records"])
```

📖 [API HDX/CKAN](https://docs.ckan.org/en/latest/api/)

---

### 📊 Tableau comparatif des sources

| Source | Accès | Mise à jour | Granularité | Points forts |
|---|---|---|---|---|
| **GDELT** | Gratuit, open | Toutes les 15 min | Événement médiatique | Volume, temps réel |
| **ACLED** | Clé API (gratuit académique) | Hebdomadaire | Incident précis | Victimes, acteurs |
| **UCDP** | Gratuit, open API | Annuelle | Incident géolocalisé | Référence académique |
| **ReliefWeb** | Gratuit, open API | Quotidienne | Rapport/Document | Contexte humanitaire |
| **HDX** | Gratuit, open | Variable | Dataset thématique | Données officielles ONU |

---

## 👥 Collaboration — Workflow Git pour l'équipe

### Inviter un collaborateur

1. Aller sur [github.com/Damasoumana1/Conflict_monitoring_dataset](https://github.com/Damasoumana1/Conflict_monitoring_dataset)
2. **Settings** → **Collaborators** → **Add people**
3. Entrer le nom d'utilisateur ou l'email GitHub du collègue
4. Le collègue accepte l'invitation reçue par email

### Workflow recommandé (une branche par fonctionnalité)

```bash
# 1. Cloner le dépôt
git clone https://github.com/Damasoumana1/Conflict_monitoring_dataset.git
cd Conflict_monitoring_dataset

# 2. Créer sa propre branche de travail
git checkout -b feature/acled-collector      # exemple pour ACLED
git checkout -b feature/ucdp-collector       # exemple pour UCDP
git checkout -b feature/data-visualization   # exemple pour les graphiques

# 3. Travailler, puis sauvegarder
git add .
git commit -m "feat: add ACLED collector with API key support"

# 4. Pousser sa branche sur GitHub
git push origin feature/acled-collector

# 5. Créer une Pull Request sur GitHub → Review → Merge dans main
```

### Branches suggérées pour l'équipe

| Branche | Responsable | Objectif |
|---|---|---|
| `main` | Damasoumana1 | Code stable et validé ✅ |
| `feature/acled-collector` | Collègue 1 | Intégration API ACLED |
| `feature/ucdp-collector` | Collègue 2 | Intégration API UCDP |
| `feature/data-visualization` | Équipe | Cartes & graphiques |
| `feature/data-merging` | Équipe | Fusion des sources |

> ⚠️ **Règle d'équipe** : Ne jamais commit directement sur `main`. Toujours passer par une branche + Pull Request.

### Mettre à jour sa branche locale avec les derniers changements

```bash
git checkout main
git pull origin main

git checkout feature/ma-branche
git merge main    # intégrer les dernières mises à jour de main
```

---

## 📚 Ressources & Documentation

- 📖 [Codebook GDELT V2](http://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf)
- 📖 [Manuel CAMEO](https://www.gdeltproject.org/data/documentation/CAMEO.Manual.1.1b3.pdf)
- 🔗 [Liste maîtresse des fichiers GDELT](http://data.gdeltproject.org/gdeltv2/masterfilelist.txt)
- 🔗 [ACLED Data Export Tool](https://acleddata.com/conflict-data/data-export-tool)
- 🔗 [API ACLED](https://developer.acleddata.com/rehd/cms/views/acled_api/rulebook/)
- 🔗 [UCDP Downloads](https://ucdp.uu.se/downloads/)
- 🔗 [ReliefWeb API](https://apidoc.reliefweb.int/)
- 🔗 [HDX — Humanitarian Data Exchange](https://data.humdata.org/)

---

## 👥 Équipe

Projet académique — *Conflict Monitoring in West Africa*

---

## 📝 Licence

Usage académique uniquement. Les données GDELT sont sous licence Creative Commons.  
Les données ACLED requièrent une attribution : *Armed Conflict Location & Event Data Project (ACLED); www.acleddata.com*
