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
from rasterio import features
from rasterio.features import shapes
from pyproj.crs import CRS

# %% 
ss=0

# pathtoDirectory = '/home/mohammad/Dossier_travail/Hydrotel/DEH/MG24HA/SLSO_MG24HA_2020/physitel'
# # workspace = os.path.join(pathtoDirectory+ "/HRU")

workspace = '/home/mohammad/Dossier_travail/Hydrotel/DEH/HRUs_Quebec_meridional/SLSO/20P'
#read the subbasin, land use, and soil maps

subwshd_pth = os.path.join(workspace,"subbasin"+"."+"shp") #subwatershed map created by Hydrotel_Raven_V2 script
lu_raster = os.path.join(workspace,"occupation_sol"+"."+"tif") #Lu map in raster
soil_raster = os.path.join(workspace,"type_sol"+"."+"tif") #soil type map in raster
lake = os.path.join(workspace,"lake_final"+"."+"shp") #lake map
altitude = os.path.join(workspace,"altitude"+ "." + "tif") # The altitude raster map
aspect = os.path.join(workspace,"orientation"+ "." + "tif") # The aspect raster map
slope = os.path.join(workspace,"slope"+ "." + "tif") # The slope raster map
uhrh_pth = os.path.join(workspace,"uhrh"+"."+"shp") # uhrh map of the region (created by Physitel)
subbasin = gpd.read_file(subwshd_pth)
lake_poly = gpd.read_file(lake)

# find the size (resolution) of the raster
rs = rasterio.open(lu_raster)
gt = rs.res
pixelSizeX = gt[0]
pixelSizeY = gt[1]


# %% Converting LU and soil rasters to polygon for further processing


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
ras_crs = CRS(ras_crs)
lu_poly  = gpd.GeoDataFrame.from_features(geoms,crs=ras_crs)
lu_poly = lu_poly.to_crs(subbasin.crs)
lu_poly['LU_ID'] = lu_poly['LU_ID'].astype(int)


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
ras_crs = CRS(ras_crs)

soil_poly  = gpd.GeoDataFrame.from_features(geoms,crs=ras_crs)
soil_poly = soil_poly.to_crs(subbasin.crs)
soil_poly['soil_ID'] = soil_poly['soil_ID'].astype(int)


# %% overlaying the soil and land use map to create the HRU map, using Union tool in Geopandas

hru1 = gpd.overlay(lu_poly, soil_poly, how='intersection')

# os.chdir(workspace)
# hru1.to_file('hru1.shp')


# %% Finding the major land use and soil class in lake polygons

# hru2 = gpd.overlay(lake_poly, hru1, how='intersection')
hru2 = gpd.overlay(lake_poly, hru1, how='intersection')

for index, row in hru2.iterrows():
    if hru2.loc[index,'ident'] < 0 and hru2.loc[index,'ident'] != 'nan':
        hru2.loc[index,'LU_ID'] = 2

hru3 = hru2.dissolve(by='ident',aggfunc = 'first', as_index = False) #aggregate all the polygons that are lake in the hru
hru4 = gpd.overlay(hru1, hru3, how='symmetric_difference')
hru5 = gpd.overlay(hru4, hru3, how='union')

hru5 = hru5.drop(['ident_1'], axis=1)



hru6 = sjoin(lake_poly,hru5,how = 'right',op='within')


hru6['LU'] = int(0)
hru6['SOIL'] = int(0)

for index, row in hru6.iterrows():
    if hru6.loc[index,'ident_2'] < 0 and hru6.loc[index,'ident_2'] != 'nan':
        hru6.loc[index,'LU'] = hru6.loc[index,'LU_ID']
        hru6.loc[index,'SOIL'] = hru6.loc[index,'soil_ID']
    else:
        hru6.loc[index,'LU'] = hru6.loc[index,'LU_ID_1']
        hru6.loc[index,'SOIL'] = hru6.loc[index,'soil_ID_1']

hru6['ident'] = hru6['ident_2']
hru6['Vol_total'] = hru6['Vol_total_2']
hru6['Hylak_id'] = hru6['Hylak_id_2']
hru6['Lake_name'] = hru6['Lake_name_2']
hru6['Poly_src'] = hru6['Poly_src_2']
hru6['Lake_type'] = hru6['Lake_type_2']
hru6['Depth_avg'] = hru6['Depth_avg_2']
hru6['Lake_area'] = hru6['Lake_area_2']
hru6['Shape_Area'] = hru6['Shape_Area_2']

hru7 = hru6.drop(hru6.columns.difference(['OBJECTID','Hylak_id','Lake_name','Poly_src','Lake_type',
                                          'Lake_area','Vol_total','Depth_avg','ident','LU','SOIL','geometry','LU_ID','SOIL_ID',
                                          'Shape_Area']), 1)

