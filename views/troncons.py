"""
Page Tronçons - Analyse GTFS Indicateurs par Tronçon
"""

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.indicateurs_troncons import compute_indicateurs_troncons
from src.cartographie import creer_carte_troncons
from src.create_troncons_uniques import creer_troncons_uniques


def charger_ou_calculer_troncons(feed, route_type, nom_mode):
    """
    Calcule automatiquement les tronçons depuis le GTFS uploadé.

    Cette fonction calcule toujours les tronçons à partir du feed GTFS fourni,
    garantissant la compatibilité avec n'importe quel réseau de transport.

    Parameters:
    -----------
    feed : gtfs_kit Feed object
        Feed GTFS chargé
    route_type : int
        Type de route GTFS (0=tram, 3=bus, etc.)
    nom_mode : str
        Nom du mode pour les messages ("Bus" ou "Tram")

    Returns:
    --------
    pandas.DataFrame : Tronçons avec colonnes nécessaires pour l'analyse
    """
    st.info(f"🔄 Calcul automatique des tronçons {nom_mode} depuis le GTFS...")

    try:
        # Calculer les tronçons uniques
        troncons_gdf = creer_troncons_uniques(feed, route_type)

        # Convertir en DataFrame avec les colonnes attendues
        troncons = pd.DataFrame(
            {
                "troncon_unique_id": troncons_gdf["troncon_unique_id"],
                "stop_depart_parent_id": troncons_gdf["stop_depart_parent_id"],
                "stop_arrivee_parent_id": troncons_gdf["stop_arrivee_parent_id"],
                "stop_depart_name": troncons_gdf["stop_depart_name"],
                "stop_arrivee_name": troncons_gdf["stop_arrivee_name"],
                "lat_depart_parent": troncons_gdf["lat_depart_parent"],
                "lon_depart_parent": troncons_gdf["lon_depart_parent"],
                "lat_arrivee_parent": troncons_gdf["lat_arrivee_parent"],
                "lon_arrivee_parent": troncons_gdf["lon_arrivee_parent"],
                "geometry": troncons_gdf["geometry"].apply(
                    lambda x: x.wkt if x is not None else None
                ),
            }
        )

        st.success(f"✅ {len(troncons)} tronçons {nom_mode} calculés automatiquement")
        return troncons

    except Exception as e:
        st.error(f"❌ Erreur lors du calcul automatique des tronçons {nom_mode}: {e}")
        return None


def troncons_page():
    st.markdown("---")

    # Avertissement sur les limitations
    st.warning(
        """
    ⚠️ **Limitation importante :** Cette analyse des tronçons est actuellement une preuve de concept
    développée spécifiquement pour le réseau de Montpellier. Bien que l'application détecte automatiquement
    les modes de transport présents dans votre GTFS, les calculs d'indicateurs pourraient nécessiter
    des adaptations pour d'autres réseaux urbains.
    """
    )

    st.markdown("---")

    # Vérifier si les données sont chargées
    if (
        st.session_state.feed is not None
        and st.session_state.active_service_ids is not None
    ):

        # Calculer les indicateurs automatiquement si pas déjà fait
        if (
            st.session_state.indicateurs_bus is None
            or st.session_state.indicateurs_tram is None
        ):

            with st.spinner("Chargement/Calcul des tronçons de référence..."):
                # Calculer automatiquement les tronçons pour bus et tram
                troncons_bus = charger_ou_calculer_troncons(
                    st.session_state.feed, route_type=3, nom_mode="Bus"
                )
                troncons_tram = charger_ou_calculer_troncons(
                    st.session_state.feed, route_type=0, nom_mode="Tram"
                )

                if troncons_bus is None or troncons_tram is None:
                    st.error("Impossible de calculer les tronçons de référence.")
                    return

            with st.spinner("Calcul des indicateurs de tronçons..."):
                try:
                    indicateurs_bus, indicateurs_tram = compute_indicateurs_troncons(
                        st.session_state.feed,
                        st.session_state.active_service_ids,
                        troncons_bus,
                        troncons_tram,
                    )
                    st.session_state.indicateurs_bus = indicateurs_bus
                    st.session_state.indicateurs_tram = indicateurs_tram
                except Exception as e:
                    st.error(f"Erreur lors du calcul des tronçons : {e}")
                    return

        if (
            st.session_state.indicateurs_bus is not None
            and st.session_state.indicateurs_tram is not None
        ):

            indicateurs_bus = st.session_state.indicateurs_bus
            indicateurs_tram = st.session_state.indicateurs_tram

            st.success("✅ Analyse des tronçons terminée !")

            # Statistiques globales
            st.header("📊 Statistiques Globales")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "Tronçons Bus actifs",
                    len(indicateurs_bus[indicateurs_bus["nombre_passages"] > 0]),
                )
            with col2:
                st.metric(
                    "Tronçons Tram actifs",
                    len(indicateurs_tram[indicateurs_tram["nombre_passages"] > 0]),
                )
            with col3:
                total_bus = int(indicateurs_bus["nombre_passages"].sum())
                st.metric("Total passages Bus", total_bus)
            with col4:
                total_tram = int(indicateurs_tram["nombre_passages"].sum())
                st.metric("Total passages Tram", total_tram)

            # Top tronçons
            col1, col2 = st.columns(2)

            with col1:
                st.header("🚌 Top 10 Tronçons Bus")
                bus_actifs = indicateurs_bus[
                    indicateurs_bus["nombre_passages"] > 0
                ].copy()
                if not bus_actifs.empty:
                    bus_actifs = bus_actifs.sort_values(
                        "nombre_passages", ascending=False
                    )
                    cols_to_show = [
                        "stop_depart_name",
                        "stop_arrivee_name",
                        "nombre_passages",
                        "vitesse_moyenne_kmh",
                    ]
                    st.dataframe(bus_actifs[cols_to_show].head(10))
                else:
                    st.info("Aucun tronçon bus actif.")

            with col2:
                st.header("🚊 Top 10 Tronçons Tram")
                tram_actifs = indicateurs_tram[
                    indicateurs_tram["nombre_passages"] > 0
                ].copy()
                if not tram_actifs.empty:
                    tram_actifs = tram_actifs.sort_values(
                        "nombre_passages", ascending=False
                    )
                    cols_to_show = [
                        "stop_depart_name",
                        "stop_arrivee_name",
                        "nombre_passages",
                        "vitesse_moyenne_kmh",
                    ]
                    st.dataframe(tram_actifs[cols_to_show].head(10))
                else:
                    st.info("Aucun tronçon tram actif.")

            # Carte interactive
            st.header("🗺️ Carte Interactive des Tronçons")
            m = creer_carte_troncons(indicateurs_bus, indicateurs_tram)
            components.html(m._repr_html_(), height=600, width=1000)

            # Télécharger les résultats
            st.header("💾 Téléchargement")
            col1, col2 = st.columns(2)
            with col1:
                csv_bus = indicateurs_bus.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Télécharger Bus CSV",
                    data=csv_bus,
                    file_name=f"indicateurs_troncons_bus_{st.session_state.date_str}.csv",
                    mime="text/csv",
                )
            with col2:
                csv_tram = indicateurs_tram.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Télécharger Tram CSV",
                    data=csv_tram,
                    file_name=f"indicateurs_troncons_tram_{st.session_state.date_str}.csv",
                    mime="text/csv",
                )
        else:
            st.info("🔄 Calcul des indicateurs en cours...")
    else:
        st.info(
            "👆 Veuillez charger un fichier GTFS et sélectionner une date dans la barre latérale."
        )
