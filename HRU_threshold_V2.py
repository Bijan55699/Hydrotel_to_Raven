"""
This script delineates the HRU map of a watershed using the Physitel inputs/outputs
@author: mohbiz1@ouranos.ca

"""
import pandas as pd
import os
import geopandas as gpd
from geopandas.tools import sjoin
from rasterstats import zonal_stats
import rasterio
from rasterio.features import shapes

###################################################################################################
pathtoDirectory = r"C:\Users\mohbiz1\Desktop\Dossier_travail\Hydrotel\DEH\MG24HA\SLSO_MG24HA_2020\physitel"
workspace = os.path.join(pathtoDirectory+ "\HRU")

#read the subbasin, land use, and soil maps

subwshd_pth = os.path.join(workspace,"subbasin_final"+"."+"shp") #subwatershed map created by Hydrotel_Raven_V2 script
lu_raster = os.path.join(workspace,"occupation_sol"+"."+"tif") #Lu map in raster
soil_raster = os.path.join(workspace,"type_sol"+"."+"tif") #soil type map in raster
lake = os.path.join(workspace,"lacs"+"."+"shp") #lake map
altitude = os.path.join(workspace,"altitude"+ "." + "tif") # The altitude raster map
aspect = os.path.join(workspace,"orientation"+ "." + "tif") # The aspect raster map
slope = os.path.join(workspace,"pente"+ "." + "tif") # The slope raster map
# Converting LU and soil rasters to polygon for further processing


# land use map

with rasterio.Env():
    with rasterio.open(lu_raster) as src:
        lu = src.read(1) # first band
        mask = src.dataset_mask()
        ras_crs = src.crs
        results = (
        {'properties': {'LU_ID': v}, 'geometry': s}
        for i, (s, v) 
        in enumerate(
            shapes(lu, mask=mask, transform=src.transform)))

geoms = list(results)
lu_poly  = gpd.GeoDataFrame.from_features(geoms,crs=ras_crs)

os.chdir(workspace)
lu_poly.to_file('lu_test.shp')

# soil

with rasterio.Env():
    with rasterio.open(soil_raster) as src:
        soil = src.read(1) # first band
        mask = src.dataset_mask()
        ras_crs = src.crs
        results = (
        {'properties': {'soil_ID': v}, 'geometry': s}
        for i, (s, v) 
        in enumerate(
            shapes(soil, mask=mask, transform=src.transform)))

geoms = list(results)
soil_poly  = gpd.GeoDataFrame.from_features(geoms,crs=ras_crs)

os.chdir(workspace)
soil_poly.to_file('soil_type.shp')

# overlaying the soil and land use map to create the HRU map, using Union tool in Geopandas

hru1 = gpd.overlay(lu_poly, soil_poly, how='intersection')

# os.chdir(workspace)
# hru1.to_file('hru1.shp')


# Finding the major land use and soil class in lake polygons
lake_poly = gpd.read_file(lake)
# # land use
# lake_poly = lake_poly.join(
#     pd.DataFrame(
#         zonal_stats(
#             vectors=lake_poly['geometry'], 
#             raster= lu_raster, 
#             stats=['majority']
#         )
#     ),
#     how='left'
# )

# lake_poly['LU_major_lake'] = lake_poly['majority']
# lake_poly = lake_poly.drop(['majority'], axis=1)

# #soil
# lake_poly = lake_poly.join(
#     pd.DataFrame(
#         zonal_stats(
#             vectors=lake_poly['geometry'], 
#             raster= soil_raster, 
#             stats=['majority']
#         )
#     ),
#     how='left'
# )

# lake_poly['soil_major_lake'] = lake_poly['majority']
# lake_poly = lake_poly.drop(['majority'], axis=1)

# Union lake polygon with HRU map (a lake is a unique HRU)

hru2 = gpd.overlay(lake_poly, hru1, how='intersection')
hru3 = hru2.dissolve(by='ident',aggfunc = 'first') #aggregate all the polygons that are lake in the hru
hru4 = gpd.overlay(hru1, hru3, how='symmetric_difference')
hru5 = gpd.overlay(hru4, hru3, how='union')


# os.chdir(workspace)
# hru5.to_file('hru5.shp')

hru6 = sjoin(lake_poly,hru5,how = 'right',op='within')
# os.chdir(workspace)
# hru6.to_file('hru6.shp')

hru6['LU'] = 0
hru6['SOIL'] = 0
for index, row in hru6.iterrows():
    if hru6.loc[index,'ident'] < 0 and hru6.loc[index,'ident'] != 'nan':
        hru6.loc[index,'LU'] =2
        hru6.loc[index,'SOIL'] = hru6.loc[index,'soil_ID']
    else:
        hru6.loc[index,'LU'] = hru6.loc[index,'LU_ID_1']
        hru6.loc[index,'SOIL'] = hru6.loc[index,'soil_ID_1']


hru7 = hru6.drop(['index_left','LU_ID_1','LU_ID_2','soil_ID_1','soil_ID_2','soil_ID','LU_ID'], axis=1)

