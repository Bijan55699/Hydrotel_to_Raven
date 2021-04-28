import arcpy,os,re
from arcpy.sa import *
from arcpy import env
import pandas as pd

arcpy.env.overwriteOutput = True
workspace = r"C:\Users\mohbiz1\Desktop\Dossier_travail\Hydrotel\DEH\MG24HA\SLSO_MG24HA_2020\physitel\HRU"
arcpy.env.workspace = workspace
subwatershed = os.path.join(workspace,"uhrh_diss"+"."+"shp") #subwatershed map created by Hydrotel_Raven code
lu_raster = os.path.join(workspace,"occupation_sol"+"."+"tif") #Lu map in raster
soil_raster = os.path.join(workspace,"type_sol"+"."+"tif") #soil type map in raster
#subwatershed_raster = os.path.join(workspace,"subwatershed_ras"+"."+"tif") #subwatershed map created by Hydrotel_Raven code
#subwatershed2 = os.path.join(workspace,"uhrh_diss2"+"."+"shp") #subwatershed map created by Hydrotel_Raven code
arcpy.env.scratchWorkspace = workspace

###########################################################################
#const = 100.0
#arcpy.Times_3d("slope_in_deg.tif","100.0","times.tif")
#intslope= Int("times.tif")
#





#cellsize = arcpy.GetRasterProperties_management(lu_raster,"CELLSIZEX")  #Extracting the raster cell size
#cellsize1 = int(cellsize.getOutput(0))
# ##########################################################################
# arcpy.FeatureToRaster_conversion(subwatershed, "Troncon_id", subwatershed_raster, lu_raster)
# arcpy.RasterToPolygon_conversion(subwatershed_raster,subwatershed2, "NO_SIMPLIFY", "VALUE")
# subwatershed3 = os.path.join(workspace,"uhrh_diss3"+"."+"shp") #subwatershed map created by Hydrotel_Raven code
# arcpy.Dissolve_management(subwatershed2,subwatershed3,"gridcode","","","")
#
# arcpy.JoinField_management(subwatershed3,"gridcode",subwatershed,"Troncon_id")
# arcpy.DeleteField_management(subwatershed3, ["Troncon__2","Troncon__1","gridcode"])

##########################################################################
# Converting LU and soil rasters to polygon for further processing
lu = os.path.join(workspace,"lu"+ "." + "shp") #feature class of land use map
soil = os.path.join(workspace,"soil"+ "." + "shp") #feature class of soil type map
arcpy.RasterToPolygon_conversion(lu_raster,lu, "NO_SIMPLIFY", "VALUE")
arcpy.RasterToPolygon_conversion(soil_raster,soil,"NO_SIMPLIFY","VALUE")

arcpy.AddField_management(soil, "soil_type","SHORT", "","","","","","","")
arcpy.AddField_management(lu, "LU_type","SHORT", "","","","","","","")

arcpy.CalculateField_management(soil, "soil_type","!gridcode!", "PYTHON_9.3")
arcpy.DeleteField_management(soil, "gridcode")
arcpy.CalculateField_management(lu, "LU_type","!gridcode!", "PYTHON_9.3")
arcpy.DeleteField_management(lu, "gridcode")

# overlain the soil type, land use, for creating the HRU map
HRU1 = os.path.join(workspace,"HRU1"+ "." + "shp") #feature class of soil type map
arcpy.Intersect_analysis([soil, lu],"HRU1","ALL")

# Update with lake map: A lake is a unique HRU
lakes = os.path.join(workspace,"lacs"+"."+"shp") #subwatershed map created by Hydrotel_Raven code
HRU2 = os.path.join(workspace,"HRU2"+ "." + "shp") #feature class of soil type map
os.system("saga_cmd shapes_polygons 18 -A " + HRU1 + " -B " + lakes + " -RESULT " + HRU2)


arcpy.CheckOutExtension("Spatial")  #activating spetial analyst module
arcpy.AddField_management(subwatershed, "LakeID","LONG", "","","","","","","")
arcpy.CalculateField_management(subwatershed, "LakeID","!HyLakeId!", "PYTHON_9.3")

# Major LU class in lake features
outzstable_lake = os.path.join(workspace,"outzstable_lake"+"."+"dbf") #
outZonalStats_lake = ZonalStatisticsAsTable(subwatershed, "LakeID", lu_raster, outzstable_lake,"DATA","MAJORITY")

