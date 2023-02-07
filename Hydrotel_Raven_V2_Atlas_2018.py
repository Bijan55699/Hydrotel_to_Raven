
"""
This script delineates the subbasin map of a watershed using the Physitel inputs/outputs
@author: mohbiz1@ouranos.ca

"""
import pandas as pd
import scipy.io as sio
import shutil
import geopandas as gpd
import os
from geopandas.tools import sjoin
from rasterstats import zonal_stats
import numpy as np

# %% Step1: read the Troncon data (.mat file) and copy the physitel data to /HRU directory
region = 'EST_TRONCON'
Troncon_path = '/home/mohammad/Dossier_travail/Hydrotel/DEH/Atlas_2018/INFO_2018/INFO_TRONCON.mat'
data = sio.loadmat(Troncon_path, struct_as_record=False, squeeze_me=True)
region_name = data[region]
size = region_name.shape[0]
s = size-1
ss = 0
ll=1

workspace = '/home/mohammad/Dossier_travail/Hydrotel/DEH/Atlas_2018/EST_Atlas2018_Subbasin/'
pathtoDirectory = '/home/mohammad/Dossier_travail/Hydrotel/DEH/Atlas_2018/SETZO_2018/EST_SETZO_2018/physitel'
shutil.copytree(pathtoDirectory,workspace)
os.chdir(workspace)
# %% STEP2: Define a Troncon_info dataframe to work with appended data frame .mat file

df = []
for i in range(size):
    rec = region_name[i]
    df.append([rec.NOEUD_AVAL.NUMERO,rec.NOEUD_AMONT.NUMERO,rec.NO_TRONCON,rec.TYPE_NO,rec.LONGUEUR,rec.LARGEUR,rec.UHRH_ASSOCIES,rec.C_MANNING,rec.PENTE_MOYENNE,rec.SUPERFICIE_DRAINEE])
Troncon_info= pd.DataFrame(df,
                           columns = {"NODE_AVAL": int,
                                      "NODE_AMONT": int,
                                      "SubId": int,
                                      "TYPE_NO": int,
                                      "RivLength": float,
                                      "BnkfWidth": float,
                                      "ASSOCI_UHRH": int,
                                      "Ch_n": float,
                                      "RivSlope": float,
                                      "SA_Up": float,
                                      },
                           index = None,
                           )

Troncon_info.loc[Troncon_info.TYPE_NO == 2, 'Ch_n'] = 0.
Troncon_info.loc[Troncon_info.TYPE_NO == 2, 'BnkfWidth'] = 0.
Troncon_info.loc[Troncon_info.TYPE_NO == 2, 'RivLength'] = 0. # for Lake subbasins, the RivLength=0 to avoid in-channel routing process
Troncon_info.loc[Troncon_info.TYPE_NO == 2, 'RivSlope'] = 0. # 



# %%  step1: add subbasin id (SubId) to uhrh shapefile and assign its values based on Troncon_info['ASSOCI_UHRH']

uhrh_fpth = os.path.join(workspace,"uhrh"+ "." + "shp") # The uhrh shape file created by Physitel
uhrh = gpd.read_file(uhrh_fpth)
uhrh['SubId'] = 0


i=0
for i in range(size):
    a = Troncon_info['ASSOCI_UHRH'][i]
    id = Troncon_info['SubId'][i]
    print ('writing subbasin :', i )
    if type(a) is int:
        aa = [a]
        st = len(aa)
        stt = st-1
        dict = {i: aa[i] for i in range(0, len(aa))}
    else:
        al = a.tolist()
        st = len(al)  # number of UHRH associated with current reach
        stt = st - 1
        #create a temporary dictionary
        dict = {i: al[i] for i in range(0, len(al))}
    for j in range(st):
        for index, row in uhrh.iterrows():
            if uhrh.loc[index,'ident'] in dict.values():
                uhrh.loc[index,'SubId'] = id

# %% step2: merge the uhrhs based on SubId field. the number of feature classes in the resulting file should be same sa number of field in Troncon_info

# uhrh_diss = gpd.read_file(os.path.join(workspace,"uhrh_diss"+ "." + "shp"))
uhrh_dissolve = uhrh.dissolve(by='SubId')
uhrh_dissolve.reset_index(inplace=True)    
uhrh_dissolve['BasArea'] = uhrh_dissolve.area  # calculating the Area (m2) of each subbasin       