#os.chdir(workspace)
#hru7.to_file('hru7.shp')

# calculate major land use and soil classes within each subbasin feature
subbasin = gpd.read_file(subwshd_pth)
# land use
subbasin = subbasin.join(
    pd.DataFrame(
        zonal_stats(
            vectors=subbasin['geometry'], 
            raster= lu_raster, 
            stats=['majority']
        )
    ),
    how='left'
)

subbasin['LU_major'] = subbasin['majority'].astype(int)
subbasin = subbasin.drop(['majority'], axis=1)

#soil
subbasin = subbasin.join(
    pd.DataFrame(
        zonal_stats(
            vectors=subbasin['geometry'], 
            raster= soil_raster, 
            stats=['majority']
        )
    ),
    how='left'
)

subbasin['soil_major'] = subbasin['majority'].astype(int)
subbasin = subbasin.drop(['majority'], axis=1)


# intersecct the hru7 with subbasin to cut the HRU's on subbasin limits

hru8 = gpd.overlay(hru7, subbasin, how='intersection')

#os.chdir(workspace)
#hru8.to_file('hru8.shp')


# calculate area of each land use class within each subbasin: This will be needed to dissolve small (based on a threshold given by user)
# land use classes by the major one
subbasin ['LUID_1'] = 0.  # No data
subbasin ['LUID_2'] = 0.  # Water
subbasin ['LUID_3'] = 0.  # Bare soil
subbasin ['LUID_4'] = 0.  # deciduous forest
subbasin ['LUID_5'] = 0.  # agricultur
subbasin ['LUID_6'] = 0.  # coniferous forest
subbasin ['LUID_7'] = 0.  # impermeable surface
subbasin ['LUID_8'] = 0.  # peatland
subbasin ['LUID_9'] = 0.  # wetland

for index, row in subbasin.iterrows():
    sub = subbasin.loc[subbasin['SubId'] == subbasin['SubId'][index]] # selects the subbasin a in the subbasin map
    intersection = gpd.overlay(sub, lu_poly, how='intersection') # intersection operation
    intersection['area'] = intersection.area  # the area of each row in the intersection   
    subbasin.loc[index,'LUID_2'] = intersection.loc[intersection['LU_ID'] == 2,'area'].sum()
    subbasin.loc[index,'LUID_3'] = intersection.loc[intersection['LU_ID'] == 3,'area'].sum()
    subbasin.loc[index,'LUID_4'] = intersection.loc[intersection['LU_ID'] == 4,'area'].sum()
    subbasin.loc[index,'LUID_5'] = intersection.loc[intersection['LU_ID'] == 5,'area'].sum()
    subbasin.loc[index,'LUID_6'] = intersection.loc[intersection['LU_ID'] == 6,'area'].sum()
    subbasin.loc[index,'LUID_7'] = intersection.loc[intersection['LU_ID'] == 7,'area'].sum()
    subbasin.loc[index,'LUID_8'] = intersection.loc[intersection['LU_ID'] == 8,'area'].sum()
    subbasin.loc[index,'LUID_9'] = intersection.loc[intersection['LU_ID'] == 9,'area'].sum()
        
os.chdir(workspace)
subbasin.to_file('subbasin2.shp')
 
## ##########################################################
# Defining the threshold and creating the aggregated HRU map
c = hru8.columns
merge = gpd.GeoDataFrame(columns = c,crs = hru8.crs)
hru8['LU_agg'] = hru8['LU']
Threshold = 5 # This is the threshold (%) based on which the land use classes covering smaller than that will be aggreagted to the major land use class
for i in range(subbasin.shape[0]):
    subwsh_number = i + 1
    sub = subbasin.loc[subbasin['SubId'] == subwsh_number] # selects the subbasin a in the subbasin map
    lu_major = sub['LU_major'][i]
    area_total = sub['BasArea'][i]
    perc_lu2 = (sub['LUID_2'][i]/area_total)*100.
    perc_lu3 = (sub['LUID_3'][i]/area_total)*100.
    perc_lu4 = (sub['LUID_4'][i]/area_total)*100.
    perc_lu5 = (sub['LUID_5'][i]/area_total)*100.
    perc_lu6 = (sub['LUID_6'][i]/area_total)*100.
    perc_lu7 = (sub['LUID_7'][i]/area_total)*100.
    perc_lu8 = (sub['LUID_8'][i]/area_total)*100.
    perc_lu9 = (sub['LUID_9'][i]/area_total)*100.
    # hru check and modifications
    hru_temp = hru8.loc[hru8['SubId'] == subwsh_number] # selects the subbasin a in the subbasin map
    for index, row in hru_temp.iterrows():
        #check the percentage with threshold
        # if (row.LU==2):
        #     if (perc_lu2<=Threshold and perc_lu2>0 and row.Lake_Cat==0):
        #         hru_temp.loc[index,'LU_agg'] = lu_major
        if (row.LU==3):
            if (perc_lu3<=Threshold and perc_lu3>0 and lu_major!=2):
                hru_temp.loc[index,'LU_agg'] = lu_major        
        if (row.LU==4):
            if (perc_lu4<=Threshold and perc_lu4>0 and lu_major!=2):
                hru_temp.loc[index,'LU_agg'] = lu_major  
        if (row.LU==5):
            if (perc_lu5<=Threshold and perc_lu5>0 and lu_major!=2):
                hru_temp.loc[index,'LU_agg'] = lu_major  
        if (row.LU==6):
            if (perc_lu6<=Threshold and perc_lu6>0 and lu_major!=2):
                hru_temp.loc[index,'LU_agg'] = lu_major  
        if (row.LU==7):
            if (perc_lu7<=Threshold and perc_lu7>0 and lu_major!=2):
                hru_temp.loc[index,'LU_agg'] = lu_major  
        if (row.LU==8):
            if (perc_lu8<=Threshold and perc_lu8>0 and lu_major!=2):
                hru_temp.loc[index,'LU_agg'] = lu_major  
        if (row.LU==9):
            if (perc_lu9<=Threshold and perc_lu9>0 and lu_major!=2):
                hru_temp.loc[index,'LU_agg'] = lu_major
    # import pdb; pdb.set_trace()
    temp = hru_temp.dissolve(by = ["LU_agg","SOIL"], as_index = False)
    temp2 = merge.append(temp)
    merge = temp2