# Major Soil class in lake features
outzstable_lake_soil = os.path.join(workspace,"outzstable_lake_soil"+"."+"dbf") #
outZonalStats_lake_soil = ZonalStatisticsAsTable(subwatershed, "LakeID", soil_raster, outzstable_lake_soil,"DATA","MAJORITY")

# join the tables to the subwatershed's attribute table

arcpy.JoinField_management(subwatershed,"LakeID",outzstable_lake,"LakeID")
arcpy.JoinField_management(subwatershed,"LakeID",outzstable_lake_soil,"LakeID")




#sr=arcpy.Describe(lu).spatialReference
#
# arcpy.AddField_management(subwatershed2, "Troncon_id", "LONG", "", "", 16)
# arcpy.CalculateField_management(subwatershed2, "Troncon_id", "!gridcode!", "PYTHON_9.3")
# arcpy.DeleteField_management("soil_poly.shp", "gridcode")
##########################################################################
# Use Identity to cut the features with subwatershed boundaries
HRU_identity = os.path.join(workspace,"HRU_identity"+ "." + "shp") #subwatershed map created by Hydrotel_Raven code
os.system("saga_cmd shapes_polygons 19 -A " + HRU2 + " -B " + subwatershed + " -RESULT " + HRU_identity)




# add major lu class and soil type of the lake features to the HRU_identity attribute table
out_xls = os.path.join(workspace,"lake_lu_dbf"+ "." + "xls") #
arcpy.TableToExcel_conversion(outzstable_lake, out_xls)
df_lu = pd.read_excel(out_xls)

#out_xls_soil = os.path.join(workspace,"lake_soil_dbf"+ "." + "xls") #
#arcpy.TableToExcel_conversion(outzstable_lake_soil, out_xls_soil)
#df_soil = pd.read_excel(out_xls_soil)
arcpy.MakeFeatureLayer_management(HRU_identity, 'HRU_identity_lyr')

size = len(df_lu.index)
for i in range(1,size,1):
    lake_numner = i
    name = "lake_%i.shp" % lake_numner
    where = ' "LakeID" = %i ' % (lake_numner)
    arcpy.SelectLayerByAttribute_management("HRU_identity_lyr", "NEW_SELECTION", where)  #
    if arcpy.Describe("HRU_identity_lyr").FIDSet:
        with arcpy.da.UpdateCursor("HRU_identity_lyr", ["soil_type","LU_type","MAJORITY","MAJORITY_1"]) as cursor:
            for row in cursor:
                row[0] = row[3]
                row[1] = row[2]
                cursor.updateRow(row)
        del cursor
    arcpy.SelectLayerByAttribute_management('HRU_identity_lyr', "CLEAR_SELECTION")

HRU_identity2 = os.path.join(workspace,"HRU_identity2"+ "." + "shp")
arcpy.CopyFeatures_management("HRU_identity_lyr", HRU_identity2)

arcpy.DeleteField_management(HRU_identity2, ["LakeID","LakeID_1","COUNT","AREA","MAJORITY","LakeID_12","COUNT_1","AREA_1","MAJORITY_1"])
arcpy.DeleteField_management(subwatershed, ["LakeID","LakeID_1","COUNT","AREA","MAJORITY","LakeID_12","COUNT_1","AREA_1","MAJORITY_1"])
###########################################################################
arcpy.CheckOutExtension("Spatial")  #activating spetial analyst module

arcpy.AddField_management(HRU_identity2, "LUID", "SHORT", "", "", 16)
arcpy.CalculateField_management(HRU_identity2, "LUID","!LU_type!", "PYTHON_9.3")

# run Tabulate area to determine the surface area of each LU class in subwatershed
outareatable = os.path.join(workspace,"outareatable"+"."+"dbf") #
TabulateArea(subwatershed,"SubId",HRU_identity2,"LUID",outareatable,lu_raster)

# run zonal statistics tool to determine the dominant landuse class in each subwatershed
outzstable = os.path.join(workspace,"outzstable"+"."+"dbf") #
outZonalStats = ZonalStatisticsAsTable(subwatershed, "SubId", lu_raster, outzstable,"DATA","MAJORITY")
#outZonalStats.save(outzstable)

