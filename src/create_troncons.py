import pandas as pd
from shapely.geometry import LineString
from shapely import wkt
import geopandas as gpd

from utils import charger_gtfs


########################################################################
# CREATION DES TABLES DES TRONCONS
########################################################################


def creer_df_troncons(feed, route_type):
    """
    Crée une table de tous les tronçons (segments entre arrêts consécutifs)
    basée sur la séquence réelle des trips. Tient compte des différentes routes
    """
    print("\nCréation de la table des tronçons...")
    
    # Joindre stop_times avec trips pour avoir les route_id
    stop_times_enrichi = feed.stop_times.merge(
        feed.trips[['trip_id', 'route_id']], 
        on='trip_id'
    )

    # Joindre route avec trips pour avoir les route_type
    stop_times_enrichi = stop_times_enrichi.merge(
        feed.routes[['route_id', 'route_type']], 
        on='route_id'
    )
    
    # Joindre avec stops pour avoir les coordonnées
    stop_times_enrichi = stop_times_enrichi.merge(
        feed.stops[['stop_id', 'stop_name', 'stop_lat', 'stop_lon']], 
        on='stop_id'
    )
    
    # Conserver uniquement les routes du type demandé
    stop_times_enrichi = stop_times_enrichi[
        stop_times_enrichi['route_type'] == int(route_type)
    ]

    # Trier par trip_id et stop_sequence pour avoir l'ordre correct
    stop_times_enrichi = stop_times_enrichi.sort_values(['trip_id', 'stop_sequence'])
    
    # Créer les tronçons en décalant les arrêts
    troncons = []
    
    for trip_id, groupe in stop_times_enrichi.groupby('trip_id'):
        groupe = groupe.sort_values('stop_sequence').reset_index(drop=True)
        
        # Pour chaque arrêt (sauf le dernier), créer un tronçon vers l'arrêt suivant
        for i in range(len(groupe) - 1):
            arret_depart = groupe.iloc[i]
            arret_arrivee = groupe.iloc[i + 1]
            
            troncon = {
                'route_id': arret_depart['route_id'],
                'stop_depart_id': arret_depart['stop_id'],
                'stop_arrivee_id': arret_arrivee['stop_id'],
                'stop_depart_name': arret_depart['stop_name'],
                'stop_arrivee_name': arret_arrivee['stop_name'],
                'lat_depart': arret_depart['stop_lat'],
                'lon_depart': arret_depart['stop_lon'],
                'lat_arrivee': arret_arrivee['stop_lat'],
                'lon_arrivee': arret_arrivee['stop_lon']
            }
            
            troncons.append(troncon)
    
    df_troncons = pd.DataFrame(troncons)
    
    # Dédupliquer les tronçons identiques (même route, mêmes arrêts)
    # On garde une seule occurrence de chaque tronçon unique
    df_troncons = df_troncons.drop_duplicates(
        subset=['route_id', 'stop_depart_id', 'stop_arrivee_id']
    ).reset_index(drop=True)
    
    # Générer un identifiant unique pour chaque tronçon
    df_troncons['troncon_id'] = [
        f"T{i:06d}" for i in range(len(df_troncons))
    ]
    
    # Créer l'objet géométrique LineString pour chaque tronçon
    df_troncons['geometry'] = df_troncons.apply(
        lambda row: LineString([
            (row['lon_depart'], row['lat_depart']),
            (row['lon_arrivee'], row['lat_arrivee'])
        ]),
        axis=1
    )
    
    # Réorganiser les colonnes dans l'ordre demandé
    colonnes_finales = [
        'troncon_id',
        'route_id',
        'stop_depart_id',
        'stop_arrivee_id',
        'stop_depart_name',
        'stop_arrivee_name',
        'lat_depart',
        'lon_depart',
        'lat_arrivee',
        'lon_arrivee',
        'geometry'
    ]
    
    df_troncons = df_troncons[colonnes_finales]
    
    print(f"✓ Table des tronçons créée : {len(df_troncons)} tronçons uniques")
    
    return df_troncons


