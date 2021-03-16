import arcpy,os,re
from arcpy.sa import *
from arcpy import env

arcpy.env.overwriteOutput = True
workspace = r"C:\Users\mohbiz1\Desktop\Dossier_travail\Hydrotel\DEH\MG24HA\SLNO_MG24HA_2020\physitel\HRU"
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

#sr=arcpy.Describe(lu).spatialReference
#
# arcpy.AddField_management(subwatershed2, "Troncon_id", "LONG", "", "", 16)
# arcpy.CalculateField_management(subwatershed2, "Troncon_id", "!gridcode!", "PYTHON_9.3")
# arcpy.DeleteField_management("soil_poly.shp", "gridcode")
##########################################################################
# Use Identity to cut the features with subwatershed boundaries
HRU_identity = os.path.join(workspace,"HRU_identity"+ "." + "shp") #subwatershed map created by Hydrotel_Raven code
os.system("saga_cmd shapes_polygons 19 -A " + HRU1 + " -B " + subwatershed + " -RESULT " + HRU_identity)

###########################################################################
arcpy.CheckOutExtension("Spatial")  #activating spetial analyst module

# run Tabulate area to determine the surface area of each LU class in subwatershed
outareatable = os.path.join(workspace,"outareatable"+"."+"dbf") #
TabulateArea(subwatershed,"SubId",HRU_identity,"LU_type",outareatable,lu_raster)

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

where = ' "SubId" =0 '
arcpy.MakeFeatureLayer_management(HRU_identity, 'HRU_identity_lyr')
arcpy.SelectLayerByAttribute_management("HRU_identity_lyr", "NEW_SELECTION",where)  # select the subwaterwshed=i in LU map

if arcpy.Describe("HRU_identity_lyr").FIDSet:
     arcpy.DeleteFeatures_management("HRU_identity_lyr")
#
# lu_identity2 = os.path.join(workspace,"lu_identity2"+ "." + "shp") #subwatershed map created by Hydrotel_Raven code
# arcpy.CopyFeatures_management("lu_identity_lyr", lu_identity2)
############################################################################

#run spatial join between subwatershed map and new LU map to find the subwatershed in whcih the HRU is located

fms = arcpy.FieldMappings()
# loading all field objects from joinFC into the <FieldMappings object>
fms.addTable(subwatershed)

fields_sequence = ['DownSubId','Rivlen','BkfWidth','BkfDepth','IsObs','RivSlope','Ch_n','FloodP_n','IsLake','SubId','GRIDC_1','GRIDC_2','GRIDC_3','GRIDC_4','GRIDC_5','GRIDC_6','GRIDC_7','GRIDC_8','GRIDC_9','COUNT','AREA','MAJORITY']
# remove fieldmaps for those fields that are not needed in the output joined fc
fields_to_delete = [f.name for f in fms.fields if f.name not in fields_sequence]
for field in fields_to_delete:
    fms.removeFieldMap(fms.findFieldMapIndex(field))
    fms_out = arcpy.FieldMappings()
    fms_out.addTable(HRU_identity)

# we need to add Troncon_ID to fieldmapping
for field in fields_sequence:
    mapping_index = fms.findFieldMapIndex(field)
    field_map = fms.fieldMappings[mapping_index]
    fms_out.addFieldMap(field_map)


LU_HRU_agg = os.path.join(workspace,"LU_HRU_agg"+ "." + "shp")

