import gtfs_kit as gk
import pandas as pd
from shapely import wkt
import geopandas as gpd


# Configuration
GTFS_ZIP_PATH = "data/TAM_MMM_GTFS.zip"  # À modifier


########################################################################
# HELPERS GTFS
########################################################################


def charger_gtfs(zip_path=GTFS_ZIP_PATH):
    """
    Charge le fichier GTFS à l'aide de gtfs_kit.
    Returns:
        feed: gtfs_kit Feed object
    """
    print(f"Chargement du fichier GTFS : {zip_path}")
    feed = gk.read_feed(zip_path, dist_units='km')
    print(f"✓ GTFS chargé avec succès")
    return feed


def obtenir_service_ids_pour_date(feed, date_str):
    """
    Identifie les service_id actifs pour une date donnée
    en tenant compte de calendar et calendar_dates
    Args:
        feed: gtfs_kit Feed object
        date_str (str): Date au format 'YYYYMMDD'
    Returns:
        list[str]: Liste des service_id actifs
    """
    date_obj = pd.to_datetime(date_str, format='%Y%m%d')
    jour_semaine = date_obj.strftime('%A').lower()  # lundi, mardi, etc.
    
    # Mapping jour de la semaine -> colonne calendar
    jour_mapping = {
        'monday': 'monday',
        'tuesday': 'tuesday', 
        'wednesday': 'wednesday',
        'thursday': 'thursday',
        'friday': 'friday',
        'saturday': 'saturday',
        'sunday': 'sunday'
    }
    
    service_ids = set()
    
    # 1. Vérifier calendar.txt
    if hasattr(feed, 'calendar') and feed.calendar is not None:
        calendar = feed.calendar.copy()
        # Convertir les dates
        calendar['start_date'] = pd.to_datetime(calendar['start_date'], format='%Y%m%d')
        calendar['end_date'] = pd.to_datetime(calendar['end_date'], format='%Y%m%d')
        
        # Filtrer les services actifs ce jour
        jour_col = jour_mapping[jour_semaine]
        services_calendar = calendar[
            (calendar['start_date'] <= date_obj) &
            (calendar['end_date'] >= date_obj) &
            (calendar[jour_col] == 1)
        ]['service_id'].tolist()
        
        service_ids.update(services_calendar)
    
    # 2. Vérifier calendar_dates.txt (exceptions)
    if hasattr(feed, 'calendar_dates') and feed.calendar_dates is not None:
        calendar_dates = feed.calendar_dates.copy()
        calendar_dates['date'] = pd.to_datetime(calendar_dates['date'], format='%Y%m%d')
        
        exceptions = calendar_dates[calendar_dates['date'] == date_obj]
        
        for _, row in exceptions.iterrows():
            if row['exception_type'] == 1:  # Service ajouté
                service_ids.add(row['service_id'])
            elif row['exception_type'] == 2:  # Service retiré
                service_ids.discard(row['service_id'])
    
    service_ids = list(service_ids)
    print(f"✓ Services actifs le {date_str} : {len(service_ids)} service(s)")
    return service_ids


########################################################################
# UTILITAIRES D'EXPORT ET DE LECTURE
########################################################################


def exporter_df_to_csv(df, chemin_fichier):
    """
    Exporte un DataFrame en CSV
    
    Parameters:
    -----------
    df : DataFrame
        DataFrame à exporter
    chemin_fichier : str
        Chemin du fichier de sortie
    """
    df.to_csv(chemin_fichier, index=False, encoding='utf-8-sig')
    print(f"✓ CSV exporté : {chemin_fichier}")
    
def exporter_gdf_to_csv(gdf, chemin_fichier):
    """
    Exporte un GeoDataFrame en CSV sans la geometry
    
    Parameters:
    -----------
    gdf : GeoDataFrame
        GeoDataFrame à exporter
    chemin_fichier : str
        Chemin du fichier de sortie
    """
    df = gdf.drop(columns=['geometry'], errors='ignore')
    df.to_csv(chemin_fichier, index=False, encoding='utf-8-sig')
    print(f"✓ CSV exporté : {chemin_fichier}")


def exporter_geojson(gdf, chemin_fichier):
    """
    Exporte un GeoDataFrame en GeoJSON.
    
    Parameters:
    -----------
    gdf : GeoDataFrame
        GeoDataFrame à exporter
    chemin_fichier : str
        Chemin du fichier de sortie
    """
    gdf.to_file(chemin_fichier, driver='GeoJSON')
    print(f"✓ GeoJSON exporté : {chemin_fichier}")


def charger_csv_avec_geometrie(chemin_fichier):
    """
    Charge un CSV contenant une colonne 'geometry' en WKT et retourne un GeoDataFrame.
    
    Parameters:
    -----------
    chemin_fichier : str
        Chemin du fichier CSV
    
    Returns:
    --------
    GeoDataFrame
    """
    df = pd.read_csv(chemin_fichier)
    
    if 'geometry' in df.columns:
        df['geometry'] = df['geometry'].apply(wkt.loads)
        gdf = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
    else:
        gdf = gpd.GeoDataFrame(df, crs='EPSG:4326')
    
    return gdf