# Join the two tables to the subwatershed's attribute table
arcpy.JoinField_management(subwatershed,"SubId",outareatable,"SubId")
arcpy.JoinField_management(subwatershed,"SubId",outzstable,"SubId")
# delete redundant fields in subwatershed feature class
arcpy.DeleteField_management(subwatershed, ["SubId_12","SUBID_1"])

# add subwatershed area (in m2) to the attribute table
#arcpy.AddGeometryAttributes_management(subwatershed, "AREA", "METERS", "SQUARE_METERS")  # area in m2
############################################################################
#remove slivers generated in the identity process
where = ' "SubId" =0 '
arcpy.MakeFeatureLayer_management(HRU_identity2, 'HRU_identity_lyr2')
arcpy.SelectLayerByAttribute_management("HRU_identity_lyr2", "NEW_SELECTION",where)  # select the subwaterwshed=i in LU map

if arcpy.Describe("HRU_identity_lyr2").FIDSet:
     arcpy.DeleteFeatures_management("HRU_identity_lyr2")

arcpy.SelectLayerByAttribute_management('HRU_identity_lyr2', "CLEAR_SELECTION")
HRU_identity3 = os.path.join(workspace,"HRU_identity3"+ "." + "shp") #subwatershed map created by Hydrotel_Raven code
arcpy.CopyFeatures_management("HRU_identity_lyr2", HRU_identity3)
############################################################################

#run spatial join between subwatershed map and new LU map to find the subwatershed in whcih the HRU is located

fms = arcpy.FieldMappings()
# loading all field objects from joinFC into the <FieldMappings object>
fms.addTable(subwatershed)

fields_sequence = ['DownSubId','Rivlen','BkfWidth','BkfDepth','IsObs','RivSlope','Ch_n','FloodP_n','IsLake','SubId','LUID_1','LUID_2','LUID_3','LUID_4','LUID_5','LUID_6','LUID_7','LUID_8','LUID_9','COUNT','AREA','MAJORITY']
# remove fieldmaps for those fields that are not needed in the output joined fc
fields_to_delete = [f.name for f in fms.fields if f.name not in fields_sequence]
for field in fields_to_delete:
    fms.removeFieldMap(fms.findFieldMapIndex(field))
    fms_out = arcpy.FieldMappings()
    fms_out.addTable(HRU_identity3)

# we need to add Troncon_ID to fieldmapping
for field in fields_sequence:
    mapping_index = fms.findFieldMapIndex(field)
    field_map = fms.fieldMappings[mapping_index]
    fms_out.addFieldMap(field_map)


LU_HRU_agg = os.path.join(workspace,"LU_HRU_agg"+ "." + "shp")

arcpy.SpatialJoin_analysis(target_features=HRU_identity3, join_features=subwatershed,
                               out_feature_class=LU_HRU_agg,
                               join_operation='JOIN_ONE_TO_ONE', join_type='KEEP_ALL',
                               field_mapping=fms_out, match_option='WITHIN',
                               search_radius=None, distance_field_name=None)

where = ' "SubId" =0 '
arcpy.MakeFeatureLayer_management(LU_HRU_agg, 'LU_HRU_agg_ly')
arcpy.SelectLayerByAttribute_management("LU_HRU_agg_ly", "NEW_SELECTION",where)  # select the subwaterwshed=i in LU map
#
if arcpy.Describe("LU_HRU_agg_ly").FIDSet:
     arcpy.DeleteFeatures_management("LU_HRU_agg_ly")

arcpy.SelectLayerByAttribute_management('LU_HRU_agg_ly', "CLEAR_SELECTION")

LU_HRU_agg2 = os.path.join(workspace,"LU_HRU_agg2"+ "." + "shp") #subwatershed map created by Hydrotel_Raven code
arcpy.CopyFeatures_management("LU_HRU_agg_ly", LU_HRU_agg2)