# step3: finding the downstream subwatershed ID associated with each uhrh

Troncon_info['DowSubId']=-1
for i in range(size):
    naval = Troncon_info['NODE_AVAL'][i]
    for j in range(size):
        namont= Troncon_info['NODE_AMONT'][j]
        id = Troncon_info['SubId'][j]
        if type(namont) is int:
            nal = [namont]
        else:
            nal = namont.tolist()
        if naval in nal: # if naval (downstream node) for reach i is upstream node for reach j, then reach j is downstream reach i
            Troncon_info.loc[i, 'DowSubId'] = id
    
#Troncon_info['Has_Gauge'] = (Troncon_info['DowSubId'] == -1).astype(int)  #create a boolean indicator to set 1 for gauged subwatershed and 0 for others
Troncon_info['Has_Gauge'] = 0 # Has_Gauge should be always 0 in the shapefile (strange?)
Troncon_info['BkfDepth'] = 0.13 * (Troncon_info['SA_Up'] ** 0.4) # taken from equation 10 in paper Fossey et. al., 2015
Troncon_info.loc[Troncon_info.TYPE_NO == 2, 'BkfDepth'] = 0. 
Troncon_info['Lake_Cat']= 0
Troncon_info.loc[Troncon_info.TYPE_NO == 2, 'Lake_Cat'] = 1

Troncon_info = Troncon_info.astype({"Has_Gauge": int, "Lake_Cat": int, "BkfDepth": float, "DowSubId":int})


# TO BE IMPROVED:
# In Troncon_info dataframe, the outlet has the DowSubId of -1, which can be the number of gauge. to be discussed.

# %% step4: determining lake properties using the HydroLAKES database

pth = '/home/mohammad/Dossier_travail/Hydrotel/HydroLAKES_polys_v10_shp'
pth2 = os.path.join(pth,"HydroLAKES_polys_v10_Canada2"+ "." + "shp") # The clipped version of HyLAKES for Canada
HyLAKES_Canada = gpd.read_file(pth2)

pth3 = os.path.join(workspace,"lacs"+ "." + "shp") # The lake shape file created by Physitel
Hydrotel_lakes = gpd.read_file(pth3)

# finding the centroid of the HYLAKES_Canada and intesect with Hydrotel lakes to determine the properties
# HyLAKES_Canada_points  = HyLAKES_Canada.copy()
# HyLAKES_Canada_points['geometry'] = HyLAKES_Canada_points['geometry'].centroid

join_lakes_attr = sjoin(HyLAKES_Canada, Hydrotel_lakes, how="right") 

# join_lakes_attr.to_file('join_lakes_attr.shp')

# Dealing with cases where there are two lakes in subwatershed whereas only one lake is identified in the lacs.shp shapefile by Hydrotel
#finding rows with similar ident (uhrh) value
repeatd_ident = join_lakes_attr[join_lakes_attr.duplicated(subset = ['ident'], keep= False)]

repeatd_ident.reset_index(level=0,inplace = True)

# diss_repeat = 

# diss_repeat = repeatd_ident.groupby('index')['returns'].agg(Mean='mean', Sum='sum')

aggfn = {'ident':'first','Shape_Area':'sum','Depth_avg':'mean','Vol_total':'sum','Lake_area':'sum','Lake_type':'first','index':'first',
         'OBJECTID':'first','Hylak_id':'first'}
diss_repeat = repeatd_ident.dissolve(by = 'index',aggfunc=aggfn)

diss_repeat['Depth_avg'] = diss_repeat['Vol_total']/diss_repeat['Lake_area'] #recalculating lake average depth
diss_repeat['Lake_type'] = int(1)

#replacing this to the repeatd_ident dataframe

join_lakes_attr = join_lakes_attr.drop(diss_repeat.index)
lake_final = (pd.concat([join_lakes_attr,diss_repeat])).sort_index()
lake_final = lake_final.drop(['index_left'], axis=1)

# fill NaN attributes in lake_final polygon