# os.chdir(workspace)
# merge.to_file('hru9.shp')


#############################################################################
merge = merge.reset_index()
merge['SOIL'] = merge['SOIL'].astype(int)
merge['LU'] = merge['LU'].astype(int)
merge['Soil_ID'] = merge['SOIL']
merge['Landuse_ID'] = merge['LU_agg']

st = {1:'sand', 2:'loamy_sand', 3:'sandy_loam', 4:'loam', 5:'silt_loam', 6:'silt', 7:'sandy_clay_loam', 8:'clay_loam', 9:'silty_clay_loam',
      10:'sandy_clay', 11:'silty_clay', 12:'clay'}  # to be confirned with DEH

merge['SOIL_PROF'] = merge['Soil_ID'].map(st)


lu_codes = st = {1:'No_data', 2:'Water', 3:'bare_soil', 4:'deciduous_forest', 5:'agriculture', 6:'coniferous_forest', 7:'impermeable_surface', 8:'peatland', 9:'wetland'}  # to be confirned with DEH

merge['LAND_USE_CODE'] = merge['LU_agg'].map(lu_codes)


os.chdir(workspace)
merge.to_file('hru10.shp')
#############################################################
## add latitude,longitude, HRU ID, Slope, aspect, and Elevation to the HRU feature class

# adding HRU_ID
merge['HRU_ID'] = 0
j=1
for index, row in merge.iterrows():
    merge.loc[index,'HRU_ID'] = j
    j = j+1


# calculating the ara of each HRU polygon in m2
merge['HRU_Area'] = merge.area  

# adding mean elevation of each HRU 

#elevation

merge = merge.join(
    pd.DataFrame(
        zonal_stats(
            vectors=merge['geometry'], 
            raster= altitude, 
            stats=['mean']
        )
    ),
    how='left'
)

merge['HRU_E_mean'] = merge['mean']
merge = merge.drop(['mean'], axis=1)


#aspect

merge = merge.join(
    pd.DataFrame(
        zonal_stats(
            vectors=merge['geometry'], 
            raster= aspect, 
            stats=['mean']
        )
    ),
    how='left'
)

merge['HRU_A_mean'] = merge['mean']
merge = merge.drop(['mean'], axis=1)


# adding mean slope


# pth5 = os.path.join(workspace,"subbasin"+ "." + "shp") # The lake shape file created by Physitel
# subbasin = gpd.read_file(pth5)

merge = merge.join(
    pd.DataFrame(
        zonal_stats(
            vectors=merge['geometry'], 
            raster= slope, 
            stats=['mean']
        )
    ),
    how='left'
)

merge.loc[merge['mean'] < 0 , "mean"] = 0 

merge['HRU_S_mean'] = merge['mean']
merge = merge.drop(['mean'], axis=1)

# adding latitude, longitude

merge['HRU_CenX'] = merge.centroid.x
merge['HRU_CenY'] = merge.centroid.y



merge = merge.drop(['index_left','ident','index','OBJECTID','LU_major','soil_major','LU_agg','LU','SOIL'], axis=1)

# removing the lake information from non-lake HRUs added because of intersection with subbasin map.

for index, row in merge.iterrows():
    if merge.loc[index,'Landuse_ID'] > 2:
        merge.loc[index,'Lake_Area'] = 0.
        merge.loc[index,'HyLakeId'] = 0.
        merge.loc[index,'Lake_Cat'] = 0
        merge.loc[index,'FloodP_n'] = 0.04
        merge.loc[index,'Ch_n'] = 0.04
        merge.loc[index,'Lake_Vol'] = 0.
        merge.loc[index,'LakeDepth'] = 0.
        merge.loc[index,'Lake_type'] = 0.

os.chdir(workspace)
merge.to_file('hru_final.shp')
























