"""
This script creates the subbasin map from a Hydrotel project directory

Inputs:

1- region_name = should be among following list:

1- troncon_path: The path to The INFO_TRONCON.mat (provided by DEH) file which contains the river reaches (troncon) properties of the region.
2- hydroteldir: The hydrotel project directory path
3- workspace: The working directory to create the outputs

Ouput:

1- Subbasin polygon


References:

1- The river depth information is based on Hydrotel's depth-area relationship given in : https://onlinelibrary.wiley.com/doi/10.1002/hyp.10534
2- The HydroLakes database is used for determining lake volume, depth and areas. reference: https://www.hydrosheds.org/products/hydrolakes
3- The volum-area-depth relationship of lakes that are not identified by Hydrolakes is based on fitted relationship for Quebec's lake in :  https://agupubs.onlinelibrary.wiley.com/doi/full/10.1002/2016GL071378


"""
import pandas as pd
import scipy.io as sio
import shutil
import geopandas as gpd
import os
from geopandas.tools import sjoin
from rasterstats import zonal_stats
import numpy as np


def uhrh_to_sub(region_name, troncon_path, workspace, hydroteldir):
    regions_list = ['ABIT_TRONCON','CNDA_TRONCON','CNDB_TRONCON','CNDC_TRONCON','CNDD_TRONCON','CNDE_TRONCON','GASP_TRONCON','LABI_TRONCON','MONT_TRONCON',
                    'OUTM_TRONCON','OUTV_TRONCON','SAGU_TRONCON','SLNO_TRONCON','SLSO_TRONCON','VAUD_TRONCON']
    if region_name not in regions_list:
        print('the'+region_name+'is not recognized! please make sure the name is among the regions list!')
    data = sio.loadmat(troncon_path, struct_as_record=False, squeeze_me=True)
    region = data[region_name]
    size = region.shape[0]
    shutil.copytree(hydroteldir, workspace)
    os.chdir(workspace)
    df = []
    for i in range(size):
        rec = region[i]
        df.append(
            [rec.NOEUD_AVAL.NUMERO, rec.NOEUD_AMONT.NUMERO, rec.NO_TRONCON, rec.TYPE_NO, rec.LONGUEUR, rec.LARGEUR, 0,
             rec.UHRH_ASSOCIES, rec.C_MANNING, rec.PENTE_MOYENNE, rec.SUPERFICIE_DRAINEE, 0, 0, 0])
    troncon_info = pd.DataFrame(df, columns={"NODE_AVAL": int,
                                             "NODE_AMONT": int,
                                             "SubId": int,
                                             "TYPE_NO": int,
                                             "RivLength": float,
                                             "BnkfWidth": float,
                                             "BkfDepth":float,
                                             "ASSOCI_UHRH": int,
                                             "Ch_n": float,
                                             "RivSlope": float,
                                             "SA_Up": float,
                                             "Has_Gauge":int,
                                             "Lake_Cat":int,
                                             "DowSubId":int},
                                index=None,
                                )
    # special values for non-river (lake) features
    troncon_info['Has_Gauge'] = 0  # Has_Gauge should be always 0 in the shapefile (strange?)
    troncon_info['BkfDepth'] = 0.13 * (troncon_info['SA_Up'] ** 0.4)  # taken from equation 10 of Fossey et. al., 2015
    troncon_info.loc[troncon_info.TYPE_NO == 2, {'Ch_n','BnkfWidth','RivLength','RivSlope','BkfDepth'}] = 0.
    troncon_info['Lake_Cat'] = 0
    troncon_info.loc[troncon_info.TYPE_NO == 2, 'Lake_Cat'] = 1 # for Lakes
    # Assigning the SubId to uhrh geodataframe
    uhrh_fpth = os.path.join(workspace, "uhrh" + "." + "shp")  # The uhrh shape file created by Physitel
    uhrh = gpd.read_file(uhrh_fpth)
    uhrh['SubId'] = 0

    # In this loop the SubIds will be added to the uhrh geodataframe.
    for i in range(size):
        a = troncon_info['ASSOCI_UHRH'][i]
        id = troncon_info['SubId'][i]
        print('writing subbasin :', i)
        if type(a) is int:
            aa = [a]
            st = len(aa)
            stt = st - 1
            dict = {i: aa[i] for i in range(0, len(aa))}
        else:
            al = a.tolist()
            st = len(al)  # number of UHRH associated with current reach
            stt = st - 1
            # create a temporary dictionary
            dict = {i: al[i] for i in range(0, len(al))}
        for j in range(st):
            for index, row in uhrh.iterrows():
                if uhrh.loc[index, 'ident'] in dict.values():
                    uhrh.loc[index, 'SubId'] = id

    # Dissolve the uhrh geodataframe based on SubIds
    uhrh_dissolve = uhrh.dissolve(by='SubId')
    uhrh_dissolve.reset_index(inplace=True)
    uhrh_dissolve['BasArea'] = uhrh_dissolve.area  # calculating the Area (m2) of each subbasin

    # Finding the downstream subwatershed ID associated with each uhrh
    troncon_info['DowSubId'] = -1
    for i in range(size):
        naval = troncon_info['NODE_AVAL'][i]
        for j in range(size):
            namont = troncon_info['NODE_AMONT'][j]
            id = troncon_info['SubId'][j]
            if type(namont) is int:
                nal = [namont]
            else:
                nal = namont.tolist()
            if naval in nal:  # if naval (downstream node) for reach i is upstream node for reach j, then reach j is downstream reach i
                troncon_info.loc[i, 'DowSubId'] = id
    return troncon_info, uhrh_dissolve