arcpy.SpatialJoin_analysis(target_features=HRU_identity, join_features=subwatershed,
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
HRU_agg_threshold = os.path.join(workspace, "lu_agg_final_threshold" + "." + "shp") #subwatershed map created by Hydrotel_Raven code
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

arcpy.Merge_management(mergelist, HRU_agg_threshold)
for fc in mergelist:
    if arcpy.Exists(fc):
        arcpy.Delete_management(fc)

# add latitude,longitude, HRU ID, Slope, aspect, and Elevation to the HRU feature class

# Numbering the HRU feature class
arcpy.AddField_management(HRU_agg_threshold, "HRU_ID", "LONG", "", "", 16)
HRU_ID = 1
with arcpy.da.UpdateCursor(HRU_agg_threshold, "HRU_ID") as cursor:
    for row in cursor:
        row[0] = HRU_ID
        HRU_ID = HRU_ID + 1
        cursor.updateRow(row)

# add longitude, latitude fields
arcpy.AddField_management(HRU_agg_threshold, "HRU_CenY", "DOUBLE", "", "", 16)
arcpy.AddField_management(HRU_agg_threshold, "HRU_CenX", "DOUBLE", "", "", 16)

# gcs = arcpy.Describe("HRU.shp").spatialReference  # HRU.shp is a projected coordinate system. for latitude, longitude we need geographic coordinate system.
sr = arcpy.SpatialReference(4269)  # EPSG code of NAD83=4269

with arcpy.da.UpdateCursor(HRU_agg_threshold, ['SHAPE@', 'HRU_CenY', 'HRU_CenX']) as rows:
    for row in rows:
        pnt_sr = row[0].projectAs(sr)
        row[1:] = [pnt_sr.centroid.Y, pnt_sr.centroid.X]  # will be in decimal degrees
        rows.updateRow(row)
del rows

# add mean elevation of each HRU to the attribute table

arcpy.RasterToPoint_conversion("altitude.tif","elev_point.shp", "Value")

fieldmappings = arcpy.FieldMappings()
#fieldmappings.addInputField("HRU.shp","Mean_elev")
fieldmappings.addTable(lu_agg_final_5) #add attribute table of HRU feature class to the fieldmap
fieldmappings.addTable("elev_point.shp") #add attribute table of elev_point feature class to the fieldmap

asptFieldIndex = fieldmappings.findFieldMapIndex("grid_code")
fieldmap = fieldmappings.getFieldMap(asptFieldIndex)

# Get the output field's properties as a field object
field = fieldmap.outputField

# Rename the field and pass the updated field object back into the field map
field.name = "HRU_E_mean"
field.aliasName = "HRU_E_mean"
fieldmap.outputField = field

# Set the merge rule to mean and then replace the old fieldmap in the mappings object
# with the updated one
fieldmap.mergeRule = "mean"
fieldmappings.replaceFieldMap(asptFieldIndex, fieldmap)

# Run the Spatial Join tool, using the defaults for the join operation and join type
HRU6 = os.path.join(workspace,"output.gdb","HRU6")
arcpy.SpatialJoin_analysis(HRU_agg_threshold, "elev_point.shp", HRU6, "#", "#", fieldmappings)


# adding mean slope of HRUs
slope1 = Slope("altitude.tif",'DEGREE')  # SLOPE IN DEGREE
slope1.save("slope_in_deg.tif")

arcpy.RasterToPoint_conversion(slope1,"slope_shapefile.shp", "Value")

fieldmappings = arcpy.FieldMappings()
#fieldmappings.addInputField("HRU.shp","Mean_elev")
fieldmappings.addTable(HRU6) #add attribute table of HRU feature class to the fieldmap
fieldmappings.addTable("slope_shapefile.shp") #add attribute table of elev_point feature class to the fieldmap

asptFieldIndex = fieldmappings.findFieldMapIndex("grid_code")
fieldmap = fieldmappings.getFieldMap(asptFieldIndex)

# Get the output field's properties as a field object
field = fieldmap.outputField

# Rename the field and pass the updated field object back into the field map
field.name = "HRU_S_mean"
field.aliasName = "HRU_S_mean"
fieldmap.outputField = field

# Set the merge rule to mean and then replace the old fieldmap in the mappings object
# with the updated one
fieldmap.mergeRule = "mean"
fieldmappings.replaceFieldMap(asptFieldIndex, fieldmap)

# Run the Spatial Join tool, using the defaults for the join operation and join type
HRU7 = os.path.join(workspace,"output.gdb","HRU7")
arcpy.SpatialJoin_analysis(HRU6, "slope_shapefile.shp", HRU7, "#", "#", fieldmappings)

# adding mean Aspect of HRUs
aspect1 = Aspect("altitude.tif")  # ATTENTION: Aspect in Arcgis is calculated clockwise so East is 90. in Raven's manual Aspect is assumed to be counterclockwise i.e., west 90
aspect1.save("aspect")

arcpy.RasterToPoint_conversion(aspect1,"aspect_shapefile.shp", "Value")

fieldmappings = arcpy.FieldMappings()
#fieldmappings.addInputField("HRU.shp","Mean_elev")
fieldmappings.addTable(HRU7) #add attribute table of HRU feature class to the fieldmap
fieldmappings.addTable("aspect_shapefile.shp") #add attribute table of elev_point feature class to the fieldmap

asptFieldIndex = fieldmappings.findFieldMapIndex("grid_code")
fieldmap = fieldmappings.getFieldMap(asptFieldIndex)

# Get the output field's properties as a field object
field = fieldmap.outputField

# Rename the field and pass the updated field object back into the field map
field.name = "HRU_A_mean"
field.aliasName = "HRU_A_mean"
fieldmap.outputField = field

# Set the merge rule to mean and then replace the old fieldmap in the mappings object
# with the updated one
fieldmap.mergeRule = "mean"
fieldmappings.replaceFieldMap(asptFieldIndex, fieldmap)

# Run the Spatial Join tool, using the defaults for the join operation and join type
HRU8 = os.path.join(workspace,"output.gdb","HRU8")
arcpy.SpatialJoin_analysis(HRU7, "aspect_shapefile.shp", HRU8, "#", "#", fieldmappings)