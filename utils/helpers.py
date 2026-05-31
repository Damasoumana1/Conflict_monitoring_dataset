"""
utils/helpers.py
=================
Fonctions utilitaires partagées entre les collecteurs.
"""

import hashlib
import requests
from pathlib import Path
from loguru import logger


def verify_md5(filepath: Path, expected_md5: str) -> bool:
    """
    Vérifie l'intégrité d'un fichier téléchargé via son hash MD5.

    Args:
        filepath: Chemin vers le fichier local
        expected_md5: Hash MD5 attendu (fourni par GDELT)

    Returns:
        True si le fichier est intact, False sinon
    """
    md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    computed = md5.hexdigest()
    if computed != expected_md5:
        logger.warning(f"MD5 mismatch pour {filepath.name}: attendu {expected_md5}, obtenu {computed}")
        return False
    return True


def check_internet_connection(url: str = "http://data.gdeltproject.org", timeout: int = 5) -> bool:
    """
    Vérifie que le serveur GDELT est accessible.

    Returns:
        True si accessible, False sinon
    """
    try:
        requests.get(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        logger.error(f"❌ Impossible de se connecter à {url}. Vérifiez votre connexion internet.")
        return False


def format_size(size_bytes: int) -> str:
    """
    Formate une taille en octets en chaîne lisible (KB, MB, GB).

    Args:
        size_bytes: Taille en octets

    Returns:
        Chaîne formatée, ex: "42.3 MB"
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
