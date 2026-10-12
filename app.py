"""
HydroData Insights - Application web de prédiction de la consommation d'eau régionale.

Lancement :
    streamlit run app.py
"""

import json
from datetime import date

import joblib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import auth

# ----------------------------------------------------------------------------
# Configuration générale
# ----------------------------------------------------------------------------
NOM_APP = "HydroData Insights"
FICHIER_DONNEES = "donnees_consommation_eau.csv"
FICHIER_MODELE = "models/modele_consommation.joblib"
FICHIER_META = "models/metadonnees.json"

COULEUR_PRIMAIRE = "#0077B6"
COULEUR_SECONDAIRE = "#00B4D8"
COULEUR_ALERTE = "#E63946"
COULEUR_ATTENTION = "#F4A261"
COULEUR_OK = "#2A9D8F"
PALETTE_ZONES = ["#0077B6", "#00B4D8", "#2A9D8F", "#F4A261"]

st.set_page_config(page_title=NOM_APP, page_icon="💧", layout="wide")


def appliquer_style() -> None:
    """Injecte le CSS de l'application (couleurs modernes, cartes KPI)."""
    st.markdown(
        f"""
        <style>
        .bandeau {{
            background: linear-gradient(120deg, {COULEUR_PRIMAIRE}, {COULEUR_SECONDAIRE});
            padding: 1.2rem 1.6rem; border-radius: 14px; color: white; margin-bottom: 1.2rem;
        }}
        .bandeau h1 {{ margin: 0; font-size: 1.9rem; color: white; }}
        .bandeau p {{ margin: 0.2rem 0 0 0; opacity: 0.92; }}
        div[data-testid="stMetric"] {{
            background: #F1F8FC; border-left: 5px solid {COULEUR_PRIMAIRE};
            padding: 0.8rem 1rem; border-radius: 10px;
        }}
        div[data-testid="stMetric"] label, div[data-testid="stMetric"] div {{ color: #0B2545 !important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def bandeau(titre: str, sous_titre: str) -> None:
    st.markdown(f'<div class="bandeau"><h1>{titre}</h1><p>{sous_titre}</p></div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Chargement des ressources (mises en cache)
# ----------------------------------------------------------------------------
@st.cache_data
def charger_donnees() -> pd.DataFrame:
    df = pd.read_csv(FICHIER_DONNEES, parse_dates=["date"])
    return df.sort_values(["date", "region"]).reset_index(drop=True)


@st.cache_resource
def charger_modele():
    return joblib.load(FICHIER_MODELE)


@st.cache_data
def charger_meta() -> dict:
    with open(FICHIER_META, "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------------------
# Page de connexion / inscription
# ----------------------------------------------------------------------------
def page_connexion() -> None:
    bandeau(f"💧 {NOM_APP}", "Plateforme de suivi et de prédiction de la consommation d'eau régionale")
    _, centre, _ = st.columns([1, 1.4, 1])
    with centre:
        onglet_connexion, onglet_inscription = st.tabs(["🔐 Connexion", "📝 Inscription"])

        with onglet_connexion:
            with st.form("form_connexion"):
                identifiant = st.text_input("Identifiant")
                mot_de_passe = st.text_input("Mot de passe", type="password")
                valider = st.form_submit_button("Se connecter", width="stretch")
            if valider:
                ok, resultat = auth.authentifier(identifiant, mot_de_passe)
                if ok:
                    st.session_state["connecte"] = True
                    st.session_state["utilisateur"] = resultat
                    st.rerun()  # redirection vers le tableau de bord
                else:
                    st.error(resultat)
            st.caption("Compte de démonstration : admin / admin123")

        with onglet_inscription:
            with st.form("form_inscription"):
                nouvel_id = st.text_input("Identifiant souhaité")
                nom = st.text_input("Nom complet")
                mdp1 = st.text_input("Mot de passe", type="password", key="mdp1")
                mdp2 = st.text_input("Confirmer le mot de passe", type="password", key="mdp2")
                creer = st.form_submit_button("Créer mon compte", width="stretch")
            if creer:
                if mdp1 != mdp2:
                    st.error("Les mots de passe ne correspondent pas.")
                else:
                    ok, message = auth.inscrire(nouvel_id, nom, mdp1)
                    (st.success if ok else st.error)(message)


# ----------------------------------------------------------------------------
# Filtres communs (barre latérale)
# ----------------------------------------------------------------------------
def filtres_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.markdown("### 🔎 Filtres")
    zones = sorted(df["region"].unique())
    zones_choisies = st.sidebar.multiselect("Zones", zones, default=zones)
    d_min, d_max = df["date"].min().date(), df["date"].max().date()
    periode = st.sidebar.date_input("Période", value=(d_min, d_max), min_value=d_min, max_value=d_max)
    if not isinstance(periode, tuple) or len(periode) != 2:
        periode = (d_min, d_max)
    masque = (
        df["region"].isin(zones_choisies)
        & (df["date"].dt.date >= periode[0])
        & (df["date"].dt.date <= periode[1])
    )
    return df[masque]


# ----------------------------------------------------------------------------
# Page 1 : Vue d'ensemble
# ----------------------------------------------------------------------------
def page_vue_ensemble(df: pd.DataFrame) -> None:
    bandeau("📊 Vue d'ensemble", "Indicateurs clés de la consommation d'eau")
    if df.empty:
        st.warning("Aucune donnée pour les filtres sélectionnés.")
        return

    par_jour = df.groupby("date")["consommation_m3"].sum()
    seuil_pic = par_jour.quantile(0.95)
    nb_pics = int((par_jour >= seuil_pic).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Consommation totale", f"{df['consommation_m3'].sum() / 1e6:,.2f} M m³")
    c2.metric("Moyenne quotidienne", f"{par_jour.mean():,.0f} m³")
    c3.metric("Pics de demande (top 5 %)", f"{nb_pics} jours", help=f"Jours ≥ {seuil_pic:,.0f} m³")
    c4.metric("Zones surveillées", df["region"].nunique())

    st.markdown("#### Consommation journalière (toutes zones sélectionnées)")
    fig = px.area(par_jour.reset_index(), x="date", y="consommation_m3", color_discrete_sequence=[COULEUR_PRIMAIRE])
    fig.add_hline(y=seuil_pic, line_dash="dash", line_color=COULEUR_ALERTE, annotation_text="Seuil de pic (95e centile)")
    fig.update_layout(yaxis_title="Consommation (m³)", xaxis_title="", margin=dict(t=20))
    st.plotly_chart(fig, width="stretch")

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("#### Répartition par zone")
        repart = df.groupby("region")["consommation_m3"].sum().reset_index()
        fig = px.pie(repart, names="region", values="consommation_m3", hole=0.5, color_discrete_sequence=PALETTE_ZONES)
        st.plotly_chart(fig, width="stretch")
    with g2:
        st.markdown("#### Consommation moyenne par saison")
        saison = df.groupby(["saison", "region"])["consommation_m3"].mean().reset_index()
        fig = px.bar(saison, x="region", y="consommation_m3", color="saison", barmode="group",
                     color_discrete_sequence=[COULEUR_ATTENTION, COULEUR_PRIMAIRE])
        fig.update_layout(yaxis_title="m³ / jour", xaxis_title="")
        st.plotly_chart(fig, width="stretch")


# ----------------------------------------------------------------------------
# Page 2 : Visualisation & Analyses
# ----------------------------------------------------------------------------
def page_visualisation(df: pd.DataFrame) -> None:
    bandeau("📈 Visualisation & Analyses", "Évolution, comparaison régionale et impact météo")
    if df.empty:
        st.warning("Aucune donnée pour les filtres sélectionnés.")
        return

    onglet1, onglet2, onglet3 = st.tabs(["Évolution temporelle", "Comparaison régionale", "Impact météo"])

    with onglet1:
        agregation = st.radio("Agrégation", ["Jour", "Semaine", "Mois"], index=2, horizontal=True)
        regle = {"Jour": "D", "Semaine": "W", "Mois": "MS"}[agregation]
        serie = (
            df.set_index("date").groupby("region")["consommation_m3"].resample(regle).sum().reset_index()
        )
        fig = px.line(serie, x="date", y="consommation_m3", color="region", color_discrete_sequence=PALETTE_ZONES)
        fig.update_layout(yaxis_title="Consommation (m³)", xaxis_title="", legend_title="Zone")
        st.plotly_chart(fig, width="stretch")

    with onglet2:
        col_a, col_b = st.columns(2)
        with col_a:
            moyenne = df.groupby("region")["consommation_m3"].mean().reset_index()
            fig = px.bar(moyenne, x="region", y="consommation_m3", color="region", color_discrete_sequence=PALETTE_ZONES,
                         title="Consommation moyenne journalière")
            fig.update_layout(showlegend=False, yaxis_title="m³ / jour", xaxis_title="")
            st.plotly_chart(fig, width="stretch")
        with col_b:
            fig = px.box(df, x="region", y="consommation_m3", color="region", color_discrete_sequence=PALETTE_ZONES,
                         title="Dispersion de la consommation")
            fig.update_layout(showlegend=False, yaxis_title="m³", xaxis_title="")
            st.plotly_chart(fig, width="stretch")

        df_mois = df.assign(mois=df["date"].dt.month_name().str[:3], num_mois=df["date"].dt.month)
        chaleur = df_mois.pivot_table(index="region", columns="num_mois", values="consommation_m3", aggfunc="mean")
        fig = px.imshow(chaleur, aspect="auto", color_continuous_scale="Blues",
                        labels=dict(x="Mois", y="Zone", color="m³/jour"), title="Consommation moyenne par zone et par mois")
        st.plotly_chart(fig, width="stretch")

    with onglet3:
        col_a, col_b = st.columns(2)
        echantillon = df.sample(min(len(df), 1500), random_state=1)
        with col_a:
            fig = px.scatter(echantillon, x="temperature_moy", y="consommation_m3", color="region",
                             color_discrete_sequence=PALETTE_ZONES, opacity=0.6,
                             title="Consommation vs température", labels={"temperature_moy": "Température (°C)"})
            st.plotly_chart(fig, width="stretch")
        with col_b:
            fig = px.scatter(echantillon, x="precipitations_mm", y="consommation_m3", color="region",
                             color_discrete_sequence=PALETTE_ZONES, opacity=0.6,
                             title="Consommation vs précipitations", labels={"precipitations_mm": "Précipitations (mm)"})
            st.plotly_chart(fig, width="stretch")

        st.markdown("#### Matrice de corrélation")
        colonnes = ["temperature_moy", "precipitations_mm", "population_estimee",
                    "taux_couverture_reseau", "pression_moyenne_bar", "consommation_m3"]
        fig = px.imshow(df[colonnes].corr().round(2), text_auto=True, color_continuous_scale="RdBu_r",
                        zmin=-1, zmax=1, aspect="auto")
        st.plotly_chart(fig, width="stretch")


# ----------------------------------------------------------------------------
# Page 3 : Module de prédiction
# ----------------------------------------------------------------------------
def saison_pour_mois(mois: int) -> str:
    return "Sèche" if 6 <= mois <= 9 else "Pluvieuse"


def page_prediction(df: pd.DataFrame) -> None:
    bandeau("🔮 Module de prédiction", "Estimez la consommation d'eau à partir de paramètres saisis")
    modele = charger_modele()
    meta = charger_meta()
    defauts = meta["defauts_par_region"]

    col_form, col_res = st.columns([1.3, 1])

    with col_form:
        region = st.selectbox("Région / zone", sorted(defauts.keys()))
        d = defauts[region]
        date_cible = st.date_input("Date de la prédiction", value=date.today())
        saison_auto = saison_pour_mois(date_cible.month)
        saison = st.selectbox("Saison", ["Sèche", "Pluvieuse"], index=["Sèche", "Pluvieuse"].index(saison_auto))

        c1, c2 = st.columns(2)
        temperature = c1.slider("Température moyenne (°C)", 15.0, 40.0, 27.0, 0.1)
        pluie = c2.slider("Précipitations (mm)", 0.0, 120.0, 0.0 if saison == "Sèche" else 10.0, 0.5)
        population = st.number_input("Population estimée", 100_000, 5_000_000, d["population_estimee"], step=10_000)
        c3, c4 = st.columns(2)
        couverture = c3.slider("Taux de couverture du réseau (%)", 30.0, 100.0, float(round(d["taux_couverture_reseau"], 1)), 0.1)
        pression = c4.slider("Pression moyenne (bar)", 1.0, 6.0, float(round(d["pression_moyenne_bar"], 2)), 0.05)
        ferie = st.checkbox("Jour férié")
        lancer = st.button("Calculer la prédiction", type="primary", width="stretch")

    with col_res:
        st.markdown("#### Résultat")
        if lancer:
            entree = pd.DataFrame([{
                "temperature_moy": temperature,
                "precipitations_mm": pluie,
                "population_estimee": population,
                "taux_couverture_reseau": couverture,
                "est_jour_ferie": int(ferie),
                "pression_moyenne_bar": pression,
                "mois": date_cible.month,
                "jour_semaine": date_cible.weekday(),
                "region": region,
                "saison": saison,
            }])
            prediction = float(modele.predict(entree)[0])
            capacite = d["capacite_reseau_m3"]
            taux = prediction / capacite * 100

            st.metric("Consommation prévue", f"{prediction:,.0f} m³")
            st.metric("Taux d'utilisation de la capacité", f"{taux:.1f} %")

            jauge = go.Figure(go.Indicator(
                mode="gauge+number", value=taux, number={"suffix": " %"},
                gauge={"axis": {"range": [0, 130]}, "bar": {"color": COULEUR_PRIMAIRE},
                       "steps": [{"range": [0, 80], "color": "#D8F3DC"},
                                 {"range": [80, 100], "color": "#FFE5B4"},
                                 {"range": [100, 130], "color": "#FFC9C9"}]}))
            jauge.update_layout(height=260, margin=dict(t=20, b=10))
            st.plotly_chart(jauge, width="stretch")

            if taux >= 100:
                st.error("🚨 Dépassement de capacité probable : prévoir des mesures de délestage.")
            elif taux >= 85:
                st.warning("⚠️ Tension sur le réseau : surveillance renforcée recommandée.")
            else:
                st.success("✅ Consommation prévue dans la capacité normale du réseau.")
        else:
            st.info("Renseignez les paramètres puis cliquez sur « Calculer la prédiction ».")

        m = meta["metriques"]
        st.caption(f"Performance du modèle (test) — R² : {m['R2']:.3f} · MAE : {m['MAE']:.0f} m³ · RMSE : {m['RMSE']:.0f} m³")


# ----------------------------------------------------------------------------
# Page 4 : Alertes & gestion des tensions
# ----------------------------------------------------------------------------
def page_alertes(df: pd.DataFrame) -> None:
    bandeau("🚨 Alertes & gestion des tensions", "Détection des risques de surconsommation et de dépassement de capacité")
    meta = charger_meta()
    capacites = {r: v["capacite_reseau_m3"] for r, v in meta["defauts_par_region"].items()}
    if df.empty:
        st.warning("Aucune donnée pour les filtres sélectionnés.")
        return

    c1, c2 = st.columns(2)
    seuil_attention = c1.slider("Seuil d'attention (% de la capacité)", 60, 100, 85)
    seuil_critique = c2.slider("Seuil critique (% de la capacité)", 80, 130, 100)
    pression_min = st.slider("Pression minimale acceptable (bar)", 1.0, 4.0, 2.2, 0.1)

    donnees = df.copy()
    donnees["capacite_m3"] = donnees["region"].map(capacites)
    donnees["taux_utilisation"] = donnees["consommation_m3"] / donnees["capacite_m3"] * 100

    def niveau(taux: float) -> str:
        if taux >= seuil_critique:
            return "Critique"
        if taux >= seuil_attention:
            return "Attention"
        return "Normal"

    donnees["niveau"] = donnees["taux_utilisation"].apply(niveau)
    donnees["basse_pression"] = donnees["pression_moyenne_bar"] < pression_min

    k1, k2, k3 = st.columns(3)
    k1.metric("Jours critiques", int((donnees["niveau"] == "Critique").sum()))
    k2.metric("Jours en attention", int((donnees["niveau"] == "Attention").sum()))
    k3.metric("Jours de basse pression", int(donnees["basse_pression"].sum()))

    st.markdown("#### Taux d'utilisation de la capacité par zone")
    fig = px.line(donnees, x="date", y="taux_utilisation", color="region", color_discrete_sequence=PALETTE_ZONES)
    fig.add_hline(y=seuil_attention, line_dash="dot", line_color=COULEUR_ATTENTION, annotation_text="Attention")
    fig.add_hline(y=seuil_critique, line_dash="dash", line_color=COULEUR_ALERTE, annotation_text="Critique")
    fig.update_layout(yaxis_title="% de la capacité", xaxis_title="")
    st.plotly_chart(fig, width="stretch")

    st.markdown("#### Synthèse par zone")
    synthese = donnees.groupby("region").agg(
        capacite_m3=("capacite_m3", "first"),
        jours_critiques=("niveau", lambda s: int((s == "Critique").sum())),
        jours_attention=("niveau", lambda s: int((s == "Attention").sum())),
        jours_basse_pression=("basse_pression", "sum"),
        pic_m3=("consommation_m3", "max"),
    ).reset_index()
    synthese["capacite_m3"] = synthese["capacite_m3"].round(0)
    st.dataframe(synthese, width="stretch", hide_index=True)

    st.markdown("#### Dernières alertes détectées")
    alertes = donnees[(donnees["niveau"] != "Normal") | donnees["basse_pression"]].sort_values("date", ascending=False)
    if alertes.empty:
        st.success("Aucune alerte sur la période sélectionnée.")
    else:
        tableau = alertes[["date", "region", "consommation_m3", "taux_utilisation", "pression_moyenne_bar", "niveau"]].head(50).copy()
        tableau["date"] = tableau["date"].dt.strftime("%Y-%m-%d")
        tableau["taux_utilisation"] = tableau["taux_utilisation"].round(1)
        st.dataframe(tableau, width="stretch", hide_index=True)

    st.markdown("#### Recommandations")
    pires = synthese.sort_values("jours_critiques", ascending=False).iloc[0]
    if pires["jours_critiques"] > 0:
        st.error(f"**{pires['region']}** concentre le plus de jours critiques ({int(pires['jours_critiques'])}). "
                 "Envisager une extension de capacité ou un plan de délestage.")
    else:
        st.success("Aucune zone n'atteint le seuil critique sur la période.")


# ----------------------------------------------------------------------------
# Point d'entrée
# ----------------------------------------------------------------------------
def main() -> None:
    appliquer_style()

    if not st.session_state.get("connecte", False):
        page_connexion()
        return

    df_complet = charger_donnees()

    st.sidebar.markdown(f"## 💧 {NOM_APP}")
    st.sidebar.caption(f"👤 {st.session_state.get('utilisateur', '')}")
    page = st.sidebar.radio("Navigation", ["Vue d'ensemble", "Visualisation & Analyses", "Module de prédiction", "Alertes & Tensions"])

    if page != "Module de prédiction":
        df_filtre = filtres_sidebar(df_complet)
    else:
        df_filtre = df_complet

    if page == "Vue d'ensemble":
        page_vue_ensemble(df_filtre)
    elif page == "Visualisation & Analyses":
        page_visualisation(df_filtre)
    elif page == "Module de prédiction":
        page_prediction(df_complet)
    else:
        page_alertes(df_filtre)

    st.sidebar.divider()
    if st.sidebar.button("Se déconnecter", width="stretch"):
        st.session_state["connecte"] = False
        st.session_state.pop("utilisateur", None)
        st.rerun()


main()
