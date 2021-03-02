import arcpy,os,re
from arcpy.sa import *
from arcpy import env

arcpy.env.overwriteOutput = True
workspace = r"C:\Users\mohbiz1\Desktop\Dossier_travail\Hydrotel\DEH\MG24HA\SLNO_MG24HA_2020\physitel\HRU"
arcpy.env.workspace = workspace
subwatershed = os.path.join(workspace,"uhrh_diss"+"."+"shp") #subwatershed map created by Hydrotel_Raven code
lu_raster = os.path.join(workspace,"occupation_sol"+"."+"tif") #subwatershed map created by Hydrotel_Raven code
#subwatershed_raster = os.path.join(workspace,"subwatershed_ras"+"."+"tif") #subwatershed map created by Hydrotel_Raven code
#subwatershed2 = os.path.join(workspace,"uhrh_diss2"+"."+"shp") #subwatershed map created by Hydrotel_Raven code
arcpy.env.scratchWorkspace = workspace

###########################################################################
cellsize = arcpy.GetRasterProperties_management(lu_raster,"CELLSIZEX")  #Extracting the raster cell size
cellsize1 = int(cellsize.getOutput(0))
# ##########################################################################
# arcpy.FeatureToRaster_conversion(subwatershed, "Troncon_id", subwatershed_raster, lu_raster)
# arcpy.RasterToPolygon_conversion(subwatershed_raster,subwatershed2, "NO_SIMPLIFY", "VALUE")
# subwatershed3 = os.path.join(workspace,"uhrh_diss3"+"."+"shp") #subwatershed map created by Hydrotel_Raven code
# arcpy.Dissolve_management(subwatershed2,subwatershed3,"gridcode","","","")
#
# arcpy.JoinField_management(subwatershed3,"gridcode",subwatershed,"Troncon_id")
# arcpy.DeleteField_management(subwatershed3, ["Troncon__2","Troncon__1","gridcode"])

##########################################################################
# Converting LU raster to polygon for further processing
lu = os.path.join(workspace,"lu"+ "." + "shp") #subwatershed map created by Hydrotel_Raven code
arcpy.RasterToPolygon_conversion(lu_raster,lu, "NO_SIMPLIFY", "VALUE")
#sr=arcpy.Describe(lu).spatialReference
#
# arcpy.AddField_management(subwatershed2, "Troncon_id", "LONG", "", "", 16)
# arcpy.CalculateField_management(subwatershed2, "Troncon_id", "!gridcode!", "PYTHON_9.3")
# arcpy.DeleteField_management("soil_poly.shp", "gridcode")
##########################################################################
# Use Identity to cut the LU features with subwatershed boundaries
lu_identity = os.path.join(workspace,"lu_identity"+ "." + "shp") #subwatershed map created by Hydrotel_Raven code
os.system("saga_cmd shapes_polygons 19 -A " + lu + " -B " + subwatershed + " -RESULT " + lu_identity)

###########################################################################
arcpy.CheckOutExtension("Spatial")  #activating spetial analyst module

# run Tabulate area to determine the surface area of each LU class in subwatershed
outareatable = os.path.join(workspace,"outareatable"+"."+"dbf") #
TabulateArea(subwatershed,"SubId",lu_identity,"gridcode",outareatable,cellsize1)

# run zonal statistics tool to determine the dominant landuse class in each subwatershed
outzstable = os.path.join(workspace,"outzstable"+"."+"dbf") #
outZonalStats = ZonalStatisticsAsTable(subwatershed, "SubId", lu_raster, outzstable,"DATA","MAJORITY")
#outZonalStats.save(outzstable)

# Join the two tables to the subwatershed's attribute table
arcpy.JoinField_management(subwatershed,"SubId",outareatable,"SubId")
arcpy.JoinField_management(subwatershed,"SubId",outzstable,"SubId")
# add subwatershed area (in m2) to the attribute table
arcpy.AddGeometryAttributes_management(subwatershed, "AREA", "METERS", "SQUARE_METERS")  # area in m2
############################################################################

where = ' "Troncon_id" =0 '
arcpy.MakeFeatureLayer_management(lu_identity, 'lu_identity_lyr')
arcpy.SelectLayerByAttribute_management("lu_identity_lyr", "NEW_SELECTION",where)  # select the subwaterwshed=i in LU map

# if arcpy.Describe("lu_identity_lyr").FIDSet:
#     arcpy.DeleteFeatures_management("lu_identity_lyr")
#
# lu_identity2 = os.path.join(workspace,"lu_identity2"+ "." + "shp") #subwatershed map created by Hydrotel_Raven code
# arcpy.CopyFeatures_management("lu_identity_lyr", lu_identity2)
############################################################################

