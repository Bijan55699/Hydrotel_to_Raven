
"""
Created on Tue Aug 16 12:17:32 2022

@author: Mohammad Bizhanimanzar


"""
import geopandas as gpd
from shapely.ops import nearest_points

#read the dpolygon and point files
hru = gpd.read_file('/home/mohammad/Dossier_travail/Raven/HRUs/HRU_MG24HA2020_SLSO_20P.shp')
point = gpd.read_file('/home/mohammad/Dossier_travail/Raven/Grid/gridded_station.shp')
points_union = point["geometry"].unary_union



hru["centroid"] = hru.centroid    
# Create an union of the other GeoDataFrame's geometries:

# i=0
# hru['cell_id'] = int(0)
# for index, row in hru.iterrows():
#     hru_number = i + 1
#     hru1 = hru.loc[hru['HRU_ID'] == hru_number] # selects the subbasin a in the subbasin map 
#     print ('writing HRU :', hru_number )
#     nearest_geoms = point['geometry'] == nearest_points(hru1['geometry'], points_union)[1]
#     nearest_data = point.loc[point["geometry"] == nearest_geoms[1]]
#     nearest_value = point[nearest_data]['station_id'].get_values()[0]
#     hru.loc[index,'cell_id'] = nearest_value  


def nearest(row, geom_union, df1, df2, geom1_col='centroid', geom2_col='geometry', src_column=None):
    """Find the nearest point and return the corresponding value from specified column."""
    
    # Find the geometry that is closest
    nearest = df2[geom2_col] == nearest_points(row[geom1_col], geom_union)[1]
    
    # Get the corresponding value from df2 (matching is based on the geometry)
    value = df2[nearest][src_column].get_values()[0]
    
    return value

hru['nearest_id'] = hru.apply(nearest, geom_union=points_union, df1=hru, df2=point, geom1_col='centroid', src_column='station_id', axis=1)












# def get_nearest_values(row,geom_union, df1,df2,geom1_col = 'geometry','geom2_col'):    
    
#     points_union = point["geometry"].unary_union
    
#     # Find the nearest points
#     nearest_geoms = nearest_points(poly["centroid"], points_union)
            
    
#     # Get corresponding values from the point dataset
#     nearest_data = point.loc[point["geometry"] == nearest_geoms[1]]
    
#     nearest_value = nearest_data[column_to_get]
    
#     return nearest_value





# hru['cell_id'] = hru.apply(get_nearest_values,points_union,df1 = hru, df2 = points, col1 = 'centroid', src_column = 'stations',axis = 1)    

# hru1 = hru.loc[hru['HRU_ID'] == 1] # selects the subbasin a in the subbasin map
# # nearest_geoms = nearest_points(hru1["geometry"], points_union)