lake_final['Country'].fillna('Canada',inplace=True)
lake_final['Continent'].fillna('North America',inplace=True)
lake_final['Poly_src'].fillna('Hydrotel',inplace=True)
lake_final['Lake_type'].fillna(1,inplace=True)
lake_final['Shape_Area'].fillna(lake_final.area,inplace=True)
lake_final['Lake_area'].fillna(lake_final['Shape_Area']/1000000,inplace=True)
lake_final['Hylak_id'].fillna(100,inplace=True)


# Regional relationship for volume-area of Que/bec: ref: Heathcote et al., 2016.
test_lake = lake_final
lake_final['Vol_total'].fillna(1/1000000*(np.power(10,1.165*np.log10(lake_final['Shape_Area'])+np.log10(0.758))),inplace=True) #volume is in MCM and area is in m

lake_final['Hylak_id'] = lake_final['Hylak_id'].astype(int)
lake_final['Lake_type'] = lake_final['Lake_type'].astype(int)
lake_final['Depth_avg'].fillna(lake_final['Vol_total']/lake_final['Lake_area'],inplace=True)
# lake_final['index'] = lake_final['index'].astype(int)

# os.chdir(workspace)
lake_final.to_file('lake_final.shp')

# Intersecting with uhrh_dissolve to find the SubId of each lake
lake_sub = sjoin(lake_final,uhrh_dissolve,how = 'right',op='within')

lake_sub['LakeArea'] = lake_sub['Lake_area'] * 1000000.  # To convert the area in Km2 in HydroLAKES database to m2
lake_sub['LakeVol'] = lake_sub['Vol_total'] / 1000.  # To convert the volume in MCM in HydroLAKES database to km3
lake_sub['LakeDepth'] = lake_sub['Depth_avg'] 

# os.chdir(workspace)
# lake_sub.to_file('uhrh_with_lake.shp')

# %% step5: add the downstream ID to the shapefile of the created subbasin shapefile (uhrh_diss.shp)    
# pth4 = os.path.join(workspace,"uhrh_with_lake"+ "." + "shp")    

subbasin= pd.merge(Troncon_info,lake_sub, on= 'SubId')
#Lake data from HydroLAKES database
subbasin['HyLakeId'] = subbasin['Hylak_id']
subbasin['Laketype'] = subbasin['Lake_type']
subbasin['FloodP_n'] = subbasin['Ch_n']
# subbasin['LakeArea'] = subbasin['Lake_area']

crs = lake_sub.crs
subbasin = gpd.GeoDataFrame(subbasin,geometry=subbasin['geometry'],crs = crs)

subbasin = subbasin.drop(['NODE_AVAL','NODE_AMONT','ASSOCI_UHRH','index_left','Lake_name','Country','Continent','Poly_src','Grand_id','Shore_len','Shore_dev','Vol_src','Dis_avg',
                          'Res_time','Elevation','Slope_100','Wshd_area','Pour_long','Pour_lat','Hylak_id','ident_left',
                          'ident_right','Lake_area','Vol_res','Vol_total','Lake_type'], axis=1)


# schema = gpd.io.file.infer_schema(subbasin)
# schema['properties']['BnkfWidth'] = 'float'
# schema['properties']['Ch_n'] = 'float'
# schema['properties']['FloodP_n'] = 'float'
# schema['properties']['HyLakeId'] = 'int'
# schema['properties']['Laketype'] = 'int'

# subbasin['RivLength'] = subbasin['RivLength'].astype(float)
# subbasin['BnkfWidth'] = subbasin['BnkfWidth'].astype(float)
# subbasin['Ch_n'] = subbasin['Ch_n'].astype(float)
# subbasin['RivSlope'] = subbasin['RivSlope'].astype(float)
# subbasin['SA_Up'] = subbasin['SA_Up'].astype(float)
# subbasin['BnkfWidth'] = subbasin['BnkfWidth'].astype(float)


# os.chdir(workspace)
# subbasin.to_file('subbasin.shp',schema = schema)



# subbasin = gpd.read_file(pth4)

# subbasin['DowSubId'] = 0
# subbasin['RivLength'] = 0.0
# subbasin['BkfWidth'] = 0.0
# subbasin['BkfDepth'] = 0.0
# subbasin['Has_Gauge'] = 0.0
# subbasin['RivSlope'] = 0.0
# subbasin['Ch_n'] = 0.0
# subbasin['FloodP_n'] = 0.0
# subbasin['Lake_Cat'] = int(0)