#run spatial join between subwatershed map and new LU map to find the subwatershed in whcih the HRU is located

fms = arcpy.FieldMappings()
# loading all field objects from joinFC into the <FieldMappings object>
fms.addTable(subwatershed)

fields_sequence = ['Troncon_id','POLY_AREA','GRIDC_2','GRIDC_3','GRIDC_4','GRIDC_5','GRIDC_6','GRIDC_7','GRIDC_8','GRIDC_9','MAJORITY']
# remove fieldmaps for those fields that are not needed in the output joined fc
fields_to_delete = [f.name for f in fms.fields if f.name not in fields_sequence]
for field in fields_to_delete:
    fms.removeFieldMap(fms.findFieldMapIndex(field))
    fms_out = arcpy.FieldMappings()
    fms_out.addTable(lu_identity)

# we need to add Troncon_ID to fieldmapping
for field in fields_sequence:
    mapping_index = fms.findFieldMapIndex(field)
    field_map = fms.fieldMappings[mapping_index]
    fms_out.addFieldMap(field_map)


LU_HRU_agg = os.path.join(workspace,"LU_HRU_agg"+ "." + "shp") #subwatershed map created by Hydrotel_Raven code

arcpy.SpatialJoin_analysis(target_features=lu_identity, join_features=subwatershed,
                               out_feature_class=LU_HRU_agg,
                               join_operation='JOIN_ONE_TO_ONE', join_type='KEEP_ALL',
                               field_mapping=fms_out, match_option='WITHIN',
                               search_radius=None, distance_field_name=None)

#
where = ' "Troncon_id" =0 '
arcpy.MakeFeatureLayer_management(LU_HRU_agg, 'LU_HRU_agg_ly')
arcpy.SelectLayerByAttribute_management("LU_HRU_agg_ly", "NEW_SELECTION",where)  # select the subwaterwshed=i in LU map
#
if arcpy.Describe("LU_HRU_agg_ly").FIDSet:
     arcpy.DeleteFeatures_management("LU_HRU_agg_ly")

arcpy.SelectLayerByAttribute_management('LU_HRU_agg_ly', "CLEAR_SELECTION")

LU_HRU_agg6 = os.path.join(workspace,"LU_HRU_agg6"+ "." + "shp") #subwatershed map created by Hydrotel_Raven code
arcpy.CopyFeatures_management("LU_HRU_agg_ly", LU_HRU_agg6)

################################################################################################
# Defining the threshold and creating the simplified HRU map
Threshold = 5
result = arcpy.GetCount_management(subwatershed)
subwsh_count = int(result.getOutput(0))
arcpy.MakeFeatureLayer_management(LU_HRU_agg6, 'LU_HRU_agg6_lyr')
count = subwsh_count -1
lu_agg_final_5 = os.path.join(workspace,"lu_agg_final_5"+ "." + "shp") #subwatershed map created by Hydrotel_Raven code
#arcpy.CreateFeatureclass_management(workspace, 'lu_agg_final', "POLYGON", "", "DISABLED", "DISABLED",sr)
mergelist = []
for i in range(subwsh_count):
    subwsh_number = i + 1
    name = "merge_subwsh_%i.shp" %subwsh_number
    where = ' "Troncon_id" = %i ' % subwsh_number
    arcpy.SelectLayerByAttribute_management("LU_HRU_agg6_lyr", "NEW_SELECTION", where)  # select the subwaterwshed=i in LU map
    if arcpy.Describe("LU_HRU_agg6_lyr").FIDSet:
        with arcpy.da.UpdateCursor("LU_HRU_agg6_lyr", ["GRIDC_2","GRIDC_3","GRIDC_4","GRIDC_5","GRIDC_6","GRIDC_7","GRIDC_8","GRIDC_9","gridcode","POLY_AREA","MAJORITY"]) as cursor:
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
        arcpy.Dissolve_management('LU_HRU_agg6_lyr', name, "gridcode", "", "MULTI_PART", "")
        mergelist.append(name)

#arcpy.SelectLayerByAttribute_management('LU_HRU_agg4_lyr', "CLEAR_SELECTION")

arcpy.Merge_management(mergelist,lu_agg_final_5)
for fc in mergelist:
    if arcpy.Exists(fc):
        arcpy.Delete_management(fc)

# add latitude,longitude, HRU ID, and Elevation information to the HRU feature class


