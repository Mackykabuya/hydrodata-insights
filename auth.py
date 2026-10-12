"""
HydroData Insights - Module d'authentification.

Les comptes sont stockés dans `users.json` (mots de passe hachés avec PBKDF2-SHA256
et un sel aléatoire). Un compte administrateur de démonstration est créé au
premier lancement : identifiant `admin`, mot de passe `admin123`
(à changer en production).
"""

import hashlib
import hmac
import json
import os
import re
import secrets

FICHIER_UTILISATEURS = "users.json"
ITERATIONS = 120_000


def _hacher(mot_de_passe: str, sel: str) -> str:
    """Retourne le hachage PBKDF2 du mot de passe."""
    return hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode(), bytes.fromhex(sel), ITERATIONS).hex()


def _charger() -> dict:
    """Charge la base d'utilisateurs, en créant le compte de démonstration si besoin."""
    if not os.path.exists(FICHIER_UTILISATEURS):
        sel = secrets.token_hex(16)
        base = {"admin": {"sel": sel, "hash": _hacher("admin123", sel), "nom": "Administrateur"}}
        _sauvegarder(base)
        return base
    with open(FICHIER_UTILISATEURS, "r", encoding="utf-8") as f:
        return json.load(f)


def _sauvegarder(base: dict) -> None:
    with open(FICHIER_UTILISATEURS, "w", encoding="utf-8") as f:
        json.dump(base, f, indent=2, ensure_ascii=False)


def inscrire(identifiant: str, nom: str, mot_de_passe: str) -> tuple[bool, str]:
    """Crée un nouveau compte. Retourne (succès, message)."""
    identifiant = identifiant.strip().lower()
    if not re.fullmatch(r"[a-z0-9_.-]{3,30}", identifiant):
        return False, "Identifiant invalide (3 à 30 caractères : lettres, chiffres, _ . -)."
    if len(mot_de_passe) < 6:
        return False, "Le mot de passe doit contenir au moins 6 caractères."
    base = _charger()
    if identifiant in base:
        return False, "Cet identifiant existe déjà."
    sel = secrets.token_hex(16)
    base[identifiant] = {"sel": sel, "hash": _hacher(mot_de_passe, sel), "nom": nom.strip() or identifiant}
    _sauvegarder(base)
    return True, "Compte créé avec succès. Vous pouvez vous connecter."


def authentifier(identifiant: str, mot_de_passe: str) -> tuple[bool, str]:
    """Vérifie les identifiants. Retourne (succès, nom affiché ou message d'erreur)."""
    base = _charger()
    utilisateur = base.get(identifiant.strip().lower())
    if utilisateur is None:
        return False, "Identifiant ou mot de passe incorrect."
    attendu = utilisateur["hash"]
    obtenu = _hacher(mot_de_passe, utilisateur["sel"])
    if not hmac.compare_digest(attendu, obtenu):
        return False, "Identifiant ou mot de passe incorrect."
    return True, utilisateur["nom"]