# hru7 = hru6.drop(['index_left','LU_ID_1','LU_ID_2','soil_ID_1','soil_ID_2','soil_ID','LU_ID'], axis=1)


# %% calculate major land use and soil classes within each subbasin feature

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
subbasin = subbasin.drop(['majority','Depth_avg','index'], axis=1)

# correcting the subbasin field before intersection with lake map

for index, row in subbasin.iterrows():
    if row['Lake_Cat']==0:
        subbasin.loc[index,'LakeArea'] = 0.
        subbasin.loc[index,'LakeVol'] = 0.
        subbasin.loc[index,'LakeDepth'] = 0.
        subbasin.loc[index,'HyLakeId'] = 0
        subbasin.loc[index,'Laketype'] = 0

# intersecct the hru7 with subbasin to cut the HRU's on subbasin limits

hru8 = gpd.overlay(hru7, subbasin, how='intersection')

for index, row in hru8.iterrows():
    value = row['ident']
    if pd.isnull(value):
        hru8.loc[index,'Lake_Cat'] = 0
        hru8.loc[index,'LakeArea'] = 0.
        hru8.loc[index,'LakeVol'] = 0.
        hru8.loc[index,'Laketype'] = 0
        hru8.loc[index,'LakeDepth'] = 0.
        hru8.loc[index,'HyLakeId'] = 0
        
for index, row in hru8.iterrows():
    if row['LU']==2 and row['Lake_Cat'] < 1 and row['LU_major'] != 2:
        hru8.loc[index,'LU'] = hru8.loc[index,'LU_major']
    elif row['LU']==2 and row['Lake_Cat'] < 1 and row['LU_major'] == 2:
        hru8.loc[index,'LU'] = 9

        
        


#os.chdir(workspace)
hru8.to_file('hru8.shp')


# %% calculate area of each land use class within each subbasin: This will be needed to dissolve small (based on a threshold given by user)
# land use classes by the major one

# rst = rasterio.open("occupation_sol.tif")
# meta = rst.meta.copy()

# subbasin_ras = os.path.join(workspace,"subbasin"+ "." + "tif") # The subbasin raster map

# with rasterio.open(subbasin_ras, 'w+', **meta) as out:
#     out_arr = out.read(1)

#     # this is where we create a generator of geom, value pairs to use in rasterizing
#     shapes = ((geom,value) for geom, value in zip(subbasin.geometry, subbasin.SubId))

#     burned = features.rasterize(shapes=shapes, fill=0, out=out_arr, transform=out.transform)
#     out.write_band(1, burned)
    
# out = os.path.join(workspace,"out"+ "." + "sdat") # The subbasin raster map
# out_table = os.path.join(workspace,"out_table"+ "." + "dbf") # The subbasin raster map

# os.system("saga_cmd grid_analysis 13 " + "-INPUT " + subbasin_ras + "-INPUT2 " + lu_raster + " -RESULTGRID " + out + "-RESULTTABLE "+ out_table + "-MAXNUMCLASS " + "10")

cmap = {1: 'LUID_1', 2: 'LUID_2',3: 'LUID_3',4: 'LUID_4',5: 'LUID_5',6: 'LUID_6',7: 'LUID_7',8: 'LUID_8',9: 'LUID_9'}
zs = zonal_stats(subbasin,lu_raster,categorical=True,category_map = cmap)

zs_df = pd.DataFrame.from_dict(zs)
zs_df = zs_df.fillna(float(0))
zs_df = zs_df * pixelSizeX * pixelSizeY

zs_df.reset_index(inplace=True) 
zs_df['SubId'] = zs_df['index'] +1


subbasin = subbasin.merge(zs_df, on = 'SubId')
 
# %% 
# Defining the threshold and creating the aggregated HRU map
c = hru8.columns
merge = gpd.GeoDataFrame(columns = c,crs = hru8.crs)
hru8['LU_agg'] = hru8['LU']
Threshold = 20 # This is the threshold (%) based on which the land use classes covering smaller than that will be aggreagted to the major land use class
for i in range(subbasin.shape[0]):
    subwsh_number = i + 1
    sub = subbasin.loc[subbasin['SubId'] == subwsh_number] # selects the subbasin a in the subbasin map
    print ('writing subbasin :', subwsh_number )
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