def process_lakes(workspace, hydrolakes_file,troncon_info,uhrh_dissolve):
    HyLAKES_Canada = gpd.read_file(hydrolakes_file)
    pth3 = os.path.join(workspace, "lacs" + "." + "shp")  # The lake shape file created by Physitel
    Hydrotel_lakes = gpd.read_file(pth3)

    join_lakes_attr = sjoin(HyLAKES_Canada, Hydrotel_lakes, how="right")

    # Dealing with cases where there are two lakes in subwatershed whereas only one lake is identified in the lacs.shp shapefile by Hydrotel
    # finding rows with similar ident (uhrh) value
    repeatd_ident = join_lakes_attr[join_lakes_attr.duplicated(subset=['ident'], keep=False)]

    repeatd_ident.reset_index(level=0, inplace=True)

    # diss_repeat =

    # diss_repeat = repeatd_ident.groupby('index')['returns'].agg(Mean='mean', Sum='sum')

    aggfn = {'ident': 'first', 'Shape_Area': 'sum', 'Depth_avg': 'mean', 'Vol_total': 'sum', 'Lake_area': 'sum',
             'Lake_type': 'first', 'index': 'first',
             'OBJECTID': 'first', 'Hylak_id': 'first'}
    diss_repeat = repeatd_ident.dissolve(by='index', aggfunc=aggfn)

    diss_repeat['Depth_avg'] = diss_repeat['Vol_total'] / diss_repeat['Lake_area']  # recalculating lake average depth
    diss_repeat['Lake_type'] = int(1)

    join_lakes_attr = join_lakes_attr.drop(diss_repeat.index)
    lake_final = (pd.concat([join_lakes_attr, diss_repeat])).sort_index()
    lake_final = lake_final.drop(['index_left'], axis=1)

    # fill NaN attributes in lake_final polygon

    lake_final['Country'].fillna('Canada', inplace=True)
    lake_final['Continent'].fillna('North America', inplace=True)
    lake_final['Poly_src'].fillna('Hydrotel', inplace=True)
    lake_final['Lake_type'].fillna(1, inplace=True)
    lake_final['Shape_Area'].fillna(lake_final.area, inplace=True)
    lake_final['Lake_area'].fillna(lake_final['Shape_Area'] / 1000000, inplace=True)
    lake_final['Hylak_id'].fillna(100, inplace=True)

    # Regional relationship for lake's volume-area for Quebec: ref: Heathcote et al., 2016.
    lake_final['Vol_total'].fillna(
        1 / 1000000 * (np.power(10, 1.165 * np.log10(lake_final['Shape_Area']) + np.log10(0.758))),
        inplace=True)  # volume is in MCM and area is in m

    lake_final['Hylak_id'] = lake_final['Hylak_id'].astype(int)
    lake_final['Lake_type'] = lake_final['Lake_type'].astype(int)
    lake_final['Depth_avg'].fillna(lake_final['Vol_total'] / lake_final['Lake_area'], inplace=True)
    # lake_final['index'] = lake_final['index'].astype(int)

    # os.chdir(workspace)
    lake_final.to_file('lake_final.shp')

    # Intersecting with uhrh_dissolve to find the SubId of each lake
    lake_sub = sjoin(lake_final, uhrh_dissolve, how='right', op='within')

    lake_sub['LakeArea'] = lake_sub['Lake_area'] * 1000000.  # To convert the area in Km2 in HydroLAKES database to m2
    lake_sub['LakeVol'] = lake_sub['Vol_total'] / 1000.  # To convert the volume in MCM in HydroLAKES database to km3
    lake_sub['LakeDepth'] = lake_sub['Depth_avg']