arcpy.DeleteField_management(LU_HRU_agg2, ["DownSubI_1","Rivlen_1","BkfWidth_1","BkfDepth_1","IsObs_1","RivSlope_1","Ch_n_1","FloodP_n_1","IsLake_1","SubId_1"])
################################################################################################
# Defining the threshold and creating the simplified HRU map
Threshold = 5
result = arcpy.GetCount_management(subwatershed)
subwsh_count = int(result.getOutput(0))
arcpy.MakeFeatureLayer_management(LU_HRU_agg2, 'LU_HRU_agg2_lyr')
count = subwsh_count -1
LU_agg_threshold = os.path.join(workspace, "lu_agg_hreshold" + "." + "shp") #subwatershed map created by Hydrotel_Raven code
#arcpy.CreateFeatureclass_management(workspace, 'lu_agg_final', "POLYGON", "", "DISABLED", "DISABLED",sr)
mergelist = []
for i in range(subwsh_count):
    subwsh_number = i + 1
    name = "merge_subwsh_%i.shp" %subwsh_number
    where = ' "SubId" = %i ' % subwsh_number
    arcpy.SelectLayerByAttribute_management("LU_HRU_agg2_lyr", "NEW_SELECTION", where)  # select the subwaterwshed=i in LU map
    if arcpy.Describe("LU_HRU_agg2_lyr").FIDSet:
        with arcpy.da.UpdateCursor("LU_HRU_agg2_lyr", ["LUID_2","LUID_3","LUID_4","LUID_5","LUID_6","LUID_7","LUID_8","LUID_9","LUID","POLY_AREA","MAJORITY"]) as cursor:
            for row in cursor:
                lu_major = row[10]
                perc_lu2 = (row[0] / row[9]) * 100
                perc_lu3 = (row[1] / row[9]) * 100
                perc_lu4 = (row[2] / row[9]) * 100
                perc_lu5 = (row[3] / row[9]) * 100
                perc_lu6 = (row[4] / row[9]) * 100
                perc_lu7 = (row[5] / row[9]) * 100
                perc_lu8 = (row[6] / row[9]) * 100
                perc_lu9 = (row[7] / row[9]) * 100
                if (row[8]==2):
                    if (perc_lu2<=Threshold and perc_lu2>0):
                        row[8] = lu_major
                elif (row[8]==3):
                    if (perc_lu3<=Threshold and perc_lu3>0):
                        row[8] = lu_major
                elif (row[8]==4):
                    if (perc_lu4<=Threshold and perc_lu4>0):
                        row[8] = lu_major
                elif (row[8]==5):
                    if (perc_lu5<=Threshold and perc_lu5>0):
                        row[8] = lu_major
                elif (row[8]==6):
                    if (perc_lu6<=Threshold and perc_lu6>0):
                        row[8] = lu_major
                elif(row[8]==7):
                    if (perc_lu7<=Threshold and perc_lu7>0):
                        row[8] = lu_major
                elif(row[8]==8):
                    if (perc_lu8<=Threshold and perc_lu8>0):
                        row[8] = lu_major
                elif(row[8]==9):
                    if (perc_lu9<=Threshold and perc_lu9>0):
                        row[8] = lu_major
                cursor.updateRow(row)
        arcpy.Dissolve_management('LU_HRU_agg2_lyr', name, "LUID", "", "MULTI_PART", "")
        mergelist.append(name)

#arcpy.SelectLayerByAttribute_management('LU_HRU_agg4_lyr', "CLEAR_SELECTION")

arcpy.Merge_management(mergelist, LU_agg_threshold)
for fc in mergelist:
    if arcpy.Exists(fc):
        arcpy.Delete_management(fc)

HRUF = os.path.join(workspace,"HRUF"+ "." + "shp") #feature class of soil type map
arcpy.Intersect_analysis([soil, LU_agg_threshold],"HRUF","ALL")



# add latitude,longitude, HRU ID, Slope, aspect, and Elevation to the HRU feature class

# Numbering the HRU feature class
arcpy.AddField_management(HRUF, "HRU_ID", "LONG", "", "", 16)
HRU_ID = 1
with arcpy.da.UpdateCursor(HRUF, "HRU_ID") as cursor:
    for row in cursor:
        row[0] = HRU_ID
        HRU_ID = HRU_ID + 1
        cursor.updateRow(row)
# add surface area to identify features with null surface area (slivers) and remove
arcpy.AddGeometryAttributes_management(HRUF, "AREA", "METERS", "SQUARE_METERS")  # area in m2
where = ' "POLY_AREA" <=0.1 '
arcpy.MakeFeatureLayer_management(HRUF, 'HRUF_lyr')
arcpy.SelectLayerByAttribute_management("HRUF_lyr", "NEW_SELECTION",where)  # select the subwaterwshed=i in LU map

if arcpy.Describe("HRUF_lyr").FIDSet:
     arcpy.DeleteFeatures_management("HRUF_lyr")

