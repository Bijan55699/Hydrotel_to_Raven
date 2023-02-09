"""
This script creates the subbasin map from a Hydrotel project directory

Inputs:

1- region_name = should be among following list:

1- troncon_path: The path to The INFO_TRONCON.mat (provided by DEH) file which contains the river reaches (troncon) properties of the region.
2- hydroteldir: The hydrotel project directory path
3- hydroteldir: The working directory to create the outputs

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
import warnings
warnings.filterwarnings("ignore")

def uhrh_to_sub(region_name, troncon_path, hydroteldir):
    regions_list = ['ABIT_TRONCON','CNDA_TRONCON','CNDB_TRONCON','CNDC_TRONCON','CNDD_TRONCON','CNDE_TRONCON','GASP_TRONCON','LABI_TRONCON','MONT_TRONCON',
                    'OUTM_TRONCON','OUTV_TRONCON','SAGU_TRONCON','SLNO_TRONCON','SLSO_TRONCON','VAUD_TRONCON']
    if region_name not in regions_list:
        raise ValueError("the %s is not recognized! please make sure the region_name is correct!" %region_name)
    data = sio.loadmat(troncon_path, struct_as_record=False, squeeze_me=True)
    region = data[region_name]
    size = region.shape[0]
    # shutil.copytree(hydroteldir, hydroteldir)
    # os.chdir(hydroteldir)
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
                                             "DowSubId":int}, index=None)
    # special values for non-river (lake) features
    troncon_info['Has_Gauge'] = 0  # Has_Gauge should be always 0 in the shapefile (strange?)
    troncon_info['BkfDepth'] = 0.13 * (troncon_info['SA_Up'] ** 0.4)  # taken from equation 10 of Fossey et. al., 2015
    troncon_info.loc[troncon_info.TYPE_NO == 2, {'Ch_n','BnkfWidth','RivLength','RivSlope','BkfDepth'}] = 0.
    troncon_info['Lake_Cat'] = 0
    troncon_info.loc[troncon_info.TYPE_NO == 2, 'Lake_Cat'] = 1 # for Lakes
    # Assigning the SubId to uhrh geodataframe
    uhrh_fpth = os.path.join(hydroteldir, "uhrh" + "." + "shp")  # The uhrh shape file created by Physitel
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
def process_lakes(uhrh_dissolve,hydroteldir, hydrolakes_file):
    HyLAKES_Canada = gpd.read_file(hydrolakes_file)
    HyLAKES = gpd.clip(HyLAKES_Canada,uhrh_dissolve) # here we mask the Lakes of the region
    Hydrotel_lakes = gpd.read_file(os.path.join(hydroteldir, "lacs" + "." + "shp"))  # The lake shape file in Hydrotel

    join_lakes_attr = sjoin(HyLAKES, Hydrotel_lakes, how="right")

    # Dealing with cases where Hydrotel lake is the merge of two neighbouring lakes in HydroLAKES.
    repeatd_ident = join_lakes_attr[join_lakes_attr.duplicated(subset=['ident'], keep=False)]
    # join_lakes_attr.to_file('join_lakes_attr.shp')
    # uhrh_dissolve.to_file('uhrh_dissolve.shp')


    repeatd_ident.reset_index(level=0, inplace=True)


    aggfn = {'ident': 'first', 'Shape_Area': 'sum', 'Depth_avg': 'mean', 'Vol_total': 'sum', 'Lake_area': 'sum',
             'Lake_type': 'first', 'index': 'first',
             'OBJECTID': 'first', 'Hylak_id': 'first'}
    diss_repeat = repeatd_ident.dissolve(by='index', aggfunc=aggfn)

    diss_repeat['Depth_avg'] = diss_repeat['Vol_total'] / diss_repeat['Lake_area']  # recalculating lake average depth
    diss_repeat['Lake_type'] = int(1)

    join_lakes_attr = join_lakes_attr.drop(diss_repeat.index)
    lake = (pd.concat([join_lakes_attr, diss_repeat])).sort_index()
    lake = lake.drop(['index_left'], axis=1)

    # fill NaN attributes in lake polygon

    lake['Country'].fillna('Canada', inplace=True)
    lake['Continent'].fillna('North America', inplace=True)
    lake['Poly_src'].fillna('Hydrotel', inplace=True)
    lake['Lake_type'].fillna(1, inplace=True)
    lake['Shape_Area'].fillna(lake.area, inplace=True)
    lake['Lake_area'].fillna(lake['Shape_Area'] / 1000000, inplace=True)
    lake['Hylak_id'].fillna(100, inplace=True)

    # Regional relationship for lake's volume-area for Quebec: ref: https://agupubs.onlinelibrary.wiley.com/doi/full/10.1002/2016GL071378.
    lake['Vol_total'].fillna(
        1 / 1000000 * (np.power(10, 1.165 * np.log10(lake['Shape_Area']) + np.log10(0.758))),
        inplace=True)  # volume is in MCM and area is in m

    lake['Hylak_id'] = lake['Hylak_id'].astype(int)
    lake['Lake_type'] = lake['Lake_type'].astype(int)
    lake['Depth_avg'].fillna(lake['Vol_total'] / lake['Lake_area'], inplace=True)
    # lake['index'] = lake['index'].astype(int)

    # os.chdir(hydroteldir)
    # lake.to_file('lake.shp')

    # Intersecting with uhrh_dissolve to find the SubId of each lake
    lake_final = sjoin(lake, uhrh_dissolve, how='right', op='within')

    lake_final['LakeArea'] = lake_final['Lake_area'] * 1000000.  # To convert the area in Km2 in HydroLAKES database to m2
    lake_final['LakeVol'] = lake_final['Vol_total'] / 1000.  # To convert the volume in MCM in HydroLAKES database to km3
    lake_final['LakeDepth'] = lake_final['Depth_avg']
    os.chdir(hydroteldir)
    lake_final.to_file('lake_final.shp')
    return lake_final

def create_subbasin(troncon_info,lake_final):
    subbasin = pd.merge(troncon_info, lake_final, on='SubId')
    # Lake data from HydroLAKES database
    subbasin['HyLakeId'] = subbasin['Hylak_id']
    subbasin['Laketype'] = subbasin['Lake_type']
    subbasin['FloodP_n'] = subbasin['Ch_n']
    # subbasin['LakeArea'] = subbasin['Lake_area']

    crs = lake_final.crs
    subbasin = gpd.GeoDataFrame(subbasin, geometry=subbasin['geometry'], crs=crs)

    subbasin = subbasin.drop(
        ['NODE_AVAL', 'NODE_AMONT', 'ASSOCI_UHRH', 'index_left', 'Lake_name', 'Country', 'Continent', 'Poly_src',
         'Grand_id', 'Shore_len', 'Shore_dev', 'Vol_src', 'Dis_avg',
         'Res_time', 'Elevation', 'Slope_100', 'Wshd_area', 'Pour_long', 'Pour_lat', 'Hylak_id', 'ident_left',
         'ident_right', 'Lake_area', 'Vol_res', 'Vol_total', 'Lake_type'], axis=1)
    return subbasin
def add_sub_attributes(hydroteldir, subbasin):
    # calculating subbasin-scale properties
    # 1. Slope
    # slope must be between 0 to 60 degree (http://hydrology.uwaterloo.ca/basinmaker/data/resources/attribute_tables_20210429.pdf)
    os.chdir(hydroteldir)
    cmd_slope = 'gdaldem  slope altitude.tif slope.tif -compute_edges'
    os.system(cmd_slope)

    # 2.Aspect
    cmd_aspect = 'gdaldem  aspect altitude.tif aspect.tif -trigonometric -compute_edges'
    os.system(cmd_aspect)

    # loop over the subbasin features and adding the mean elevation, mean aspect and
    ss = os.path.join(hydroteldir, "slope" + "." + "tif")  # The lake shape file created by Physitel
    # pth5 = os.path.join(hydroteldir,"subbasin"+ "." + "shp") # The lake shape file created by Physitel
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
    aa = os.path.join(hydroteldir, "aspect" + "." + "tif")  # The lake shape file created by Physitel

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

    ee = os.path.join(hydroteldir, "altitude" + "." + "tif")  # The lake shape file created by Physitel

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

    subbasin['BnkfWidth'] = subbasin['BnkfWidth'].astype(float)
    subbasin['Ch_n'] = subbasin['Ch_n'].astype(float)
    subbasin['FloodP_n'] = subbasin['FloodP_n'].astype(float)
    subbasin['HyLakeId'] = subbasin['HyLakeId'].astype(int)
    subbasin['Laketype'] = subbasin['Laketype'].astype(int)

    subbasin.to_file('subbasin.shp')

def main():
    region_name = 'SLSO_TRONCON'
    troncon_path = '/home/mohammad/Dossier_travail/Hydrotel/DEH/INFO_TRONCON_test.mat'
    hydrolakes_file = '/home/mohammad/Dossier_travail/Hydrotel/HydroLAKES_polys_v10_shp/HydroLAKES_polys_v10_Canada2.shp'
    hydroteldir = '/home/mohammad/Dossier_travail/Hydrotel/DEH/MG24HA/SLSO_MG24HA_2020/physitel'
    # methods
    [troncon_info, uhrh_dissolve] = uhrh_to_sub(region_name, troncon_path, hydroteldir)
    lake_final = process_lakes(uhrh_dissolve,hydroteldir, hydrolakes_file)
    subbasin   = create_subbasin(troncon_info, lake_final)
    add_sub_attributes(hydroteldir, subbasin)

if __name__ == "__main__":
    main()
