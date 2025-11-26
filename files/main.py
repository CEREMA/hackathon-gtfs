"""
POC - Analyse GTFS : Indicateurs par arrêt pour un jour donné
Calcule pour chaque arrêt : nombre de passages, premier et dernier départ
"""

import gtfs_kit as gk
import pandas as pd
import folium
import numpy as np

# Configuration
GTFS_ZIP_PATH = "data/TAM_MMM_GTFS.zip"  # À modifier
DATE_ANALYSE = "20251014"  # Format YYYYMMDD - À modifier


def charger_gtfs(zip_path):
    """Charge le fichier GTFS"""
    print(f"Chargement du fichier GTFS : {zip_path}")
    feed = gk.read_feed(zip_path, dist_units="km")
    print(f"✓ GTFS chargé avec succès")
    return feed


def obtenir_service_ids_pour_date(feed, date_str):
    """
    Identifie les service_id actifs pour une date donnée
    en tenant compte de calendar et calendar_dates
    """
    date_obj = pd.to_datetime(date_str, format="%Y%m%d")
    jour_semaine = date_obj.strftime("%A").lower()  # lundi, mardi, etc.

    # Mapping jour de la semaine -> colonne calendar
    jour_mapping = {
        "monday": "monday",
        "tuesday": "tuesday",
        "wednesday": "wednesday",
        "thursday": "thursday",
        "friday": "friday",
        "saturday": "saturday",
        "sunday": "sunday",
    }

    service_ids = set()

    # 1. Vérifier calendar.txt
    if hasattr(feed, "calendar") and feed.calendar is not None:
        calendar = feed.calendar.copy()
        # Convertir les dates
        calendar["start_date"] = pd.to_datetime(calendar["start_date"], format="%Y%m%d")
        calendar["end_date"] = pd.to_datetime(calendar["end_date"], format="%Y%m%d")

        # Filtrer les services actifs ce jour
        jour_col = jour_mapping[jour_semaine]
        services_calendar = calendar[
            (calendar["start_date"] <= date_obj)
            & (calendar["end_date"] >= date_obj)
            & (calendar[jour_col] == 1)
        ]["service_id"].tolist()

        service_ids.update(services_calendar)

    # 2. Vérifier calendar_dates.txt (exceptions)
    if hasattr(feed, "calendar_dates") and feed.calendar_dates is not None:
        calendar_dates = feed.calendar_dates.copy()
        calendar_dates["date"] = pd.to_datetime(calendar_dates["date"], format="%Y%m%d")

        exceptions = calendar_dates[calendar_dates["date"] == date_obj]

        for _, row in exceptions.iterrows():
            if row["exception_type"] == 1:  # Service ajouté
                service_ids.add(row["service_id"])
            elif row["exception_type"] == 2:  # Service retiré
                service_ids.discard(row["service_id"])

    service_ids = list(service_ids)
    print(f"✓ Services actifs le {date_str} : {len(service_ids)} service(s)")
    return service_ids


def calculer_indicateurs_arrets(feed, date_str):
    """
    Calcule les indicateurs pour chaque arrêt :
    - Nombre de lignes desservies
    - Nombre de passages
    - Heure du premier départ
    - Heure du dernier départ
    - Amplitude horaire
    - Temps d'attente moyen, min et max
    """
    print(f"\nCalcul des indicateurs pour le {date_str}...")

    # Récupérer les services actifs
    service_ids = obtenir_service_ids_pour_date(feed, date_str)

    if not service_ids:
        print("⚠ Aucun service actif pour cette date")
        return None

    # Filtrer les trips actifs ce jour-là
    trips_actifs = feed.trips[feed.trips["service_id"].isin(service_ids)]
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


def exporter_resultats(df, date_str):
    """Exporte les résultats en CSV"""
    output_file = f"indicateurs_arrets_{date_str}.csv"
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\n✓ Résultats exportés dans : {output_file}")


def carte_arrets(df):
    # Carte des arrêts avec leur nombre de passages

    # Définir les seuils pour les couleurs
    passages_values = df["nombre_passages"].values
    bins = np.percentile(passages_values, [0, 25, 50, 75, 100])
    bins = [0] + list(bins[1:])  # Assurer que le minimum est 0

    def get_color(passages):
        if passages == 0:
            return "gray"
        elif passages <= bins[1]:
            return "green"
        elif passages <= bins[2]:
            return "yellow"
        elif passages <= bins[3]:
            return "orange"
        else:
            return "red"

    m = folium.Map(
        location=[df["stop_lat"].mean(), df["stop_lon"].mean()],
        zoom_start=12,
        width="100%",
        height="500px",
    )

    for _, row in df.iterrows():
        stop_id = row["stop_id"]
        lat = row["stop_lat"]
        lon = row["stop_lon"]
        passages = row["nombre_passages"]

        color = get_color(passages)

        folium.CircleMarker(
            location=[lat, lon],
            radius=2,
            popup=f"Arrêt ID: {stop_id}\nPassages: {passages}",
            color=color,
            fill=True,
            fill_color=color,
        ).add_to(m)

    m.save("stops_map.html")

    print("\n✓ Carte des arrêts enregistrée dans : stops_map.html")

    return m


def main():
    """Fonction principale"""
    print("=" * 70)
    print("POC - ANALYSE GTFS : INDICATEURS PAR ARRÊT")
    print("=" * 70)

    try:
        # Charger le GTFS
        feed = charger_gtfs(GTFS_ZIP_PATH)

        # Calculer les indicateurs
        resultats = calculer_indicateurs_arrets(feed, DATE_ANALYSE)

        if resultats is not None:
            # Afficher les statistiques
            afficher_statistiques(resultats)

            # Exporter les résultats
            exporter_resultats(resultats, DATE_ANALYSE)

            # Carte des arrêts
            carte_arrets(resultats)

            print("\n✓ Traitement terminé avec succès !")

            return resultats

    except FileNotFoundError:
        print(f"✗ Erreur : Le fichier {GTFS_ZIP_PATH} n'a pas été trouvé")
    except Exception as e:
        print(f"✗ Erreur lors du traitement : {e}")
        raise


if __name__ == "__main__":
    resultats = main()
