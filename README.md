# HydroData Insights

Application web de suivi et de prédiction de la consommation d'eau régionale (Streamlit + Scikit-Learn + Plotly).

## 1. Structure du projet

```
hydrodata-insights/
├── app.py                          # Application Streamlit (dashboard, prédiction, alertes)
├── auth.py                         # Connexion / inscription (mots de passe hachés)
├── generate_data.py                # Génération du dataset synthétique
├── train_model.py                  # Entraînement et sauvegarde du modèle
├── requirements.txt                # Dépendances
├── .gitignore
├── README.md
├── donnees_consommation_eau.csv    # Généré par generate_data.py
└── models/
    ├── modele_consommation.joblib  # Généré par train_model.py
    └── metadonnees.json
```

## 2. Environnement de développement (VS Code)

Ouvrez le dossier du projet dans VS Code (`Fichier > Ouvrir un dossier`), puis ouvrez un terminal (`Ctrl+ù` ou `Ctrl+``).

**Windows (PowerShell)**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
# Si l'activation est bloquée : Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**macOS / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

Dans VS Code : `Ctrl+Maj+P` > « Python: Select Interpreter » > choisissez `./venv`.

**requirements.txt**
```
streamlit>=1.50.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
plotly>=5.18.0
joblib>=1.3.0
```
(Vous pouvez aussi le générer avec `pip freeze > requirements.txt`, mais gardez la version courte ci-dessus pour le déploiement.)

**Installation**
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Exécution

```bash
python generate_data.py      # crée donnees_consommation_eau.csv (4 384 lignes)
python train_model.py        # crée models/ et affiche RMSE, MAE, R²
streamlit run app.py         # lance l'application sur http://localhost:8501
```

Compte de démonstration : `admin` / `admin123` (changez-le avant toute mise en production).

> Note : sur Streamlit Community Cloud, le fichier `users.json` est stocké sur un disque temporaire :
> les comptes créés par inscription sont perdus à chaque redémarrage de l'application.
> Pour un usage réel, utilisez une base de données externe.

## 4. Déploiement gratuit sur Streamlit Community Cloud

### 4.1 Dépôt Git local
```bash
git init
git add .
git commit -m "HydroData Insights : version initiale"
git branch -M main
```
Vérifiez que `donnees_consommation_eau.csv` et `models/` sont bien inclus (`git status`) : l'application en a besoin au démarrage.

### 4.2 Dépôt GitHub
1. Connectez-vous sur https://github.com et cliquez sur **New repository**.
2. Nom : `hydrodata-insights` ; visibilité Public (ou Privé si votre compte Streamlit est lié à GitHub avec accès privé) ; ne cochez ni README ni .gitignore.
3. Poussez le code :
```bash
git remote add origin https://github.com/<VOTRE_UTILISATEUR>/hydrodata-insights.git
git push -u origin main
```

### 4.3 `.gitignore`
```
venv/
.venv/
env/
__pycache__/
*.py[cod]
*.egg-info/
.vscode/
.idea/
.DS_Store
Thumbs.db
.env
.streamlit/secrets.toml
users.json
.ipynb_checkpoints/
```

### 4.4 Déploiement depuis Streamlit Cloud
1. Allez sur https://share.streamlit.io et connectez-vous avec GitHub.
2. Cliquez sur **Create app** > **Deploy a public app from GitHub**.
3. Renseignez :
   - Repository : `<VOTRE_UTILISATEUR>/hydrodata-insights`
   - Branch : `main`
   - Main file path : `app.py`
4. (Optionnel) **Advanced settings** : choisissez Python 3.11 ou 3.12, la même version que celle utilisée pour entraîner le modèle.
5. Cliquez sur **Deploy**. Après quelques minutes, l'application est accessible sur `https://<nom>.streamlit.app`.

Si le modèle ne se charge pas (erreur de version de scikit-learn), réentraînez-le avec la version installée sur le Cloud en épinglant la même version dans `requirements.txt` (par exemple `scikit-learn==1.5.2`), puis refaites `python train_model.py` et poussez à nouveau `models/`.
