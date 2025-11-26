"""
Application d'analyse GTFS - Interface principale
"""

import os
import tempfile
import pandas as pd
import streamlit as st

from src.utils import charger_gtfs, obtenir_service_ids_pour_date
from views.home import home_page
from views.arrets import arrets_page
from views.troncons import troncons_page

# Configuration de la page
st.set_page_config(page_title="Analyse GTFS - Cerema", page_icon="🚌", layout="wide")

# Titre principal
st.title("🚌 Analyse GTFS - Indicateurs de Transport")

# Navigation horizontale en haut
st.markdown(
    """
<style>
.stButton button {
    width: 100% !important;
    margin: 0 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("---")
col1, col2, col3, col4 = st.columns([1, 1, 1, 3])  # 4 colonnes pour équilibrer l'espace

with col1:
    if st.button("🏠 Accueil", use_container_width=True):
        st.session_state.selected_page = "Accueil"

with col2:
    if st.button("📍 Arrêts", use_container_width=True):
        st.session_state.selected_page = "Arrêts"

with col3:
    if st.button("🛤️ Tronçons", use_container_width=True):
        st.session_state.selected_page = "Tronçons"

with col4:
    st.write("")  # Espace vide pour équilibrer


# Initialiser la page sélectionnée si pas déjà fait
if "selected_page" not in st.session_state:
    st.session_state.selected_page = "Accueil"

# Barre latérale pour les paramètres uniquement
st.sidebar.header("📁 Paramètres d'analyse")
uploaded_file = st.sidebar.file_uploader("Uploader le fichier GTFS (zip)", type="zip")
date_selected = st.sidebar.date_input("Sélectionner une date")

# Variables globales pour stocker les résultats
if "feed" not in st.session_state:
    st.session_state.feed = None
if "active_service_ids" not in st.session_state:
    st.session_state.active_service_ids = None
if "date_str" not in st.session_state:
    st.session_state.date_str = None
if "indicateurs_arrets" not in st.session_state:
    st.session_state.indicateurs_arrets = None
if "indicateurs_bus" not in st.session_state:
    st.session_state.indicateurs_bus = None
if "indicateurs_tram" not in st.session_state:
    st.session_state.indicateurs_tram = None
if "modes_disponibles" not in st.session_state:
    st.session_state.modes_disponibles = None
if "last_date_str" not in st.session_state:
    st.session_state.last_date_str = None


# Fonction pour vérifier si la date a changé et remettre à zéro les indicateurs
def check_date_change():
    current_date_str = date_selected.strftime("%Y%m%d") if date_selected else None
    if st.session_state.last_date_str != current_date_str:
        # La date a changé, remettre à zéro tous les indicateurs
        st.session_state.indicateurs_arrets = None
        st.session_state.indicateurs_bus = None
        st.session_state.indicateurs_tram = None
        st.session_state.modes_disponibles = None
        st.session_state.last_date_str = current_date_str


# Fonction pour charger les données
def charger_donnees_gtfs():
    if uploaded_file is not None and date_selected is not None:
        date_str = date_selected.strftime("%Y%m%d")

        # Sauvegarder temporairement le fichier
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
            tmp_file.write(uploaded_file.read())
            zip_path = tmp_file.name

        try:
            # Charger le GTFS
            with st.spinner("Chargement du fichier GTFS..."):
                feed = charger_gtfs(zip_path)

            # Obtenir les services actifs
            active_service_ids = obtenir_service_ids_pour_date(feed, date_str)

            # Stocker dans session_state
            st.session_state.feed = feed
            st.session_state.active_service_ids = active_service_ids
            st.session_state.date_str = date_str

            # Nettoyer le fichier temporaire
            os.unlink(zip_path)

            return True

        except Exception as e:
            st.error(f"Erreur lors du chargement : {e}")
            os.unlink(zip_path)
            return False
    return False


# Charger les données automatiquement si nécessaire
charger_donnees_gtfs()

# Vérifier si la date a changé et remettre à zéro les indicateurs si nécessaire
check_date_change()

# Navigation entre les pages
if st.session_state.selected_page == "Accueil":
    home_page()
elif st.session_state.selected_page == "Arrêts":
    arrets_page()
elif st.session_state.selected_page == "Tronçons":
    troncons_page()