arcpy.SelectLayerByAttribute_management('HRUF_lyr', "CLEAR_SELECTION")
HRUF2 = os.path.join(workspace,"HRUF2"+ "." + "shp") #subwatershed map created by Hydrotel_Raven code
arcpy.CopyFeatures_management("HRUF_lyr", HRUF2)

# delete not needed files
arcpy.Delete_management(LU_agg_threshold)

# add mean elevation of each HRU to the attribute table
elev_point = os.path.join(workspace, "elev_point.shp")
arcpy.RasterToPoint_conversion("altitude.tif",elev_point, "Value")

arcpy.CreateFileGDB_management(workspace, "output.gdb")
workspace2 = os.path.join(workspace+ "\output.gdb")
HRUF3 = os.path.join(workspace2,"HRUF3")
arcpy.CopyFeatures_management(HRUF2, HRUF3)
arcpy.env.workspace = workspace2

arcpy.SplitByAttributes_analysis(HRUF3, workspace2, ['LUID'])
fci = ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9"]  # these are splitted shapefiles
fco = ["T1_sj", "T2_sj", "T3_sj", "T4_sj", "T5_sj", "T6_sj", "T7_sj","T8_sj", "T9_sj"]  # these are splitted shapefiles
for i in range(len(fci)):
    fnp = os.path.join(workspace2, fci[i])  # the input shapefile
    fieldmappings = arcpy.FieldMappings()
    # fieldmappings.addInputField("HRU.shp","Mean_elev")
    fieldmappings.addTable(fnp)  # add attribute table of HRU feature class to the fieldmap
    fieldmappings.addTable(elev_point)  # add attribute table of elev_point feature class to the fieldmap

    elevpntFieldIndex = fieldmappings.findFieldMapIndex("grid_code")
    fieldmap = fieldmappings.getFieldMap(elevpntFieldIndex)

    # Get the output field's properties as a field object
    field = fieldmap.outputField

    # Rename the field and pass the updated field object back into the field map
    field.name = "HRU_E_mean"
    field.aliasName = "HRU_E_mean"
    fieldmap.outputField = field

    # Set the merge rule to mean and then replace the old fieldmap in the mappings object
    # with the updated one
    fieldmap.mergeRule = "mean"
    fieldmappings.replaceFieldMap(elevpntFieldIndex, fieldmap)

    # Run the Spatial Join tool, using the defaults for the join operation and join type
    #      HRU6 = os.path.join(path, "output.gdb", "HRU6")
    #  HRU6 = os.path.join(path, "HRU6" + "." + "shp")

    arcpy.SpatialJoin_analysis(fci[i], elev_point, fco[i], "#", "#", fieldmappings)

#arcpy.CreateFileGDB_management(workspace, "output.gdb")
#HRUF3 = os.path.join(workspace,"output.gdb","HRUF3")

HRUF4 = os.path.join(workspace2,"HRUF4")
arcpy.Merge_management(fco, HRUF4)

arcpy.DeleteField_management(HRUF3, ["ident", "Join_Count", "TARGET_FID"])
arcpy.Delete_management(fci[0])
arcpy.Delete_management(fci[1])
arcpy.Delete_management(fci[2])
arcpy.Delete_management(fci[3])
arcpy.Delete_management(fci[4])
arcpy.Delete_management(fci[5])
arcpy.Delete_management(fci[6])
arcpy.Delete_management(fci[7])
arcpy.Delete_management(fci[8])
#arcpy.Delete_management(fci[9])

arcpy.Delete_management(fco[0])
arcpy.Delete_management(fco[1])
arcpy.Delete_management(fco[2])
arcpy.Delete_management(fco[3])
arcpy.Delete_management(fco[4])
arcpy.Delete_management(fco[5])
arcpy.Delete_management(fco[6])
arcpy.Delete_management(fco[7])
arcpy.Delete_management(fco[8])
#arcpy.Delete_management(fco[9])




# add longitude, latitude fields
arcpy.AddField_management(HRUF4, "HRU_CenY", "DOUBLE", "", "", 16)
arcpy.AddField_management(HRUF4, "HRU_CenX", "DOUBLE", "", "", 16)

# gcs = arcpy.Describe("HRU.shp").spatialReference  # HRU.shp is a projected coordinate system. for latitude, longitude we need geographic coordinate system.
sr = arcpy.SpatialReference(4269)  # EPSG code of NAD83=4269

