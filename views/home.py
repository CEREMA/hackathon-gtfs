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
    ## Hackathon TSNI 2025 - Cerema

    Ce projet a été développé lors du Hackathon TSNI 2025 du Cerema.
    
    **Équipe :** Patrick GENDRE, Hugo DE LUCA et Maxence LIOGIER
    """
    )

    st.markdown("---")

    # Liens rapides
    st.markdown(
        """
    ## 🔗 Liens rapides

    Pour aller plus loin, vous pouvez consulter le notebook disponible sur Colab :
    - **📓 [Notebook Google Colab](https://colab.research.google.com/github/CEREMA/hackathon-gtfs/blob/main/gtfs_notebook.ipynb)** : Prendre en main le code, exécuter les cellules et regarder les cartographies dynamiques
    """
    )

    st.markdown("---")

    # Objectifs
    st.markdown(
        """
    ## Objectifs

    - **Offrir une chaîne de traitement** pour passer d'un jeu GTFS brut à des exports géolocalisés d'indicateurs à l'échelle des arrêts et des tronçons
    - **Proposer une offre d'indicateurs sur les tronçons** même en l'absence du fichier shapes.txt dans les données GTFS
    - **Proposer à la fois des scripts utilisables en local**, une interface web conviviale (via Streamlit) pour les utilisateurs non-techniques, et un notebook d'exemple pour tester / explorer les résultats
    """
    )

    st.markdown("---")

    # Fonctionnalités disponibles
    st.markdown(
        """
    ## Bienvenue dans l'application d'analyse GTFS

    Cette application vous permet d'analyser les données GTFS (General Transit Feed Specification)
    pour extraire des indicateurs clés sur les transports en commun.

    ### Fonctionnalités disponibles :

    #### 📍 **Analyse par Arrêts**
    - Nombre de passages par arrêt
    - Carte interactive des arrêts
    - Statistiques détaillées

    #### 🛤️ **Analyse par Tronçons**
    - Nombre de passages par tronçon (bus, tram, métro, etc.)
    - Calcul des vitesses moyennes
    - Carte interactive des tronçons
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
    - Hugo De Luca ([@hugo-deluca](https://github.com/hugo-deluca))
    - Maxence Liogier ([@maxenceLIOGIER](https://github.com/maxenceLIOGIER))
    - Patrick Gendre ([@PatGendre](https://github.com/PatGendre))

    ---

    [*Projet open-source - Cerema 2025*](https://github.com/CEREMA/hackathon-gtfs)
    """
    )