def create_troncons_parents(df_troncons, feed):
    """
    Crée une table des tronçons qui utilise les parent_station des arrêts
    sur la base de la table des tronçons
    """
    modified_stops = feed.stops.copy()
    modified_stops['stop_id_value'] = modified_stops['parent_station'].fillna(modified_stops['stop_id'])

    # Conversion str uniformisation pour jointure
    modified_stops['stop_id_value'] = modified_stops['stop_id_value'].astype(str)
    df_troncons['stop_depart_id'] = df_troncons['stop_depart_id'].astype(str)
    df_troncons['stop_arrivee_id'] = df_troncons['stop_arrivee_id'].astype(str)

    # Arrêt de départ : récupération de la parent station
    df_troncons = df_troncons.merge(
        modified_stops[['stop_id', 'stop_id_value']], 
        left_on='stop_depart_id',
        right_on='stop_id',
        how='left'
    ).rename(columns={
        'stop_id_value': 'stop_depart_parent_id',
    })

    # Arrêt d'arrivée : récupération de la parent station
    df_troncons = df_troncons.merge(
        modified_stops[['stop_id', 'stop_id_value']], 
        left_on='stop_arrivee_id',
        right_on='stop_id',
        how='left'
    ).rename(columns={
        'stop_id_value': 'stop_arrivee_parent_id',
    })

    df_troncons.drop(columns=['stop_id_x', 'stop_id_y'], inplace=True)

    # Récupération de la géométrie de la parent station
    # Doit être fait a posteriori pour récupérer la géométrie de la parent station

    df_troncons = df_troncons.merge(
        modified_stops[['stop_id', 'stop_lat', 'stop_lon']], 
        left_on='stop_depart_parent_id',
        right_on='stop_id',
        how='left'
    ).rename(columns={
        'stop_lat': 'lat_depart_parent',
        'stop_lon': 'lon_depart_parent'
    })

    df_troncons = df_troncons.merge(
        modified_stops[['stop_id', 'stop_lat', 'stop_lon']], 
        left_on='stop_arrivee_parent_id',
        right_on='stop_id',
        how='left'
    ).rename(columns={
        'stop_lat': 'lat_arrivee_parent',
        'stop_lon': 'lon_arrivee_parent'
    })

    df_troncons_parent = df_troncons[[
        'troncon_id',
        'route_id',
        'stop_depart_parent_id',
        'stop_depart_name',
        'stop_arrivee_parent_id',
        'stop_arrivee_name',
        'lat_depart_parent',
        'lon_depart_parent',
        'lat_arrivee_parent',
        'lon_arrivee_parent',
        ]]
    
    # Création de l'objet géométrique
    df_troncons_parent['geometry'] = df_troncons.apply(
        lambda row: LineString([
            (row['lon_depart_parent'], row['lat_depart_parent']),
            (row['lon_arrivee_parent'], row['lat_arrivee_parent'])
        ]),
        axis=1
    )

    return df_troncons_parent


def create_df_troncons_no_routes(df_troncons_parents):
    """
    Crée un df des tronçons unique sans tenir compte des routes ;
    ce df s'appuie sur les tronçons ramenés à leur parent_station.
    On cherche les couples uniques d'arrêts de départ/arrivée.
    """
    df_troncons_no_route = df_troncons_parents.drop_duplicates(
        subset=['stop_depart_parent_id', 'stop_arrivee_parent_id']
    ).reset_index(drop=True)

    # Générer un identifiant unique pour chaque tronçon
    df_troncons_no_route['troncon_no_route_id'] = [
        f"TNR{i:06d}" for i in range(len(df_troncons_no_route))
    ]

    colonnes_finales = [
        'troncon_no_route_id',
        'stop_depart_parent_id',
        'stop_arrivee_parent_id',
        'stop_depart_name',
        'stop_arrivee_name',
        'lat_depart_parent',
        'lon_depart_parent',
        'lat_arrivee_parent',
        'lon_arrivee_parent',
        'geometry'
    ]
    
    df_troncons_no_route = df_troncons_no_route[colonnes_finales]

    return df_troncons_no_route

