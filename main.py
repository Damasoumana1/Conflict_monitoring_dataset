"""
main.py — Point d'entrée du projet Conflict Monitoring Dataset
==============================================================
Lancez ce fichier pour démarrer la collecte :

    python main.py                          # collecte GDELT avec la config par défaut
    python main.py --source gdelt           # idem (explicite)
    python main.py --source gdelt --test    # mode test (seulement 3 fichiers)
"""

import argparse
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# ARGUMENTS CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Conflict Monitoring Dataset — Collecteur de données",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python main.py                      # Lance la collecte GDELT
  python main.py --source gdelt       # Idem (explicite)
  python main.py --test               # Mode test rapide (3 fichiers seulement)
  python main.py --start 2024-01-01 --end 2024-01-31  # Plage de dates personnalisée
        """,
    )

    parser.add_argument(
        "--source",
        choices=["gdelt"],
        default="gdelt",
        help="Source de données à collecter (défaut: gdelt)",
    )
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="Date de début (format YYYY-MM-DD). Écrase config.py.",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="Date de fin (format YYYY-MM-DD). Écrase config.py.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Nombre maximum de fichiers à traiter. Écrase config.py.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Mode test : traite seulement 3 fichiers pour vérifier que tout fonctionne.",
    )

    return parser.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    # ── Import du collecteur ──────────────────────────────────────────────────
    from collectors import GDELTCollector
    import config

    # ── Surcharge de la config via CLI ────────────────────────────────────────
    if args.start:
        config.GDELT_CONFIG["date_start"] = args.start
    if args.end:
        config.GDELT_CONFIG["date_end"] = args.end
    if args.max_files:
        config.GDELT_CONFIG["max_files"] = args.max_files
    if args.test:
        config.GDELT_CONFIG["max_files"] = 3
        print("🧪 Mode test activé : 3 fichiers seulement.\n")

    # ── Lancement de la collecte ──────────────────────────────────────────────
    if args.source == "gdelt":
        collector = GDELTCollector()
        collector.run()
    else:
        print(f"Source inconnue : {args.source}")
        sys.exit(1)


if __name__ == "__main__":
    main()
