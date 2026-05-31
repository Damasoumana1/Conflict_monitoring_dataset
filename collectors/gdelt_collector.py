"""
collectors/gdelt_collector.py
==============================
Collecteur principal pour les données GDELT V2.

Fonctionnalités :
- Téléchargement de la liste maîtresse des fichiers
- Filtrage par type (events, mentions, gkg) et par plage de dates
- Téléchargement et décompression des fichiers .zip
- Filtrage géographique (pays africains)
- Sauvegarde en CSV et Parquet
"""

import io
import time
import zipfile
import requests
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from loguru import logger
from datetime import datetime, timedelta
from typing import List, Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import (
    GDELT_CONFIG,
    GDELT_EVENT_COLUMNS,
    COLUMNS_TO_KEEP,
    RAW_DIR,
    PROCESSED_DIR,
    LOGS_DIR,
)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION DU LOGGER
# ─────────────────────────────────────────────────────────────────────────────

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO",
)
logger.add(
    LOGS_DIR / "gdelt_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
)


# ─────────────────────────────────────────────────────────────────────────────
# CLASSE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

class GDELTCollector:
    """
    Collecteur GDELT V2 — télécharge et pré-traite les fichiers d'événements.

    Utilisation rapide :
        collector = GDELTCollector()
        collector.run()
    """

    def __init__(self):
        self.config = GDELT_CONFIG
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ConflictMonitoringDataset/1.0 (Academic Research Project)"
        })

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 1 : Récupérer la liste des fichiers disponibles
    # ──────────────────────────────────────────────────────────────────────────

    def fetch_master_file_list(self) -> pd.DataFrame:
        """
        Télécharge la liste maîtresse de tous les fichiers GDELT V2.
        Retourne un DataFrame avec les colonnes : size, hash, url
        """
        logger.info("📋 Récupération de la liste maîtresse GDELT V2...")
        url = self.config["master_file_url"]

        try:
            response = self.session.get(url, timeout=self.config["request_timeout"])
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Impossible de récupérer la liste maîtresse : {e}")
            raise

        lines = response.text.strip().split("\n")
        records = []
        for line in lines:
            parts = line.strip().split(" ")
            if len(parts) == 3:
                size, md5, file_url = parts
                records.append({
                    "size": int(size),
                    "md5": md5,
                    "url": file_url,
                    "filename": file_url.split("/")[-1],
                })

        df = pd.DataFrame(records)
        logger.success(f"✅ {len(df)} fichiers trouvés dans la liste maîtresse.")
        return df

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 2 : Filtrer les fichiers selon la config
    # ──────────────────────────────────────────────────────────────────────────

    def filter_files(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filtre les fichiers par :
        - Type (events, mentions, gkg)
        - Plage de dates (date_start / date_end)
        - Limite du nombre de fichiers
        """
        file_types = self.config["file_types"]
        date_start = self.config.get("date_start")
        date_end = self.config.get("date_end")
        max_files = self.config.get("max_files")

        original_count = len(df)

        # ── Filtrage par type de fichier ──────────────────────────────────────
        # Les noms de fichiers GDELT V2 ont ce format :
        #   20240115120000.export.CSV.zip   → events
        #   20240115120000.mentions.CSV.zip → mentions
        #   20240115120000.gkg.csv.zip      → gkg

        type_patterns = {
            "events":   ".export.",
            "mentions": ".mentions.",
            "gkg":      ".gkg.",
        }

        masks = []
        for t in file_types:
            if t in type_patterns:
                masks.append(df["filename"].str.contains(type_patterns[t], na=False))

        if masks:
            combined_mask = masks[0]
            for m in masks[1:]:
                combined_mask = combined_mask | m
            df = df[combined_mask].copy()

        logger.info(f"🔍 Après filtre type ({file_types}): {len(df)}/{original_count} fichiers")

        # ── Filtrage par dates ────────────────────────────────────────────────
        # Extraire la date depuis le nom du fichier (les 8 premiers caractères = YYYYMMDD)
        df["file_date"] = pd.to_datetime(df["filename"].str[:8], format="%Y%m%d", errors="coerce")
        df = df.dropna(subset=["file_date"])

        if date_start:
            df = df[df["file_date"] >= pd.to_datetime(date_start)]
        if date_end:
            df = df[df["file_date"] <= pd.to_datetime(date_end)]

        logger.info(
            f"📅 Après filtre dates ({date_start} → {date_end}): {len(df)} fichiers"
        )

        # ── Limite du nombre de fichiers ──────────────────────────────────────
        if max_files and len(df) > max_files:
            df = df.head(max_files)
            logger.warning(
                f"⚠️  Limite appliquée : seulement {max_files} fichiers seront traités."
            )

        return df.reset_index(drop=True)

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 3 : Télécharger et décompresser un fichier
    # ──────────────────────────────────────────────────────────────────────────

    def download_and_extract(self, file_url: str, filename: str) -> Optional[pd.DataFrame]:
        """
        Télécharge un fichier .zip GDELT, le décompresse en mémoire
        et retourne un DataFrame pandas.
        """
        try:
            logger.debug(f"⬇️  Téléchargement : {filename}")
            response = self.session.get(
                file_url, timeout=self.config["request_timeout"], stream=True
            )
            response.raise_for_status()

            # Décompression en mémoire (pas de fichier temporaire sur disque)
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                inner_filename = zf.namelist()[0]
                with zf.open(inner_filename) as f:
                    df = pd.read_csv(
                        f,
                        sep="\t",
                        header=None,
                        names=GDELT_EVENT_COLUMNS,
                        dtype=str,       # tout en str pour éviter les erreurs de parsing
                        low_memory=False,
                    )

            logger.debug(f"   → {len(df)} lignes extraites de {filename}")
            return df

        except zipfile.BadZipFile:
            logger.warning(f"⚠️  Fichier ZIP corrompu ignoré : {filename}")
            return None
        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement de {filename}: {e}")
            return None

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 4 : Filtrer géographiquement
    # ──────────────────────────────────────────────────────────────────────────

    def apply_geo_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Conserve uniquement les événements dont ActionGeo_CountryCode
        correspond aux pays configurés dans country_filter.
        """
        country_filter = self.config.get("country_filter", [])
        if not country_filter:
            return df

        # GDELT utilise des codes FIPS-10 à 2 lettres (proches ISO mais pas identiques)
        # La colonne ActionGeo_CountryCode est en 2 lettres majuscules
        mask = df["ActionGeo_CountryCode"].isin(country_filter)
        filtered = df[mask]

        return filtered

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 5 : Nettoyage & conversion des types
    # ──────────────────────────────────────────────────────────────────────────

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sélectionne les colonnes utiles et convertit les types de données.
        """
        # Garder seulement les colonnes configurées
        available_cols = [c for c in COLUMNS_TO_KEEP if c in df.columns]
        df = df[available_cols].copy()

        # Conversions numériques
        numeric_cols = [
            "GoldsteinScale", "NumMentions", "NumArticles",
            "AvgTone", "ActionGeo_Lat", "ActionGeo_Long",
            "QuadClass",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Conversion de la date
        if "Day" in df.columns:
            df["date"] = pd.to_datetime(df["Day"], format="%Y%m%d", errors="coerce")

        # Supprimer les lignes sans coordonnées géographiques
        if "ActionGeo_Lat" in df.columns and "ActionGeo_Long" in df.columns:
            df = df.dropna(subset=["ActionGeo_Lat", "ActionGeo_Long"])

        return df.reset_index(drop=True)

    # ──────────────────────────────────────────────────────────────────────────
    # ÉTAPE 6 : Sauvegarde
    # ──────────────────────────────────────────────────────────────────────────

    def save(self, df: pd.DataFrame, label: str = "gdelt_events"):
        """
        Sauvegarde le DataFrame en CSV et en Parquet dans data/processed/.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{label}_{timestamp}"

        csv_path = PROCESSED_DIR / f"{base_name}.csv"
        parquet_path = PROCESSED_DIR / f"{base_name}.parquet"

        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        logger.success(f"💾 CSV sauvegardé : {csv_path}  ({len(df)} lignes)")

        try:
            df.to_parquet(parquet_path, index=False)
            logger.success(f"💾 Parquet sauvegardé : {parquet_path}")
        except Exception as e:
            logger.warning(f"Parquet non disponible ({e}). Seul le CSV a été sauvegardé.")

        return csv_path

    # ──────────────────────────────────────────────────────────────────────────
    # POINT D'ENTRÉE PRINCIPAL
    # ──────────────────────────────────────────────────────────────────────────

    def run(self):
        """
        Exécute le pipeline complet de collecte GDELT.

        Pipeline :
          1. Récupérer la liste maîtresse
          2. Filtrer les fichiers à télécharger
          3. Télécharger + décompresser chaque fichier
          4. Filtrer géographiquement
          5. Nettoyer
          6. Combiner et sauvegarder
        """
        logger.info("=" * 60)
        logger.info("🚀 Démarrage de la collecte GDELT V2")
        logger.info("=" * 60)

        # Étape 1 & 2
        master_df = self.fetch_master_file_list()
        files_to_download = self.filter_files(master_df)

        if files_to_download.empty:
            logger.warning("Aucun fichier ne correspond aux critères. Vérifiez votre config.")
            return

        logger.info(f"📦 {len(files_to_download)} fichier(s) à traiter.")

        # Étape 3, 4, 5 — pour chaque fichier
        all_frames: List[pd.DataFrame] = []
        sleep_time = self.config.get("sleep_between_downloads", 1)

        for _, row in tqdm(files_to_download.iterrows(), total=len(files_to_download), desc="GDELT"):
            df_raw = self.download_and_extract(row["url"], row["filename"])

            if df_raw is None or df_raw.empty:
                continue

            # Filtre géographique
            df_geo = self.apply_geo_filter(df_raw)

            if df_geo.empty:
                logger.debug(f"   → 0 événements après filtre géo pour {row['filename']}")
                continue

            # Nettoyage
            df_clean = self.clean_dataframe(df_geo)
            all_frames.append(df_clean)

            logger.info(
                f"   ✓ {row['filename']} → {len(df_clean)} événements retenus"
            )

            # Pause courtoise entre les requêtes
            time.sleep(sleep_time)

        # Étape 6 — Combinaison et sauvegarde
        if not all_frames:
            logger.warning("Aucun événement collecté. Vérifiez vos filtres.")
            return

        final_df = pd.concat(all_frames, ignore_index=True)
        final_df = final_df.drop_duplicates(subset=["GlobalEventID"])

        logger.info(f"\n📊 Total : {len(final_df)} événements uniques collectés.")
        saved_path = self.save(final_df)

        logger.info("=" * 60)
        logger.success(f"✅ Collecte terminée ! Fichier : {saved_path}")
        logger.info("=" * 60)

        return final_df