with arcpy.da.UpdateCursor(HRUF4, ['SHAPE@', 'HRU_CenY', 'HRU_CenX']) as rows:
    for row in rows:
        pnt_sr = row[0].projectAs(sr)
        row[1:] = [pnt_sr.centroid.Y, pnt_sr.centroid.X]  # will be in decimal degrees
        rows.updateRow(row)
del rows

# adding mean slope of HRUs
arcpy.CheckOutExtension("Spatial")  #activating spetial analyst module
altitude = os.path.join(workspace,"altitude"+ "." + "tif")
slope1 = Slope(altitude,'DEGREE')  # SLOPE IN DEGREE
slope_shapefile = os.path.join(workspace2,"slope_shapefile")
arcpy.RasterToPoint_conversion(slope1,slope_shapefile, "Value")
arcpy.env.workspace = workspace2
arcpy.SplitByAttributes_analysis(HRUF4, workspace2, ['LUID'])
fci = ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9"]  # these are splitted shapefiles
fco = ["T1_sj", "T2_sj", "T3_sj", "T4_sj", "T5_sj", "T6_sj", "T7_sj","T8_sj", "T9_sj"]  # these are splitted shapefiles
for i in range(len(fci)):
    fnp = os.path.join(workspace2, fci[i])  # the input shapefile
    fieldmappings = arcpy.FieldMappings()
    # fieldmappings.addInputField("HRU.shp","Mean_elev")
    fieldmappings.addTable(fnp)  # add attribute table of HRU feature class to the fieldmap
    fieldmappings.addTable(slope_shapefile)  # add attribute table of elev_point feature class to the fieldmap

    slppntFieldIndex = fieldmappings.findFieldMapIndex("grid_code")
    fieldmap = fieldmappings.getFieldMap(slppntFieldIndex)

    # Get the output field's properties as a field object
    field = fieldmap.outputField

    # Rename the field and pass the updated field object back into the field map
    field.name = "HRU_S_mean"
    field.aliasName = "HRU_S_mean"
    fieldmap.outputField = field

    # Set the merge rule to mean and then replace the old fieldmap in the mappings object
    # with the updated one
    fieldmap.mergeRule = "mean"
    fieldmappings.replaceFieldMap(slppntFieldIndex, fieldmap)

    # Run the Spatial Join tool, using the defaults for the join operation and join type
    #      HRU6 = os.path.join(path, "output.gdb", "HRU6")
    #  HRU6 = os.path.join(path, "HRU6" + "." + "shp")

    arcpy.SpatialJoin_analysis(fci[i], slope_shapefile, fco[i], "#", "#", fieldmappings)
HRUF5 = os.path.join(workspace2,"HRUF5")
arcpy.Merge_management(fco, HRUF5)

arcpy.Delete_management(fci[0])
arcpy.Delete_management(fci[1])
arcpy.Delete_management(fci[2])
arcpy.Delete_management(fci[3])
arcpy.Delete_management(fci[4])
arcpy.Delete_management(fci[5])
arcpy.Delete_management(fci[6])
arcpy.Delete_management(fci[7])
arcpy.Delete_management(fci[8])
#arcpy.Delete_management(fci[9])

arcpy.Delete_management(fco[0])
arcpy.Delete_management(fco[1])
arcpy.Delete_management(fco[2])
arcpy.Delete_management(fco[3])
arcpy.Delete_management(fco[4])
arcpy.Delete_management(fco[5])
arcpy.Delete_management(fco[6])
arcpy.Delete_management(fco[7])
arcpy.Delete_management(fco[8])

# adding mean Aspect of HRUs
arcpy.CheckOutExtension("Spatial")  #activating spetial analyst module
arcpy.env.workspace= workspace
aspect1 = Aspect("altitude.tif")  # ATTENTION: Aspect in Arcgis is calculated clockwise so East is 90. in Raven's manual Aspect is assumed to be counterclockwise i.e., west 90
aspect1.save("aspect")
aspect_shapefile = os.path.join(workspace2,"aspect_shapefile")
arcpy.RasterToPoint_conversion(aspect1,aspect_shapefile, "Value")

