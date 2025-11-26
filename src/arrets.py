"""
POC - Analyse GTFS : Indicateurs par arrêt pour un jour donné
Calcule pour chaque arrêt : nombre de passages, premier et dernier départ
"""

import pandas as pd


def calculer_indicateurs_arrets(feed, active_service_ids: list[str], date_str: str):
    """
    Calcule les indicateurs pour chaque arrêt :
    - Nombre de lignes desservies
    - Nombre de passages
    - Heure du premier départ
    - Heure du dernier départ
    - Amplitude horaire
    - Temps d'attente moyen, min et max
    """
    print(f"\nCalcul des indicateurs aux arrêts...")

    if not active_service_ids:
        print("⚠ Aucun service actif pour cette date")
        return None

    # Filtrer les trips actifs ce jour-là
    trips_actifs = feed.trips[feed.trips["service_id"].isin(active_service_ids)]
    print(f"✓ {len(trips_actifs)} trips actifs")

    # Joindre avec stop_times
    stop_times_actifs = feed.stop_times.merge(
        trips_actifs[["trip_id", "service_id"]], on="trip_id"
    )

    # Calculer les indicateurs par arrêt
    indicateurs = (
        stop_times_actifs.groupby("stop_id")
        .agg(
            nombre_passages=("trip_id", "count"),
            premier_depart=("departure_time", "min"),
            dernier_depart=("departure_time", "max"),
        )
        .reset_index()
    )

    # Utilisation de gtfs_kit pour calculer les stats de headway
    indic_gk = feed.compute_stop_stats([date_str])
    indicateurs = indicateurs.merge(
        indic_gk[["stop_id", "mean_headway", "max_headway", "num_routes"]],
        on="stop_id",
        how="left",
    )
    indicateurs.rename(
        columns={
            "num_routes": "nb_lignes",
            "mean_headway": "temps_attente_moyen",
            "max_headway": "temps_attente_max",
        },
        inplace=True,
    )

    # Joindre avec les informations des arrêts
    indicateurs = indicateurs.merge(
        feed.stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]],
        on="stop_id",
        how="left",
    )

    # Calculer l'amplitude horaire
    indicateurs["amplitude_horaire"] = pd.to_timedelta(
        indicateurs["dernier_depart"]
    ) - pd.to_timedelta(indicateurs["premier_depart"])
    # nettoyer pour retirer le 0 days
    indicateurs["amplitude_horaire"] = indicateurs["amplitude_horaire"].apply(
        lambda x: str(x).replace("0 days ", " ").strip()
    )

    # Réorganiser les colonnes
    indicateurs = indicateurs[
        [
            "stop_id",
            "stop_name",
            "stop_lat",
            "stop_lon",
            "nb_lignes",
            "nombre_passages",
            "premier_depart",
            "dernier_depart",
            "amplitude_horaire",
            "temps_attente_moyen",
            "temps_attente_max",
        ]
    ]

    # Trier par nombre de passages décroissant
    indicateurs = indicateurs.sort_values("nombre_passages", ascending=False)

    print(f"✓ Indicateurs calculés pour {len(indicateurs)} arrêts")

    return indicateurs


def afficher_statistiques(df):
    """Affiche des statistiques résumées"""
    print("\n" + "=" * 70)
    print("STATISTIQUES GLOBALES")
    print("=" * 70)
    print(f"Nombre total d'arrêts desservis : {len(df)}")
    print(f"Nombre total de passages : {df['nombre_passages'].sum():,}")
    print(f"Moyenne de passages par arrêt : {df['nombre_passages'].mean():.1f}")
    print(f"Médiane de passages par arrêt : {df['nombre_passages'].median():.1f}")
    print(
        f"\nArrêt le plus fréquenté : {df.iloc[0]['stop_name']} ({df.iloc[0]['nombre_passages']} passages)"
    )
    print(f"Premier départ global : {df['premier_depart'].min()}")
    print(f"Dernier départ global : {df['dernier_depart'].max()}")

    print("\n" + "=" * 70)
    print("TOP 10 DES ARRÊTS LES PLUS FRÉQUENTÉS")
    print("=" * 70)
    print(df.head(10).to_string(index=False))