def create_troncons_uniques(df):
    """
    Crée une liste de tronçons uniques sans distinction de sens.
    Conserve les autres informations associées au premier tronçon rencontré.
    """
    troncons_dict = {}   # clé = tuple(sorted(depart, arrivee)), valeur = dictionnaire des infos

    for _, row in df.iterrows():
        depart = row['stop_depart_parent_id']
        arrivee = row['stop_arrivee_parent_id']

        # clé du tronçon unique (A,B) == (B,A)
        key = tuple(sorted((depart, arrivee)))

        # Si on ne l'a pas encore stocké, on ajoute les infos
        if key not in troncons_dict:
            troncons_dict[key] = {
                'stop_depart_parent_id': depart,
                'stop_arrivee_parent_id': arrivee,
                'stop_depart_name': row['stop_depart_name'],
                'stop_arrivee_name': row['stop_arrivee_name'],
                'lat_depart_parent': row['lat_depart_parent'],
                'lon_depart_parent': row['lon_depart_parent'],
                'lat_arrivee_parent': row['lat_arrivee_parent'],
                'lon_arrivee_parent': row['lon_arrivee_parent'],
                'geometry': row.get('geometry', None)
            }

    # Convertir en liste de dicts
    troncons_uniques = []
    for i, (_, data) in enumerate(troncons_dict.items()):
        data = data.copy()
        data['troncon_unique_id'] = f'TU{i:06d}'
        troncons_uniques.append(data)

    # DataFrame final
    df_unique = pd.DataFrame(troncons_uniques)

    return df_unique



########################################################################
# UTILITAIRES D'EXPORT
########################################################################


def export_table_troncons_csv(df_troncons, chemin_fichier='output/troncons.csv'):
    """Export la table des tronçons au format CSV"""
    df_troncons.to_csv(chemin_fichier, index=False)
    print(f"✓ Table des tronçons exportée vers {chemin_fichier}")


def export_df_to_geojson(df, filename):
    """Export un DataFrame avec une colonne 'geometry' en GeoJSON"""
    gpd_df = gpd.GeoDataFrame(df, geometry='geometry')
    gpd_df.to_file(filename, driver='GeoJSON')
    print(f"✓ Fichier GeoJSON sauvegardé dans '{filename}'")


def read_csv_as_geodataframe(filepath):
    """Lit un fichier CSV avec une colonne 'geometry' en GeoDataFrame
    Retourne un Geodataframe"""
    df = pd.read_csv(filepath)
    df['geometry'] = df['geometry'].apply(wkt.loads)
    gpd_df = gpd.GeoDataFrame(df, geometry='geometry')
    return gpd_df

if __name__ == "__main__":
    feed = charger_gtfs()
    # Tronçons bruts par type de route
    troncons_bus = creer_df_troncons(feed, route_type=3)
    troncons_tram = creer_df_troncons(feed, route_type=0)

    # Tronçons "parents"
    df_troncon_parent_bus = create_troncons_parents(troncons_bus, feed)
    df_troncon_parent_tram = create_troncons_parents(troncons_tram, feed)

    # Tronçons sans routes
    df_troncons_no_routes_bus = create_df_troncons_no_routes(df_troncon_parent_bus)
    df_troncons_no_routes_tram = create_df_troncons_no_routes(df_troncon_parent_tram)

    # Tronçons uniques
    df_troncons_uniques_bus = create_troncons_uniques(df_troncons_no_routes_bus)
    df_troncons_uniques_bus.to_csv('output/troncons_uniques_bus.csv', index=False)
    
    df_troncons_uniques_tram = create_troncons_uniques(df_troncons_no_routes_tram)
    df_troncons_uniques_tram.to_csv('output/troncons_uniques_tram.csv', index=False)

    # Export geojson
    df_troncons_uniques_bus["geometry"] = df_troncons_uniques_bus["geometry"].apply(wkt.loads)
    gpd_df_troncons_uniques_bus = gpd.GeoDataFrame(df_troncons_uniques_bus, geometry='geometry')
    gpd_df_troncons_uniques_bus.to_file('output/troncons_uniques_bus.geojson', driver='GeoJSON')

    df_troncons_uniques_tram["geometry"] = df_troncons_uniques_tram["geometry"].apply(wkt.loads)
    gpd_df_troncons_uniques_tram = gpd.GeoDataFrame(df_troncons_uniques_tram, geometry='geometry')
    gpd_df_troncons_uniques_tram.to_file('output/troncons_uniques_tram.geojson', driver='GeoJSON')

    pass