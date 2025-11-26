"""
Page d'accueil - Application d'analyse GTFS
"""

import streamlit as st
import pandas as pd


def home_page():
    st.markdown("---")

    # Section Hackathon
    st.markdown(
        """
    ## Hackathon Cerema

    Ce projet a été développé lors d'un Hackathon Cerema les 25 et 26 novembre 2025.
    
    L'objectif du projet était de [à compléter]
    """
    )

    st.markdown("---")

    st.markdown(
        """
    ## Bienvenue dans l'application d'analyse GTFS

    Cette application vous permet d'analyser les données GTFS (General Transit Feed Specification)
    pour extraire des indicateurs clés sur les transports en commun.

    ### Fonctionnalités disponibles :

    #### 📍 **Analyse par Arrêts**
    - Fréquentation par arrêt
    - Cartographie interactive des arrêts
    - Statistiques détaillées

    #### 🛤️ **Analyse par Tronçons**
    - Fréquentation par tronçon (bus, tram, métro, etc.)
    - Calcul des vitesses moyennes
    - Cartographie interactive des tronçons
    - ⚠️ **Actuellement limité au réseau de Montpellier**

    ### Instructions :
    1. **Chargez un fichier GTFS** dans la barre latérale (format ZIP)
    2. **Sélectionnez une date** d'analyse
    3. **Naviguez entre les pages** pour explorer les analyses

    > **⚠️ Limitation importante :** L'analyse des tronçons est actuellement une preuve de concept
    > développée spécifiquement pour le réseau de Montpellier. L'application détecte automatiquement
    > les modes de transport présents dans n'importe quel GTFS, mais le calcul des indicateurs
    > de tronçons pourrait nécessiter des adaptations pour d'autres réseaux urbains.
    >
    > L'analyse par arrêts fonctionne quant à elle avec n'importe quel GTFS.
    """
    )

    st.markdown("---")

    # Section Auteurs
    st.markdown(
        """
    ## Contributeurs :
    - Hugo De Luca
    - Maxence Liogier
    - Patrick Gendre

    ---

    *Projet open-source - Cerema 2025*
    """
    )
