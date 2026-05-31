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
import os
import time
import zipfile
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
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

CACHE_FILE = "master_file_cache.csv"
CACHE_DIR = Path("cache_gdelt")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


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

        retry = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )

        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

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

        if os.path.exists(CACHE_FILE):
            logger.info("📦 Chargement du cache local master file")
            return pd.read_csv(CACHE_FILE)

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
        df.to_csv(CACHE_FILE, index=False)
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
        df = df.loc[:, available_cols]

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

        # Étape 3, 4, 5 — traitement en batch et écriture sur disque
        output_file = PROCESSED_DIR / "gdelt_stream.parquet"
        output_csv = PROCESSED_DIR / "gdelt_stream.csv"
        max_workers = self.config.get("max_workers", 5)
        batch_size = self.config.get("batch_size", 10)
        results: List[pd.DataFrame] = []
        fallback_to_csv = False
        total_events = 0
        processed_files = 0

        for batch_start in range(0, len(files_to_download), batch_size):
            batch = files_to_download.iloc[batch_start : batch_start + batch_size]
            results.clear()

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(self.process_file, row)
                    for _, row in batch.iterrows()
                ]

                for f in tqdm(as_completed(futures), total=len(futures), desc="GDELT"):
                    df = f.result()
                    if df is not None and not df.empty:
                        results.append(df)

            for df in results:
                try:
                    if not fallback_to_csv:
                        if output_file.exists():
                            df.to_parquet(output_file, engine="pyarrow", index=False, append=True)
                        else:
                            df.to_parquet(output_file, engine="pyarrow", index=False)
                        output_path = output_file
                    else:
                        raise RuntimeError("fallback-to-csv")
                except Exception as e:
                    fallback_to_csv = True
                    logger.warning(f"Parquet append impossible, bascule sur CSV : {e}")
                    if output_csv.exists():
                        df.to_csv(output_csv, mode="a", header=False, index=False, encoding="utf-8-sig")
                    else:
                        df.to_csv(output_csv, mode="w", header=True, index=False, encoding="utf-8-sig")
                    output_path = output_csv

                total_events += len(df)
                processed_files += 1

        if processed_files == 0:
            logger.warning("Aucun événement collecté. Vérifiez vos filtres.")
            return

        logger.info(f"\n📊 Total : {total_events} événements collectés sur {processed_files} fichier(s).")
        logger.info("=" * 60)
        logger.success(f"✅ Collecte terminée ! Fichier : {output_path}")
        logger.info("=" * 60)

        return output_path
