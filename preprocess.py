import json

import numpy as np
import pandas as pd
import geopandas as gpd

def meter_counts():
    """
    Loads the parking ticket data and the metered parking space polygons.

    Figures out how many tickets were issued at each meter.

    """
    # Load up the tickets and meters data
    tickets = pd.read_csv('data/Cambridge_Parking_Tickets_for_the_period_January_thru_June_2014.csv')
    meters = gpd.read_file('data/TRAFFIC_MeteredParkingSpaces.geojson')

    # Get the number of tickets for each meter
    counts = tickets['Meter'].value_counts()
    counts.name = 'count'

    # Assign the count back to each meter
    meters = meters.join(counts, on='SPACE_ID')

    # Only keep the meters that have at least one ticket
    meters = meters.loc[meters['count'] > 0, :]

    # Set the geometry to be the centroid instead of the polygon
    meters.set_geometry(meters.centroid, inplace=True)

    return meters


def tile_counts(meters=None, zmin=12, zmax=21):
    from mercantile import tile, bounds
    from shapely.geometry import box
    if meters is None:
        meters = meter_counts()

    # For each zoom level, compute the tile (x, y, z) for each point
    # and get the number of meters and total number of tickets in each
    # tile. Store the resulting geojson in a dictionary keyed on zoom level
    fcs = {}
    for z in range(zmin, zmax+1):
        tiles = meters['geometry'].apply(lambda x: tile(x.x, x.y, z))
        tile_agg = meters.groupby(tiles)['count'].agg(
            {'meters': len, 'tickets': np.sum})
        geometry = tile_agg.index.to_series().apply(lambda x: box(*bounds(*x)))
        tile_agg = tile_agg.set_geometry(geometry).reset_index(drop=True)
        tile_agg['density'] = tile_agg['tickets'] / tile_agg['meters']

        fcs[z] = tile_agg.__geo_interface__

    return fcs


def preprocess():
    meters = meter_counts()

    # Write out the geojson
    with open('data/meters_and_counts.geojson', 'w') as f:
        f.write(meters.to_json())

    feature_collections = tile_counts(meters)
    with open('data/zoom_ticket_densities.json', 'w') as f:
        json.dump(feature_collections, f)
