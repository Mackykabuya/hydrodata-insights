"""
HydroData Insights - Entraînement du modèle de prédiction de consommation d'eau.

Étapes :
  1. Chargement de donnees_consommation_eau.csv
  2. Prétraitement (features calendaires, encodage, scaling)
  3. Entraînement d'un Random Forest Regressor
  4. Évaluation (RMSE, MAE, R²)
  5. Sauvegarde du pipeline et des métadonnées dans models/

Usage :
    python train_model.py
"""

import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

FICHIER_DONNEES = "donnees_consommation_eau.csv"
DOSSIER_MODELES = "models"
SEED = 42

COLONNES_NUMERIQUES = [
    "temperature_moy",
    "precipitations_mm",
    "population_estimee",
    "taux_couverture_reseau",
    "est_jour_ferie",
    "pression_moyenne_bar",
    "mois",
    "jour_semaine",
]
COLONNES_CATEGORIELLES = ["region", "saison"]
CIBLE = "consommation_m3"


def ajouter_variables_calendaires(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute le mois et le jour de la semaine à partir de la date."""
    df = df.copy()
    dates = pd.to_datetime(df["date"])
    df["mois"] = dates.dt.month
    df["jour_semaine"] = dates.dt.dayofweek
    return df


def construire_pipeline() -> Pipeline:
    """Pipeline : encodage One-Hot des catégories + scaling + Random Forest."""
    preprocesseur = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), COLONNES_NUMERIQUES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), COLONNES_CATEGORIELLES),
        ]
    )
    modele = RandomForestRegressor(
        n_estimators=300,
        max_depth=18,
        min_samples_leaf=2,
        n_jobs=-1,
        random_state=SEED,
    )
    return Pipeline([("preprocesseur", preprocesseur), ("modele", modele)])


def evaluer(y_vrai, y_predit) -> dict:
    """Calcule RMSE, MAE et R²."""
    return {
        "RMSE": float(np.sqrt(mean_squared_error(y_vrai, y_predit))),
        "MAE": float(mean_absolute_error(y_vrai, y_predit)),
        "R2": float(r2_score(y_vrai, y_predit)),
    }


def main() -> None:
    print("Chargement des données...")
    df = pd.read_csv(FICHIER_DONNEES)
    df = ajouter_variables_calendaires(df)

    X = df[COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES]
    y = df[CIBLE]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED)

    print("Entraînement du modèle...")
    pipeline = construire_pipeline()
    pipeline.fit(X_train, y_train)

    metriques = evaluer(y_test, pipeline.predict(X_test))
    print("Évaluation sur le jeu de test :")
    print(f"  RMSE : {metriques['RMSE']:.1f} m³")
    print(f"  MAE  : {metriques['MAE']:.1f} m³")
    print(f"  R²   : {metriques['R2']:.4f}")

    # Sauvegarde
    os.makedirs(DOSSIER_MODELES, exist_ok=True)
    joblib.dump(pipeline, os.path.join(DOSSIER_MODELES, "modele_consommation.joblib"), compress=3)

    # Métadonnées utiles à l'application (valeurs par défaut des formulaires)
    meta = {
        "metriques": metriques,
        "colonnes_numeriques": COLONNES_NUMERIQUES,
        "colonnes_categorielles": COLONNES_CATEGORIELLES,
        "defauts_par_region": {
            region: {
                "population_estimee": int(g["population_estimee"].iloc[-1]),
                "taux_couverture_reseau": float(g["taux_couverture_reseau"].iloc[-1]),
                "pression_moyenne_bar": float(g["pression_moyenne_bar"].mean()),
                "capacite_reseau_m3": float(g[CIBLE].quantile(0.95) * 1.05),
            }
            for region, g in df.groupby("region")
        },
    }
    with open(os.path.join(DOSSIER_MODELES, "metadonnees.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"Modèle et métadonnées sauvegardés dans '{DOSSIER_MODELES}/'.")


if __name__ == "__main__":
    main()
