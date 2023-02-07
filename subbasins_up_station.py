
"""
Created on Mon Oct  3 15:28:01 2022

@author: mohammad
"""

import numpy as np
import geopandas
from ravenpy.utilities.geoserver import _determine_upstream_ids
import os


workspace = '/home/mohammad/Dossier_travail/Hydrotel/DEH/MG24HA/SLSO_MG24HA_2020/physitel/subbasins'
os.chdir(workspace)
stations_shp = '/home/mohammad/Dossier_travail/Hydrotel/DEH/GIS_28st/stations_SLSO_test.shp'
stations = geopandas.read_file(stations_shp)
stations = stations.sort_values(by='Subbasins',ascending=False)


hydro_shp = '/home/mohammad/Dossier_travail/Hydrotel/DEH/HRUs_Quebec_meridional/SLSO/20P/subbasin.shp'
gdf = geopandas.read_file(hydro_shp)

# loop through the stations and create the aggregated subbasin
merge = geopandas.GeoDataFrame(columns = gdf.columns,crs = gdf.crs)
for index, row in stations.iterrows():
     fid = row['Subbasins']
     df = _determine_upstream_ids(fid,gdf,'SubId','DowSubId')
     

     df['drain_to'] = fid
     df_dissolve = df.dissolve(by = ["drain_to"], aggfunc = 'first', as_index = False)
     merge = merge.append(df_dissolve)
     # del df_dissolve
     # merge = temp2
     # fname = "SubbasinsUp_%s.shp" %fid
     # df_dissolve.to_file(fname)
     
merge.to_file('merged_subbasins.shp')

###################################################################################################################

