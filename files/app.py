import streamlit as st
import streamlit.components.v1 as components
import tempfile
import os
from main import (
    charger_gtfs,
    calculer_indicateurs_arrets,
    carte_arrets,
)


# Interface Streamlit
st.title("Analyse GTFS - Indicateurs par Arrêt")

st.sidebar.header("Paramètres")

uploaded_file = st.sidebar.file_uploader("Uploader le fichier GTFS (zip)", type="zip")

date_selected = st.sidebar.date_input("Sélectionner une date")

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

        # Calculer les indicateurs
        with st.spinner("Calcul des indicateurs..."):
            indicateurs = calculer_indicateurs_arrets(feed, date_str)

        if indicateurs is not None:
            st.success("Analyse terminée !")

            # Statistiques globales
            st.header("Statistiques Globales")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Nombre d'arrêts", len(indicateurs))

            # Top 10 arrêts
            st.header("Top 10 Arrêts les plus fréquentés")
            st.dataframe(indicateurs.drop(columns=["stop_lat", "stop_lon"]).head(10))

            # Carte
            st.header("Carte des Arrêts")
            m = carte_arrets(indicateurs)
            components.html(m._repr_html_(), height=500, width=1000)

            # Télécharger les résultats
            csv = indicateurs.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Télécharger les résultats CSV",
                data=csv,
                file_name=f"indicateurs_arrets_{date_str}.csv",
                mime="text/csv",
            )
        else:
            st.error("Aucun service actif pour cette date.")

    except Exception as e:
        st.error(f"Erreur lors du traitement : {e}")

    finally:
        # Nettoyer le fichier temporaire
        os.unlink(zip_path)

else:
    st.info("Veuillez uploader un fichier GTFS et sélectionner une date.")