#############################################################################
merge = merge.reset_index()
merge['SOIL'] = merge['SOIL'].astype(int)
merge['LU'] = merge['LU'].astype(int)
merge['SubId'] = merge['SubId'].astype(int)
merge['TYPE_NO'] = merge['TYPE_NO'].astype(int)
merge['RivLength'] = merge['RivLength'].astype(float)
merge['BnkfWidth'] = merge['BnkfWidth'].astype(float)
merge['Ch_n'] = merge['Ch_n'].astype(float)
merge['RivSlope'] = merge['RivSlope'].astype(float)
merge['SA_Up'] = merge['SA_Up'].astype(float)
merge['DowSubId'] = merge['DowSubId'].astype(int)
merge['Has_Gauge'] = merge['Has_Gauge'].astype(int)
merge['BkfDepth'] = merge['BkfDepth'].astype(float)
merge['Lake_Cat'] = merge['Lake_Cat'].astype(int)
merge['Depth_avg'] = merge['Depth_avg'].astype(float)
merge['BasArea'] = merge['BasArea'].astype(float)
merge['LakeVol'] = merge['LakeVol'].astype(float)
merge['LakeDepth'] = merge['LakeDepth'].astype(float)
merge['HyLakeId'] = merge['HyLakeId'].astype('Int64')  # chek after
merge['Laketype'] = merge['Laketype'].astype('Int64')  # check after
merge['FloodP_n'] = merge['FloodP_n'].astype(float)
merge['LakeArea'] = merge['LakeArea'].astype(float)
merge['BasSlope'] = merge['BasSlope'].astype(float)
merge['BasAspect'] = merge['BasAspect'].astype(float)
merge['MeanElev'] = merge['MeanElev'].astype(float)
merge['LU_major'] = merge['LU_major'].astype(int)
merge['soil_major'] = merge['soil_major'].astype(int)
merge['LU_agg'] = merge['LU_agg'].astype(int)


merge['Soil_ID'] = merge['SOIL']
merge['Landuse_ID'] = merge['LU_agg']


st = {1:'SAND', 2:'LOAMY_SAND', 3:'SANDY_LOAM', 4:'LOAM', 5:'SILTY_LOAM', 6:'SILT', 7:'SANDY_CLAY_LOAM', 8:'CLAY_LOAM', 9:'SILTY_CLAY_LOAM',
      10:'SANDY_CLAY', 11:'SILTY_CLAY', 12:'CLAY'}  # to be confirned with DEH

merge['SOIL_PROF'] = merge['Soil_ID'].map(st)


lu_codes = {1:'NO_DATA', 2:'WATER', 3:'BARE_SOIL', 4:'DECIDUOUS_FOREST', 5:'AGRICULTURE', 6:'CONIFEROUS_FOREST', 7:'IMPERMEABLE_SURFACE', 8:'PEATLAND', 9:'WETLAND'}  # to be confirned with DEH

merge['LAND_USE_CODE'] = merge['LU_agg'].map(lu_codes)
merge['VEG_C'] = merge['LAND_USE_CODE']

merge['VEG_C'] = merge['VEG_C'].astype(str)
# os.chdir(workspace)
# merge.to_file('hru10.shp')

# %% add latitude,longitude, HRU ID, Slope, aspect, and Elevation to the HRU feature class


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


# merge = merge.to_crs(4326) # EPSG=4326 (WGS84)
# merge['HRU_CenX'] = merge.centroid.x
# merge['HRU_CenY'] = merge.centroid.y



merge = merge.drop(['index','LU_major','soil_major','LU_agg','LU','SOIL'], axis=1)

# removing the lake information from non-lake HRUs added because of intersection with subbasin map.

merge = merge.reset_index()
for index, row in merge.iterrows():
    if merge.loc[index,'Lake_Cat'] < 1:
        merge.loc[index,'Lake_Area'] = 0.
        merge.loc[index,'HyLakeId'] = 0
        merge.loc[index,'Lake_Cat'] = 0
#        merge.loc[index,'FloodP_n'] = 0.04
        merge.loc[index,'Ch_n'] = 0.04
        merge.loc[index,'LakeVol'] = 0.
        merge.loc[index,'LakeDepth'] = 0.
        merge.loc[index,'Laketype'] = 0
 
        
merge['FloodP_n'] = 0.04 
merge['Laketype'] = merge['Laketype'].astype('Int64')        
# merge.loc[merge.Lake_Cat > 1, 'HRU_IsLake'] = int(1)


merge['BkfWidth'] = merge['BnkfWidth']
merge = merge.drop(['BnkfWidth'], axis=1)

# adding HRU_ID
merge['HRU_ID'] = int(0)
j=1
for index, row in merge.iterrows():
    merge.loc[index,'HRU_ID'] = j
    j = j+1


# %% reading the soil type of a RHHU then mapping its attributes to the HRUs within the RHHU, 
# merge = merge.to_crs(lu_poly.crs)

