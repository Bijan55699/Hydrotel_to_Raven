import arcpy,os,re
from arcpy.sa import *
from arcpy import env
import pandas as pd
import scipy.io as sio
import numpy as np
import scipy as spio
import numpy as np
import shutil

Troncon_path = r'C:\Users\mohbiz1\Desktop\Dossier_travail\Hydrotel\DEH\INFO_TRONCON.mat'
data = sio.loadmat(Troncon_path, struct_as_record=False, squeeze_me=True)
#data= sio.loadmat((Troncon_path))
region_name = data['SLNO_TRONCON']
size = region_name.shape[0]
s = size-1

df = []
for i in range(size):
    rec = region_name[i]
    df.append([rec.NOEUD_AVAL.NUMERO,rec.NOEUD_AMONT.NUMERO,rec.NO_TRONCON,rec.TYPE_NO,rec.LONGUEUR,rec.LARGEUR,rec.UHRH_ASSOCIES,rec.C_MANNING,rec.PENTE_MOYENNE])
TRONCON_INFO= pd.DataFrame(df,columns = ['NODE_AVAL','NODE_AMONT','NO_TRONCON','TYPE_NO','Length','Width','ASSOCI_UHRH','n_Manning','slope'])

pathtoDirectory = r"C:\Users\mohbiz1\Desktop\Dossier_travail\Hydrotel\DEH\MG24HA\SLNO_MG24HA_2020\physitel"
workspace = os.path.join(pathtoDirectory+ "\HRU")

shutil.copytree(pathtoDirectory,workspace)

# step 0: set environment workspace for arcpy
arcpy.env.overwriteOutput = True
env.workspace = r"C:\Users\mohbiz1\Desktop\Dossier_travail\Hydrotel\DEH\MG24HA\SLNO_MG24HA_2020\physitel\HRU"
workspace = arcpy.env.workspace

# step1: add troncon id and other attributes to associated UHRHs
arcpy.AddField_management("uhrh.shp", "Troncon_id", "LONG", "", "", 16)
#arcpy.AddField_management("uhrh.shp", "Node_amont", "LONG", "", "", 16)
#arcpy.AddField_management("uhrh.shp", "Node_aval", "LONG", "", "", 16)
arcpy.AddField_management("uhrh.shp", "Type", "LONG", "", "", 16)
arcpy.AddField_management("uhrh.shp", "Length_km", "FLOAT", "", "", 16)
arcpy.AddField_management("uhrh.shp", "MANNINGS_N", "FLOAT", "", "", 16)
arcpy.AddField_management("uhrh.shp", "SLOPE", "FLOAT", "", "", 16)

TRONCON_INFO.loc[TRONCON_INFO.TYPE_NO == 2, 'n_Manning'] = 0.


for i in range(size):
    a = TRONCON_INFO['ASSOCI_UHRH'][i]
    id = TRONCON_INFO['NO_TRONCON'][i]
    tr_type = TRONCON_INFO['TYPE_NO'][i]
    tr_length = TRONCON_INFO['Length'][i]
    n_manning = TRONCON_INFO['n_Manning'][i]
    slope = TRONCON_INFO['slope'][i]
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
        with arcpy.da.UpdateCursor("uhrh.shp", ['SHAPE@', 'Troncon_id','ident','Type','Length_km','MANNINGS_N','SLOPE']) as rows:
            for row in rows:
                if row[2] in dict.values():
                    row[1] = id
                    row[3] = tr_type
                    row[4] = tr_length/1000.0
                    row[5] = n_manning
                    row[6] = slope
                rows.updateRow(row)

# step2: merge the uhrhs based on Troncon_id field. the number of feature classes in the resulting file shoudl be same sa number of Troncons?

arcpy.MakeFeatureLayer_management("uhrh.shp","templayer") #create a temporary feature layer
arcpy.Dissolve_management("templayer","uhrh_diss.shp","Troncon_id","","","")
arcpy.AddGeometryAttributes_management("uhrh_diss.shp", "AREA", "METERS", "SQUARE_KILOMETERS") # area of subbasin in km2

# step3: finding the downstream subwatershed ID associated with each uhrh
#arcpy.AddField_management("uhrh_diss.shp", "Dowstr_ID", "LONG", "", "", 16)

TRONCON_INFO['Downstream_ID']=-1
for i in range(size):
    naval = TRONCON_INFO['NODE_AVAL'][i]
    for j in range(size):
        namont= TRONCON_INFO['NODE_AMONT'][j]
        id = TRONCON_INFO['NO_TRONCON'][j]
        if type(namont) is int:
            nal = [namont]
        else:
            nal = namont.tolist()
        if naval in nal: # if naval (downstream node) for reach i is upstream node for reach j, then reach j is downstream reach i
            TRONCON_INFO.loc[i, 'Downstream_ID'] = id

#TRONCON_INFO['name'] = 'none'
TRONCON_INFO['Gauged'] = (TRONCON_INFO['Downstream_ID'] == -1).astype(int)  #create a boolean indicator to set 1 for gauged subwatershed and 0 for others

# step4: add the downstream ID to the shapefile of the created subbasin shapefile (uhrh_diss.shp)
arcpy.AddField_management("uhrh_diss.shp", "NAME", "SHORT", "", "", 16)
arcpy.AddField_management("uhrh_diss.shp", "Dowstr_ID", "LONG", "", "", 16)
arcpy.AddField_management("uhrh_diss.shp", "PROFILE", "LONG", "", "", 16)
arcpy.AddField_management("uhrh_diss.shp", "Length_km", "FLOAT", "", "", 16)
arcpy.AddField_management("uhrh_diss.shp", "GAUGED", "SHORT", "", "", 16)
arcpy.AddField_management("uhrh_diss.shp", "Type", "SHORT", "", "", 16) # NOT NEEDED for Raven. 1 = river and 2 = lake

j = 0
with arcpy.da.UpdateCursor("uhrh_diss.shp", ("Type", "Length_km", "Dowstr_ID","NAME","GAUGED","PROFILE")) as cursor:
     for ROW in cursor:
          ROW[0] = TRONCON_INFO["TYPE_NO"][j]
          ROW[1] = TRONCON_INFO["Length"][j]/1000.0
          ROW[2] = TRONCON_INFO["Downstream_ID"][j]
          ROW[3] = TRONCON_INFO["NO_TRONCON"][j]
          ROW[4] = TRONCON_INFO["Gauged"][j]
          ROW[5] = TRONCON_INFO["NO_TRONCON"][j]
          cursor.updateRow(ROW)
          j += 1

del cursor