arcpy.env.workspace= workspace2
arcpy.SplitByAttributes_analysis(HRUF5, workspace2, ['LUID'])
fci = ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9"]  # these are splitted shapefiles
fco = ["T1_sj", "T2_sj", "T3_sj", "T4_sj", "T5_sj", "T6_sj", "T7_sj","T8_sj", "T9_sj"]  # these are splitted shapefiles
for i in range(len(fci)):
    fnp = os.path.join(workspace2, fci[i])  # the input shapefile
    fieldmappings = arcpy.FieldMappings()
    # fieldmappings.addInputField("HRU.shp","Mean_elev")
    fieldmappings.addTable(fnp)  # add attribute table of HRU feature class to the fieldmap
    fieldmappings.addTable(aspect_shapefile)  # add attribute table of elev_point feature class to the fieldmap

    slppntFieldIndex = fieldmappings.findFieldMapIndex("grid_code")
    fieldmap = fieldmappings.getFieldMap(slppntFieldIndex)

    # Get the output field's properties as a field object
    field = fieldmap.outputField

    # Rename the field and pass the updated field object back into the field map
    field.name = "HRU_A_mean"
    field.aliasName = "HRU_A_mean"
    fieldmap.outputField = field

    # Set the merge rule to mean and then replace the old fieldmap in the mappings object
    # with the updated one
    fieldmap.mergeRule = "mean"
    fieldmappings.replaceFieldMap(slppntFieldIndex, fieldmap)

    # Run the Spatial Join tool, using the defaults for the join operation and join type
    #      HRU6 = os.path.join(path, "output.gdb", "HRU6")
    #  HRU6 = os.path.join(path, "HRU6" + "." + "shp")

    arcpy.SpatialJoin_analysis(fci[i], aspect_shapefile, fco[i], "#", "#", fieldmappings)


HRUF6 = os.path.join(workspace2,"HRUF6")
arcpy.Merge_management(fco, HRUF6)

arcpy.Delete_management(fci[0])
arcpy.Delete_management(fci[1])
arcpy.Delete_management(fci[2])
arcpy.Delete_management(fci[3])
arcpy.Delete_management(fci[4])
arcpy.Delete_management(fci[5])
arcpy.Delete_management(fci[6])
arcpy.Delete_management(fci[7])
arcpy.Delete_management(fci[8])
#arcpy.Delete_management(fci[9])

arcpy.Delete_management(fco[0])
arcpy.Delete_management(fco[1])
arcpy.Delete_management(fco[2])
arcpy.Delete_management(fco[3])
arcpy.Delete_management(fco[4])
arcpy.Delete_management(fco[5])
arcpy.Delete_management(fco[6])
arcpy.Delete_management(fco[7])
arcpy.Delete_management(fco[8])

## extracting subbasin ID into the HRU attribute table
subwatershedd = os.path.join(workspace2,"subwatershedd")
arcpy.CopyFeatures_management(subwatershed, subwatershedd)

HRU_final = os.path.join(workspace2,"HRU_final")

fms = arcpy.FieldMappings()

#loading all field objects from joinFC into the <FieldMappings object>
fms.addTable(subwatershedd)

fields_sequence = ['SubId','DownSubId','Rivlen','BkfWidth','BkfDepth','IsObs','RivSlope','Ch_n','FloodP_n','IsLake','HyLakeId','AREA']
#remove fieldmaps for those fields that are not needed in the output joined fc
fields_to_delete = [f.name for f in fms.fields if f.name not in fields_sequence]
for field in fields_to_delete:
    fms.removeFieldMap(fms.findFieldMapIndex(field))

#now need to create a new fms and loat all fields from cities fc
#compiling output fms - all fields from cities
fms_out = arcpy.FieldMappings()
fms_out.addTable(HRUF6)

# we need to add Troncon_ID to fieldmapping
for field in fields_sequence:
    mapping_index = fms.findFieldMapIndex(field)
    field_map = fms.fieldMappings[mapping_index]
    fms_out.addFieldMap(field_map)

#[f.name for f in fms_out.fields] [all HRU5 fields ] + [Troncon_id]

arcpy.SpatialJoin_analysis(target_features=HRUF6, join_features=subwatershedd,
                          out_feature_class=HRU_final,
                          join_operation='JOIN_ONE_TO_ONE',join_type='KEEP_ALL',
                          field_mapping=fms_out,match_option='WITHIN',
                          search_radius=None,distance_field_name=None)

arcpy.DeleteField_management(HRU_final,["Join_Count","Join_Count_1","Join_Count_12","Join_Count_12_13","TARGET_FID","TARGET_FID_1","TARGET_FID_12","TARGET_FID_12_13","FID_soil","pointid","FID_lu_agg"])
