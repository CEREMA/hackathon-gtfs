"""
Calcul de la fréquentation et vitesse moyenne par tronçon unique
Basé sur stop_parent_id, tous sens confondus
"""

import pandas as pd
import numpy as np
from shapely.geometry import LineString

from utils import charger_gtfs, obtenir_service_ids_pour_date


def calculer_distance_haversine(lat1, lon1, lat2, lon2):
    """
    Calcule la distance entre deux points GPS en kilomètres
    Utilise la formule de Haversine
    """
    R = 6371  # Rayon de la Terre en km
    
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c

def convertir_temps_en_secondes(temps_str):
    """
    Convertit un temps GTFS (HH:MM:SS) en secondes
    Gère les heures > 24 (ex: 25:30:00 pour 01:30 le lendemain)
    """
    if pd.isna(temps_str):
        return None
    
    parts = str(temps_str).split(':')
    heures = int(parts[0])
    minutes = int(parts[1])
    secondes = int(parts[2])
    
    return heures * 3600 + minutes * 60 + secondes

def preparer_mapping_parent_stops(feed):
    """
    Crée un mapping entre stop_id et parent_station
    Si parent_station n'existe pas, utilise stop_id comme parent
    """
    stops = feed.stops.copy()
    
    # Si parent_station n'existe pas ou est vide, utiliser stop_id
    if 'parent_station' not in stops.columns:
        stops['parent_station'] = stops['stop_id']
    else:
        stops['parent_station'] = stops['parent_station'].fillna(stops['stop_id'])
        # Remplacer les chaînes vides par stop_id
        stops.loc[stops['parent_station'] == '', 'parent_station'] = stops['stop_id']
    
    return stops[['stop_id', 'parent_station']].set_index('stop_id')['parent_station'].to_dict()


