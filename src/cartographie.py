import folium
from folium import plugins
import numpy as np
import branca.colormap as cm


def create_carte_arrets(df):
    """
    Crée une carte Folium interactive des indicateurs par arrêt.
    Args:
        df (pd.DataFrame): Dataframe contenant les indicateurs par arrêt.
    Returns:
        folium.Map: Carte Folium interactive.
    """

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

    return m


def creer_carte_troncons(gdf_bus, gdf_tram, colonne_frequence='nombre_passages'):
    """
    Crée une carte Folium interactive avec les tronçons bus et tram.
    Les tronçons sont colorés selon la fréquence et peuvent être activés/désactivés.
    
    Parameters:
    -----------
    gdf_bus : GeoDataFrame
        GeoDataFrame des tronçons bus avec indicateurs
    gdf_tram : GeoDataFrame
        GeoDataFrame des tronçons tram avec indicateurs
    colonne_frequence : str
        Nom de la colonne contenant la fréquence (défaut: 'nombre_passages')
    
    Returns:
    --------
    folium.Map
        Carte Folium interactive
    """
    
    # Déterminer le centre de la carte (moyenne des coordonnées)
    all_coords = []
    for gdf in [gdf_bus, gdf_tram]:
        if len(gdf) > 0:
            all_coords.extend(gdf['lat_depart_parent'].dropna().tolist())
            all_coords.extend(gdf['lat_arrivee_parent'].dropna().tolist())
    
    if not all_coords:
        center_lat, center_lon = 45.75, 4.85  # Lyon par défaut
    else:
        center_lat = np.mean(all_coords)
        all_lons = []
        for gdf in [gdf_bus, gdf_tram]:
            if len(gdf) > 0:
                all_lons.extend(gdf['lon_depart_parent'].dropna().tolist())
                all_lons.extend(gdf['lon_arrivee_parent'].dropna().tolist())
        center_lon = np.mean(all_lons)
    
    # Créer la carte de base
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles='OpenStreetMap'
    )
    
    # Ajouter des fonds de carte alternatifs
    folium.TileLayer('cartodbpositron', name='Carto Positron').add_to(m)
    folium.TileLayer('cartodbdark_matter', name='Carto Dark').add_to(m)
    
    # ===== TRONÇONS BUS =====
    if len(gdf_bus) > 0 and colonne_frequence in gdf_bus.columns:
        # Filtrer les tronçons avec passages
        gdf_bus_actif = gdf_bus[gdf_bus[colonne_frequence] > 0].copy()
        
        if len(gdf_bus_actif) > 0:
            # Créer la palette de couleurs pour les bus
            vmin_bus = gdf_bus_actif[colonne_frequence].min()
            vmax_bus = gdf_bus_actif[colonne_frequence].max()
            
            colormap_bus = cm.LinearColormap(
                colors=['#fee5d9', '#fcae91', '#fb6a4a', '#de2d26', '#a50f15'],
                vmin=vmin_bus,
                vmax=vmax_bus,
                caption=f'fréquence Bus (passages)'
            )
            
            # Créer un groupe de features pour les bus
            feature_group_bus = folium.FeatureGroup(name='🚌 Bus', show=True)
            
            # Ajouter chaque tronçon bus
            for idx, row in gdf_bus_actif.iterrows():
                freq = row[colonne_frequence]
                color = colormap_bus(freq)
                
                # Extraire les coordonnées de la géométrie
                coords = [(coord[1], coord[0]) for coord in row['geometry'].coords]
                
                # Créer le popup avec les informations
                popup_html = f"""
                <div style="font-family: Arial; font-size: 12px; width: 250px;">
                    <b style="color: #d63447;">🚌 TRONÇON BUS</b><br>
                    <hr style="margin: 5px 0;">
                    <b>ID:</b> {row.get('troncon_unique_id', 'N/A')}<br>
                    <b>De:</b> {row.get('stop_depart_name', 'N/A')}<br>
                    <b>À:</b> {row.get('stop_arrivee_name', 'N/A')}<br>
                    <hr style="margin: 5px 0;">
                    <b>Passages:</b> {int(freq)}<br>
                    <b>Vitesse moy.:</b> {row.get('vitesse_moyenne_kmh', 0):.1f} km/h<br>
                    <b>Distance:</b> {row.get('distance_km', 0):.2f} km
                </div>
                """
                
                # Épaisseur proportionnelle à la fréquence
                weight = 2 + (freq - vmin_bus) / (vmax_bus - vmin_bus) * 6
                
                folium.PolyLine(
                    coords,
                    color=color,
                    weight=weight,
                    opacity=0.8,
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{row.get('stop_depart_name', '')} → {row.get('stop_arrivee_name', '')}: {int(freq)} passages"
                ).add_to(feature_group_bus)
            
            feature_group_bus.add_to(m)
            colormap_bus.add_to(m)
    
    # ===== TRONÇONS TRAM =====
    if len(gdf_tram) > 0 and colonne_frequence in gdf_tram.columns:
        # Filtrer les tronçons avec passages
        gdf_tram_actif = gdf_tram[gdf_tram[colonne_frequence] > 0].copy()
        
        if len(gdf_tram_actif) > 0:
            # Créer la palette de couleurs pour les trams
            vmin_tram = gdf_tram_actif[colonne_frequence].min()
            vmax_tram = gdf_tram_actif[colonne_frequence].max()
            
            colormap_tram = cm.LinearColormap(
                colors=['#edf8e9', '#bae4b3', '#74c476', '#31a354', '#006d2c'],
                vmin=vmin_tram,
                vmax=vmax_tram,
                caption=f'fréquence Tram (passages)'
            )
            
            # Créer un groupe de features pour les trams
            feature_group_tram = folium.FeatureGroup(name='🚊 Tram', show=True)
            
            # Ajouter chaque tronçon tram
            for idx, row in gdf_tram_actif.iterrows():
                freq = row[colonne_frequence]
                color = colormap_tram(freq)
                
                # Extraire les coordonnées de la géométrie
                coords = [(coord[1], coord[0]) for coord in row['geometry'].coords]
                
                # Créer le popup avec les informations
                popup_html = f"""
                <div style="font-family: Arial; font-size: 12px; width: 250px;">
                    <b style="color: #28a745;">🚊 TRONÇON TRAM</b><br>
                    <hr style="margin: 5px 0;">
                    <b>ID:</b> {row.get('troncon_unique_id', 'N/A')}<br>
                    <b>De:</b> {row.get('stop_depart_name', 'N/A')}<br>
                    <b>À:</b> {row.get('stop_arrivee_name', 'N/A')}<br>
                    <hr style="margin: 5px 0;">
                    <b>Passages:</b> {int(freq)}<br>
                    <b>Vitesse moy.:</b> {row.get('vitesse_moyenne_kmh', 0):.1f} km/h<br>
                    <b>Distance:</b> {row.get('distance_km', 0):.2f} km
                </div>
                """
                
                # Épaisseur proportionnelle à la fréquence
                weight = 2 + (freq - vmin_tram) / (vmax_tram - vmin_tram) * 6
                
                folium.PolyLine(
                    coords,
                    color=color,
                    weight=weight,
                    opacity=0.8,
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{row.get('stop_depart_name', '')} → {row.get('stop_arrivee_name', '')}: {int(freq)} passages"
                ).add_to(feature_group_tram)
            
            feature_group_tram.add_to(m)
            colormap_tram.add_to(m)
    
    # Ajouter le contrôle des couches (cases à cocher)
    folium.LayerControl(collapsed=False).add_to(m)
    
    # Ajouter un bouton plein écran
    plugins.Fullscreen(
        position='topright',
        title='Plein écran',
        title_cancel='Quitter le plein écran',
        force_separate_button=True
    ).add_to(m)
    
    # Ajouter la mesure de distance
    plugins.MeasureControl(
        position='topleft',
        primary_length_unit='kilometers',
        secondary_length_unit='meters'
    ).add_to(m)
    
    return m