pth_bv3c = '/home/mohammad/Dossier_travail/Hydrotel/DEH/MG24HA/SLSO_MG24HA_2020/simulation/simulation/bv3c.csv'

soil_layer = pd.read_csv(pth_bv3c,encoding="ISO-8859-1", skiprows=7, index_col=False, delimiter = ';')
uhrh = gpd.read_file(uhrh_pth)
# uhrh.reset_index(inplace=True)   
# uhrh = uhrh.drop(['index'], axis=1)
# merge = merge.drop(['ident_2'], axis=1)

uhrh_sol = uhrh.merge(soil_layer, left_on = 'ident', right_on = 'UHRH ID', how = 'inner')

subbasin_uhrh = sjoin(subbasin,uhrh_sol,how = 'left', op='contains')
# subbasin_uhrh.reset_index(inplace=True)  

# subbasin_uhrh = subbasin_uhrh.drop(['index_right','level_0'], axis=1)
# merge = merge.drop(['index','level_0'], axis=1)


subbasin_uhrh = subbasin_uhrh.loc[:,['EPAISSEUR COUCHE 1 (m)','EPAISSEUR COUCHE 2 (m)','EPAISSEUR COUCHE 3 (m)','ident','geometry', 'UHRH ID']]

# os.chdir(workspace)
# subbasin_uhrh.to_file('subbasin_uhrh.shp')

merge2 = sjoin(merge,subbasin_uhrh,how = 'left',op='within')
merge2 = merge2.drop(['index','index_right','ident_left','ident_right'], axis=1)
merge2.reset_index(inplace=True)  
merge2 = merge2.drop(['index'], axis=1)


merge3 = merge2.dissolve(by=['SubId','LAND_USE_CODE','SOIL_PROF'],aggfunc = 'first', as_index = False) #aggregate all the polygons that are lake in the hru

merge3['Nhorizons'] = int(3)

merge3['TOPSOIL'] = merge3['Soil_ID'].map(st)
merge3['FAST_RES'] = merge3['Soil_ID'].map(st)
merge3['SLOW_RES'] = merge3['Soil_ID'].map(st)


merge3['th1'] = merge3['EPAISSEUR COUCHE 1 (m)'].astype(float)
merge3['th2'] = merge3['EPAISSEUR COUCHE 2 (m)'].astype(float)
merge3['th3'] = merge3['EPAISSEUR COUCHE 3 (m)'].astype(float)

merge3 = merge3.drop(['EPAISSEUR COUCHE 1 (m)','EPAISSEUR COUCHE 2 (m)','EPAISSEUR COUCHE 3 (m)'], axis=1)


# %% 



merge3 = merge3.drop(['Lake_Area'], axis=1)

for index, row in merge3.iterrows():
    if merge3.loc[index,'VEG_C'] != 'WATER' and merge3.loc[index,'Depth_avg'] > 0.:
        merge3.loc[index,'HRU_IsLake'] = -1
        merge3.loc[index,'Lake_Cat'] = 0
        merge3.loc[index,'LakeVol'] = 0
        merge3.loc[index,'LakeDepth'] = 0
        merge3.loc[index,'Depth_avg'] = 0       
        merge3.loc[index,'HyLakeId'] = 0
        merge3.loc[index,'TYPE_NO'] = 1
        merge3.loc[index,'Laketype'] = 0
        merge3.loc[index,'LakeArea'] = 0.0

merge3['HRU_IsLake'] = int(-1)
for index, row in merge3.iterrows():
    if merge3.loc[index,'Lake_Cat'] >0:
        merge3.loc[index,'HRU_IsLake'] = int(1)


for index, row in merge3.iterrows():
    if merge3.loc[index,'Lake_Cat'] >0:
        merge3.loc[index,'SOIL_PROF'] = 'LAKE'

# %%

merge3 = merge3.to_crs(4326) # EPSG=4326 (WGS84)
merge3['HRU_CenX'] = merge3.centroid.x
merge3['HRU_CenY'] = merge3.centroid.y

os.chdir(workspace)
merge3.to_file('HRU_MG24HA2020_SLSO_20P.shp')




# %% Extract the data for the Famine watershed
os.chdir(workspace)
famine = gpd.read_file('subbasin_Famine3.shp')
famine = famine.loc[:,['geometry']]



hru_famine = sjoin(merge3,famine,op='within')
hru_famine = hru_famine.drop(['index_right'], axis=1)


hru_famine = hru_famine.to_crs(4326) # EPSG=4326 (WGS84)
hru_famine['HRU_CenX'] = hru_famine.centroid.x
hru_famine['HRU_CenY'] = hru_famine.centroid.y

os.chdir(workspace)
hru_famine.to_file('hru_Famine_v21.shp')

