def calculer_frequentation_troncons(feed, df_troncons_uniques, service_ids, route_type):
    """
    Calcule la fréquentation et la vitesse moyenne pour chaque tronçon unique
    
    Parameters:
    -----------
    feed : gtfs_kit Feed object
        Le feed GTFS chargé
    df_troncons_uniques : DataFrame
        Table des tronçons uniques avec les colonnes :
        stop_depart_parent_id, stop_arrivee_parent_id, troncon_unique_id, etc.
    service_ids : list
        Liste des service_id actifs pour la date analysée
    route_type: int
        Le type de route (0=tram, 3=bus, etc.)
    
    Returns:
    --------
    DataFrame avec fréquentation et vitesse moyenne par tronçon
    """
    print("\nCalcul de la fréquentation par tronçon unique...")

    # Créer le mapping stop_id -> parent_station
    mapping_parent = preparer_mapping_parent_stops(feed)
    
    # Filtrer les trips actifs
    trips_actifs = feed.trips[feed.trips['service_id'].isin(service_ids)].copy()

    # Restriction au bon route_type
    routes_filtrees = feed.routes[feed.routes['route_type'] == route_type]
    trips_actifs = trips_actifs[trips_actifs['route_id'].isin(routes_filtrees['route_id'])]

    print(f"✓ {len(trips_actifs)} trips actifs")
    
    # Enrichir stop_times avec les informations nécessaires
    stop_times = feed.stop_times.merge(
        trips_actifs[['trip_id', 'route_id']], 
        on='trip_id'
    )
    
    # Ajouter les parent_station pour chaque stop
    stop_times['stop_parent_id'] = stop_times['stop_id'].map(mapping_parent)
    
    # Trier par trip et séquence
    stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])
    
    print(f"✓ {len(stop_times)} stop_times à analyser")
    
    # Calculer les passages par paire de stops consécutifs
    passages_list = []
    
    for trip_id, groupe in stop_times.groupby('trip_id'):
        groupe = groupe.sort_values('stop_sequence').reset_index(drop=True)
        
        for i in range(len(groupe) - 1):
            depart = groupe.iloc[i]
            arrivee = groupe.iloc[i + 1]
            
            # Calculer le temps de parcours
            temps_depart = convertir_temps_en_secondes(depart['departure_time'])
            temps_arrivee = convertir_temps_en_secondes(arrivee['arrival_time'])
            
            if temps_depart is not None and temps_arrivee is not None:
                duree_secondes = temps_arrivee - temps_depart
                
                if duree_secondes > 0:
                    # Identifier le tronçon (tous sens confondus)
                    parent_depart = depart['stop_parent_id']
                    parent_arrivee = arrivee['stop_parent_id']
                    
                    # Créer une clé normalisée (ordre alphabétique pour regrouper les deux sens)
                    stops_pair = tuple(sorted([parent_depart, parent_arrivee]))
                    
                    passages_list.append({
                        'stop_pair': stops_pair,
                        'stop_depart_parent': parent_depart,
                        'stop_arrivee_parent': parent_arrivee,
                        'duree_secondes': duree_secondes,
                        'trip_id': trip_id
                    })
    
    print(f"✓ {len(passages_list)} passages détectés")
    
    if not passages_list:
        print("⚠ Aucun passage détecté")
        return None
    
    df_passages = pd.DataFrame(passages_list)
    
    # Agréger par paire de stops (tous sens confondus)
    # On compte le nombre de passages et calcule la durée moyenne
    stats_par_paire = df_passages.groupby('stop_pair').agg(
        nombre_passages=('trip_id', 'count'),
        duree_moyenne_secondes=('duree_secondes', 'mean'),
        duree_min_secondes=('duree_secondes', 'min'),
        duree_max_secondes=('duree_secondes', 'max')
    ).reset_index()
    
    print(f"✓ Statistiques calculées pour {len(stats_par_paire)} paires de stops")
    
    # Préparer le matching avec df_troncons_uniques
    # Créer la même clé normalisée dans df_troncons_uniques
    df_troncons_uniques['stop_pair'] = df_troncons_uniques.apply(
        lambda row: tuple(sorted([row['stop_depart_parent_id'], row['stop_arrivee_parent_id']])),
        axis=1
    )
    
    # Joindre avec les statistiques
    df_resultat = df_troncons_uniques.merge(
        stats_par_paire,
        on='stop_pair',
        how='left'
    )
    
    # Supprimer la colonne temporaire
    df_resultat = df_resultat.drop(columns=['stop_pair'])
    
    # Calculer la distance si pas déjà présente
    if 'distance_km' not in df_resultat.columns:
        df_resultat['distance_km'] = df_resultat.apply(
            lambda row: calculer_distance_haversine(
                row['lat_depart_parent'], row['lon_depart_parent'],
                row['lat_arrivee_parent'], row['lon_arrivee_parent']
            ),
            axis=1
        )
    
    # Calculer la vitesse moyenne en km/h
    df_resultat['vitesse_moyenne_kmh'] = (
        df_resultat['distance_km'] / 
        (df_resultat['duree_moyenne_secondes'] / 3600)
    )
    
    # Calculer aussi vitesse min et max
    df_resultat['vitesse_min_kmh'] = (
        df_resultat['distance_km'] / 
        (df_resultat['duree_max_secondes'] / 3600)
    )
    
    df_resultat['vitesse_max_kmh'] = (
        df_resultat['distance_km'] / 
        (df_resultat['duree_min_secondes'] / 3600)
    )
    
    # Remplacer les NaN (tronçons sans passage) par 0
    df_resultat['nombre_passages'] = df_resultat['nombre_passages'].fillna(0).astype(int)
    
    # Trier par nombre de passages décroissant
    df_resultat = df_resultat.sort_values('nombre_passages', ascending=False).reset_index(drop=True)
    
    print(f"✓ Fréquentation calculée pour {len(df_resultat)} tronçons uniques")
    print(f"✓ Tronçons avec passages : {(df_resultat['nombre_passages'] > 0).sum()}")
    
    return df_resultat