def create_subbasin(troncon_info,lake_sub):
    subbasin = pd.merge(troncon_info, lake_sub, on='SubId')
    # Lake data from HydroLAKES database
    subbasin['HyLakeId'] = subbasin['Hylak_id']
    subbasin['Laketype'] = subbasin['Lake_type']
    subbasin['FloodP_n'] = subbasin['Ch_n']
    # subbasin['LakeArea'] = subbasin['Lake_area']

    crs = lake_sub.crs
    subbasin = gpd.GeoDataFrame(subbasin, geometry=subbasin['geometry'], crs=crs)

    subbasin = subbasin.drop(
        ['NODE_AVAL', 'NODE_AMONT', 'ASSOCI_UHRH', 'index_left', 'Lake_name', 'Country', 'Continent', 'Poly_src',
         'Grand_id', 'Shore_len', 'Shore_dev', 'Vol_src', 'Dis_avg',
         'Res_time', 'Elevation', 'Slope_100', 'Wshd_area', 'Pour_long', 'Pour_lat', 'Hylak_id', 'ident_left',
         'ident_right', 'Lake_area', 'Vol_res', 'Vol_total', 'Lake_type'], axis=1)
    return subbasin
def add_sub_attributes(workspace, subbasin):
    # calculating subbasin properties
    # 1. Slope
    # slope must be between 0 to 60 degree (http://hydrology.uwaterloo.ca/basinmaker/data/resources/attribute_tables_20210429.pdf)
    os.chdir(workspace)
    cmd_slope = 'gdaldem  slope altitude.tif slope.tif -compute_edges'
    os.system(cmd_slope)

    # 2.Aspect
    cmd_aspect = 'gdaldem  aspect altitude.tif aspect.tif -trigonometric -compute_edges'
    os.system(cmd_aspect)

    # loop over the subbasin features and adding the mean elevation, mean aspect and
    ss = os.path.join(workspace, "slope" + "." + "tif")  # The lake shape file created by Physitel
    # pth5 = os.path.join(workspace,"subbasin"+ "." + "shp") # The lake shape file created by Physitel
    # subbasin = gpd.read_file(pth5)

    subbasin = subbasin.join(
        pd.DataFrame(
            zonal_stats(
                vectors=subbasin['geometry'],
                raster=ss,
                stats=['mean']
            )
        ),
        how='left'
    )

    subbasin.loc[subbasin['mean'] < 0, "mean"] = 0

    subbasin['BasSlope'] = subbasin['mean']
    subbasin = subbasin.drop(['mean'], axis=1)

    # aspect
    aa = os.path.join(workspace, "aspect" + "." + "tif")  # The lake shape file created by Physitel

    subbasin = subbasin.join(
        pd.DataFrame(
            zonal_stats(
                vectors=subbasin['geometry'],
                raster=aa,
                stats=['mean']
            )
        ),
        how='left'
    )

    subbasin['BasAspect'] = subbasin['mean']
    subbasin = subbasin.drop(['mean'], axis=1)

    # elevation

    ee = os.path.join(workspace, "altitude" + "." + "tif")  # The lake shape file created by Physitel

    subbasin = subbasin.join(
        pd.DataFrame(
            zonal_stats(
                vectors=subbasin['geometry'],
                raster=ee,
                stats=['mean']
            )
        ),
        how='left'
    )

    subbasin['MeanElev'] = subbasin['mean']
    subbasin = subbasin.drop(['mean'], axis=1)

    # writing the final subbasin map
    # schema = gpd.io.file.infer_schema(subbasin)
    # schema['properties']['BnkfWidth'] = 'float'
    # schema['properties']['Ch_n'] = 'float'
    # schema['properties']['FloodP_n'] = 'float'
    # schema['properties']['HyLakeId'] = 'int'
    # schema['properties']['Laketype'] = 'int'

    os.chdir(workspace)
    # subbasin.to_file('subbasin.shp', schema=schema)
    subbasin.to_file('subbasin.shp')

# def main():




if __name__ == "__main__":
    region_name = 'SLSO_TRONCON'
    troncon_path = '/home/mohammad/Dossier_travail/Hydrotel/DEH/INFO_TRONCON.mat'
    workspace = '/home/mohammad/Dossier_travail/Hydrotel/DEH/HRUs_Quebec_meridional/SLSO/20P/'
    hydroteldir = '/home/mohammad/Dossier_travail/Hydrotel/DEH/MG24HA/SLSO_MG24HA_2020/physitel'
    uhrh_to_sub(region_name, troncon_path, workspace, hydroteldir)
    process_lakes(workspace, hydrolakes_file, troncon_info, uhrh_dissolve)
    # main()