# j=0
# for index, row in subbasin.iterrows():
#     if index > subbasin.index[-1]:
#         break
#     subbasin.loc[index,'DowSubId'] = Troncon_info['DowSubId'][j]
#     subbasin.loc[index,'RivLength'] = Troncon_info['RivLength'][j]
#     subbasin.loc[index,'BkfDepth'] = Troncon_info['BkfDepth'][j]
#     subbasin.loc[index,'BkfWidth'] = Troncon_info['BnkfWidth'][j]
#     subbasin.loc[index,'Has_Gauge'] = Troncon_info['Has_Gauge'][j]
#     subbasin.loc[index,'RivSlope'] = Troncon_info['RivSlope'][j]
#     subbasin.loc[index,'Ch_n'] = Troncon_info['Ch_n'][j]
#     subbasin.loc[index,'FloodP_n'] = Troncon_info['Ch_n'][j]    # to be discussed
#     subbasin.loc[index,'Lake_Cat'] = Troncon_info['Lake_Cat'][j]
#     j = j+1



# %% step 6: calculating BasSlope,BasAspect,, and Mean_Elev for each subbasin

# Slope

os.chdir(workspace)
cmd_slope = 'gdaldem  slope altitude.tif slope.tif -compute_edges'
os.system(cmd_slope)
# slope must be between 0 to 60 degree (http://hydrology.uwaterloo.ca/basinmaker/data/resources/attribute_tables_20210429.pdf)

# Aspect
os.chdir(workspace)
cmd_aspect = 'gdaldem  aspect altitude.tif aspect.tif -trigonometric -compute_edges'
os.system(cmd_aspect)


# loop over the subbasin features and adding the mean elevation, mean aspect and 
ss = os.path.join(workspace,"slope"+ "." + "tif") # The lake shape file created by Physitel
# pth5 = os.path.join(workspace,"subbasin"+ "." + "shp") # The lake shape file created by Physitel
# subbasin = gpd.read_file(pth5)

subbasin = subbasin.join(
    pd.DataFrame(
        zonal_stats(
            vectors=subbasin['geometry'], 
            raster= ss, 
            stats=['mean']
        )
    ),
    how='left'
)

subbasin.loc[subbasin['mean'] < 0 , "mean"] = 0 

subbasin['BasSlope'] = subbasin['mean']
subbasin = subbasin.drop(['mean'], axis=1)

#aspect
aa = os.path.join(workspace,"aspect"+ "." + "tif") # The lake shape file created by Physitel

subbasin = subbasin.join(
    pd.DataFrame(
        zonal_stats(
            vectors=subbasin['geometry'], 
            raster= aa, 
            stats=['mean']
        )
    ),
    how='left'
)

subbasin['BasAspect'] = subbasin['mean']
subbasin = subbasin.drop(['mean'], axis=1)

#elevation

ee = os.path.join(workspace,"altitude"+ "." + "tif") # The lake shape file created by Physitel

subbasin = subbasin.join(
    pd.DataFrame(
        zonal_stats(
            vectors=subbasin['geometry'], 
            raster= ee, 
            stats=['mean']
        )
    ),
    how='left'
)

subbasin['MeanElev'] = subbasin['mean']
subbasin = subbasin.drop(['mean'], axis=1)

# some cleaning: removing irrelevant attributes
# subbasin['Lake_Area'] = subbasin['Lake_Are_1']

# subbasin = subbasin.drop(['Lake_name','Country','Continent','Poly_src','Grand_id','Lake_area','Shore_len','Shore_dev','Vol_total',
#                           'Vol_res','Vol_src','Depth_avg','Dis_avg','Res_time','Elevation','Slope_100',
#                           'Wshd_area','Pour_long','Pour_lat','Shape_Leng','Shape_Area','Hylak_id','Lake_Are_1','index_left'], axis=1)

# writing the final subbasin map
schema = gpd.io.file.infer_schema(subbasin)
schema['properties']['BnkfWidth'] = 'float'
schema['properties']['Ch_n'] = 'float'
schema['properties']['FloodP_n'] = 'float'
schema['properties']['HyLakeId'] = 'int'
schema['properties']['Laketype'] = 'int'

os.chdir(workspace)
subbasin.to_file('subbasin.shp',schema = schema)







    
    
    
    