def afficher_statistiques_frequentation(df, date_str):
    """Affiche les statistiques de fréquentation"""
    print("\n" + "="*70)
    print(f"STATISTIQUES DE FRÉQUENTATION - {date_str}")
    print("="*70)
    
    df_actifs = df[df['nombre_passages'] > 0]
    
    print(f"Nombre total de tronçons : {len(df)}")
    print(f"Tronçons avec passages : {len(df_actifs)}")
    print(f"Nombre total de passages : {df_actifs['nombre_passages'].sum():,}")
    print(f"Moyenne de passages par tronçon actif : {df_actifs['nombre_passages'].mean():.1f}")
    print(f"Médiane de passages : {df_actifs['nombre_passages'].median():.0f}")
    
    if len(df_actifs) > 0:
        print(f"\nDistance moyenne : {df_actifs['distance_km'].mean():.2f} km")
        print(f"Vitesse moyenne : {df_actifs['vitesse_moyenne_kmh'].mean():.1f} km/h")
        print(f"Vitesse médiane : {df_actifs['vitesse_moyenne_kmh'].median():.1f} km/h")
        
        print("\n" + "="*70)
        print("TOP 10 - TRONÇONS LES PLUS FRÉQUENTÉS")
        print("="*70)
        top = df_actifs.head(10)[[
            'troncon_unique_id', 'stop_depart_name', 'stop_arrivee_name',
            'nombre_passages', 'vitesse_moyenne_kmh', 'distance_km'
        ]].copy()
        top['vitesse_moyenne_kmh'] = top['vitesse_moyenne_kmh'].round(1)
        top['distance_km'] = top['distance_km'].round(2)
        print(top.to_string(index=False))
        
        print("\n" + "="*70)
        print("TOP 10 - TRONÇONS LES PLUS RAPIDES (avec min 10 passages)")
        print("="*70)
        df_min_passages = df_actifs[df_actifs['nombre_passages'] >= 10]
        if len(df_min_passages) > 0:
            top_rapides = df_min_passages.nlargest(10, 'vitesse_moyenne_kmh')[[
                'troncon_unique_id', 'stop_depart_name', 'stop_arrivee_name',
                'vitesse_moyenne_kmh', 'distance_km', 'nombre_passages'
            ]].copy()
            top_rapides['vitesse_moyenne_kmh'] = top_rapides['vitesse_moyenne_kmh'].round(1)
            top_rapides['distance_km'] = top_rapides['distance_km'].round(2)
            print(top_rapides.to_string(index=False))


def exporter_resultats_frequentation(df, date_str, prefixe='indicateurs_troncons'):
    """Exporte les résultats"""
    output_csv = f"output/{prefixe}_{date_str}.csv"
    # df_export = df.drop(columns=['geometry'], errors='ignore')
    df_export = df
    df_export.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"\n✓ Résultats exportés : {output_csv}")
    return output_csv


def compute_indicateurs_troncons(
        feed,
        date: str,
        reference_troncons_uniques_bus: pd.DataFrame,
        reference_troncons_uniques_tram: pd.DataFrame,
        export_resutls: bool = False,
    ):
    """
    Réalise le calcul des indicateurs par tronçon pour une date d'analyse donnée
    Args:
        feed: gtfs_kit Feed object
            Le feed GTFS chargé
        date (str): Date d'analyse au format YYYYMMDD
        reference_troncons_uniques_bus (pd.DataFrame):
            Table des tronçons uniques bus
        reference_troncons_uniques_tram (pd.DataFrame):
            Table des tronçons uniques tram
    """
    
    # Obtenir les services actifs
    service_ids = obtenir_service_ids_pour_date(feed, date)
    
    # Calculer la fréquentation
    indicateurs_bus = calculer_frequentation_troncons(
        feed, 
        reference_troncons_uniques_bus, 
        service_ids,
        route_type=3  # Bus
    )

    indicateurs_tram = calculer_frequentation_troncons(
        feed, 
        reference_troncons_uniques_tram, 
        service_ids,
        route_type=0  # Tram
    )
    
    if indicateurs_bus is not None and export_resutls:
        exporter_resultats_frequentation(indicateurs_bus, date, prefixe='indicateurs_troncons_bus')
    if indicateurs_tram is not None and export_resutls:
        exporter_resultats_frequentation(indicateurs_tram, date, prefixe='indicateurs_troncons_tram')
    
    return indicateurs_bus, indicateurs_tram



# =============================================================================
# EXEMPLE D'UTILISATION
# =============================================================================

if __name__ == "__main__":

    date_calcul = '20251123'

    # Charger le GTFS
    print("Chargement du GTFS...")
    feed = charger_gtfs()
    
    # Charger la table des tronçons uniques
    df_troncons_uniques_bus = pd.read_csv("output/troncons_uniques_bus.csv")
    df_troncons_uniques_tram = pd.read_csv("output/troncons_uniques_tram.csv")
    
    indicateurs_bus, indicateurs_tram = compute_indicateurs_troncons(
        feed,
        date_calcul,
        df_troncons_uniques_bus,
        df_troncons_uniques_tram,
        export_resutls=True
    )
