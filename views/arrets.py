"""
Page Arrêts - Analyse GTFS Indicateurs par Arrêt
"""

import streamlit as st
import streamlit.components.v1 as components

from src.arrets import calculer_indicateurs_arrets
from src.cartographie import create_carte_arrets


def arrets_page():
    st.markdown("---")

    # Vérifier si les données sont chargées
    if (
        st.session_state.feed is not None
        and st.session_state.active_service_ids is not None
    ):

        # Calculer les indicateurs automatiquement si pas déjà fait
        if st.session_state.indicateurs_arrets is None:
            with st.spinner("Calcul des indicateurs d'arrêts..."):
                try:
                    indicateurs = calculer_indicateurs_arrets(
                        st.session_state.feed,
                        st.session_state.active_service_ids,
                        st.session_state.date_str,
                    )
                    st.session_state.indicateurs_arrets = indicateurs
                except Exception as e:
                    st.error(f"Erreur lors du calcul des arrêts : {e}")
                    return

        if st.session_state.indicateurs_arrets is not None:
            indicateurs = st.session_state.indicateurs_arrets

            st.success("✅ Analyse des arrêts terminée !")

            # Statistiques globales
            st.header("📊 Statistiques Globales")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Nombre d'arrêts", len(indicateurs))
            with col2:
                st.metric(
                    "Arrêts actifs",
                    len(indicateurs[indicateurs["nombre_passages"] > 0]),
                )
            with col3:
                total_passages = int(indicateurs["nombre_passages"].sum())
                st.metric("Total passages", total_passages)

            # Top 10 arrêts
            st.header("🏆 Top 10 Arrêts les plus fréquentés")
            actifs = indicateurs[indicateurs["nombre_passages"] > 0].copy()
            if not actifs.empty:
                actifs = actifs.sort_values("nombre_passages", ascending=False)
                st.dataframe(actifs.drop(columns=["stop_lon", "stop_lat"]).head(10))
            else:
                st.info("Aucun arrêt actif trouvé.")

            # Carte
            st.header("🗺️ Carte des Arrêts")
            m = create_carte_arrets(indicateurs)
            components.html(m._repr_html_(), height=500, width=1000)

            # Télécharger les résultats
            st.header("💾 Téléchargement")
            csv = indicateurs.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Télécharger les résultats CSV",
                data=csv,
                file_name=f"indicateurs_arrets_{st.session_state.date_str}.csv",
                mime="text/csv",
            )
        else:
            st.info("🔄 Calcul des indicateurs en cours...")
    else:
        st.info(
            "👆 Veuillez charger un fichier GTFS et sélectionner une date dans la barre latérale."
        )
