"""
HydroData Insights - Génération du dataset synthétique de consommation d'eau.

Produit le fichier `donnees_consommation_eau.csv` : données journalières sur
3 ans (2023-2025) pour 4 zones, soit 4 x 1096 = 4384 lignes.

Usage :
    python generate_data.py
"""

import numpy as np
import pandas as pd

# Reproductibilité des résultats
SEED = 42
rng = np.random.default_rng(SEED)

# Paramètres généraux
DATE_DEBUT = "2023-01-01"
DATE_FIN = "2028-12-31"
FICHIER_SORTIE = "donnees_consommation_eau.csv"

# Caractéristiques propres à chaque zone
ZONES = {
    "Zone Nord": {"population": 1_200_000, "couverture": 82.0, "pression": 3.2, "croissance": 0.022},
    "Zone Sud": {"population": 900_000, "couverture": 74.0, "pression": 2.9, "croissance": 0.018},
    "Zone Est": {"population": 1_500_000, "couverture": 68.0, "pression": 2.6, "croissance": 0.030},
    "Zone Ouest": {"population": 700_000, "couverture": 88.0, "pression": 3.5, "croissance": 0.015},
}

# Jours fériés fixes (mois, jour) - calendrier type
JOURS_FERIES_FIXES = {(1, 1), (1, 4), (5, 1), (6, 30), (8, 1), (8, 2), (12, 25)}


def determiner_saison(mois: int) -> str:
    """Saison sèche de juin à septembre, pluvieuse le reste de l'année."""
    return "Sèche" if 6 <= mois <= 9 else "Pluvieuse"


def generer_meteo(dates: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray]:
    """Génère température (°C) et précipitations (mm) avec saisonnalité."""
    jour_annee = dates.dayofyear.to_numpy()
    mois = dates.month.to_numpy()

    # Température : cycle annuel + bruit (plus chaud en saison sèche)
    temperature = 27 + 4 * np.sin(2 * np.pi * (jour_annee - 100) / 365) + rng.normal(0, 1.3, len(dates))

    # Précipitations : pluie fréquente en saison pluvieuse, rare en saison sèche
    pluie = np.zeros(len(dates))
    saison_pluvieuse = ~((mois >= 6) & (mois <= 9))
    proba_pluie = np.where(saison_pluvieuse, 0.55, 0.08)
    il_pleut = rng.random(len(dates)) < proba_pluie
    pluie[il_pleut] = rng.gamma(shape=2.0, scale=9.0, size=il_pleut.sum())
    return temperature, np.clip(pluie, 0, 120)


def calculer_consommation(df: pd.DataFrame) -> np.ndarray:
    """
    Calcule la consommation (m³) de façon logique :
    - base proportionnelle à la population desservie (~ 60 L / habitant / jour)
    - hausse avec la température, baisse avec les précipitations
    - légère baisse les jours fériés et le week-end
    - effet de la pression du réseau, bruit aléatoire
    """
    population_desservie = df["population_estimee"] * df["taux_couverture_reseau"] / 100
    base_m3 = population_desservie * 0.060

    effet_temperature = 1 + 0.018 * (df["temperature_moy"] - 27)
    effet_pluie = 1 - 0.0035 * np.minimum(df["precipitations_mm"], 60)
    effet_ferie = np.where(df["est_jour_ferie"] == 1, 0.93, 1.0)
    effet_weekend = np.where(pd.to_datetime(df["date"]).dt.dayofweek >= 5, 0.96, 1.0)
    effet_pression = 1 + 0.02 * (df["pression_moyenne_bar"] - 3.0)
    bruit = rng.normal(1.0, 0.025, len(df))

    return base_m3 * effet_temperature * effet_pluie * effet_ferie * effet_weekend * effet_pression * bruit


def generer_dataset() -> pd.DataFrame:
    """Assemble le dataset complet pour toutes les zones."""
    dates = pd.date_range(DATE_DEBUT, DATE_FIN, freq="D")
    morceaux = []

    for nom_zone, p in ZONES.items():
        temperature, pluie = generer_meteo(dates)
        annees_ecoulees = (dates - dates[0]).days.to_numpy() / 365.0

        zone_df = pd.DataFrame({
            "date": dates,
            "region": nom_zone,
            "temperature_moy": np.round(temperature, 1),
            "precipitations_mm": np.round(pluie, 1),
            # Croissance démographique progressive + petit bruit
            "population_estimee": (p["population"] * (1 + p["croissance"]) ** annees_ecoulees
                                   * rng.normal(1.0, 0.002, len(dates))).astype(int),
            # La couverture progresse lentement dans le temps
            "taux_couverture_reseau": np.round(np.clip(p["couverture"] + 1.2 * annees_ecoulees
                                                       + rng.normal(0, 0.15, len(dates)), 0, 100), 1),
            "est_jour_ferie": [1 if (d.month, d.day) in JOURS_FERIES_FIXES else 0 for d in dates],
            "saison": [determiner_saison(m) for m in dates.month],
            "pression_moyenne_bar": np.round(np.clip(p["pression"] + rng.normal(0, 0.25, len(dates)), 1.0, 6.0), 2),
        })
        morceaux.append(zone_df)

    df = pd.concat(morceaux, ignore_index=True)
    df["consommation_m3"] = np.round(calculer_consommation(df), 1)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df


if __name__ == "__main__":
    donnees = generer_dataset()
    donnees.to_csv(FICHIER_SORTIE, index=False, encoding="utf-8")
    print(f"Fichier généré : {FICHIER_SORTIE}")
    print(f"Nombre de lignes : {len(donnees)}")
    print(donnees.head())
    print(donnees.describe().round(2))
