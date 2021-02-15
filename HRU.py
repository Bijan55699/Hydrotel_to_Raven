# This script is intended to create HRU map from Hydrotel inputs
import arcpy,os,re
from arcpy.sa import *
from arcpy import env

arcpy.env.overwriteOutput = True
env.workspace = r"C:\Users\mohbiz1\Desktop\Dossier_travail\Hydrotel\DEH\MG24HA\ABIT_MG24HA_2020\physitel\HRU"
workspace = arcpy.env.workspace
subwatershed = os.path.join(workspace,"uhrh_diss"+"."+"shp") #subwatershed map created by Hydrotel_Raven code
arcpy.env.scratchWorkspace = workspace

###############################################################################################################
print ('section 1')
arcpy.CheckOutExtension("Spatial")  #activating spetial analyst module

# Transforming altitude, soil type, landuse and slope raster maps to polygon
#cellsize = arcpy.GetRasterProperties_management("altitude.tif","CELLSIZEX")  #Extracting the raster cell size
#cellsize1 = float(cellsize.getOutput(0))
#cellarea = cellsize1*cellsize1/1000000.0

slope1 = Slope("altitude.tif",'DEGREE')  # SLOPE IN DEGREE
slope1.save("slope_in_deg.tif")
const = 100.0
arcpy.Times_3d("slope_in_deg.tif","100.0","times.tif")
intslope= Int("times.tif")
#
aspect1 = Aspect("altitude.tif")  # ATTENTION: Aspect in Arcgis is calculated clockwise so East is 90. in Raven's manual Aspect is assumed to be counterclockwise i.e., west 90
aspect1.save("aspect")


#############################################################################################################
print ('section 2')
# converting landuse, slope, and soil rasters to feature class and overlaying the created feature classes

arcpy.RasterToPolygon_conversion("type_sol.tif",'soil_poly',"NO_SIMPLIFY","VALUE")
arcpy.RasterToPolygon_conversion("occupation_sol.tif",'LU_poly',"NO_SIMPLIFY","VALUE")
arcpy.RasterToPolygon_conversion(intslope,'pente_poly',"NO_SIMPLIFY","VALUE")  # raster to polygon conversion accepts only the integer type raster

# add the new fields in created polygons and copy the value into it.
arcpy.AddField_management("soil_poly.shp", "soil_type","SHORT", "","","","","","","")
arcpy.AddField_management("LU_poly.shp", "LU_type","SHORT", "","","","","","","")
arcpy.AddField_management("pente_poly.shp", "slope","FLOAT", "","",32,"","","","")

arcpy.Delete_management("times.tif")
arcpy.Delete_management("slope_in_deg.tif")

# copy the created fields to new fields
arcpy.CalculateField_management("soil_poly.shp", "soil_type","!gridcode!", "PYTHON_9.3")
arcpy.DeleteField_management("soil_poly.shp", "gridcode")
arcpy.CalculateField_management("LU_poly.shp", "LU_type","!gridcode!", "PYTHON_9.3")
arcpy.DeleteField_management("LU_poly.shp", "gridcode")
arcpy.CalculateField_management("pente_poly.shp", "slope","!gridcode!/100.0", "PYTHON_9.3")
arcpy.DeleteField_management("pente_poly.shp", "gridcode")
# overlain the soil type, land use, and slope for creating the HRU map
arcpy.Intersect_analysis(["soil_poly.shp", "LU_poly.shp"],"HRU1","ALL")
arcpy.Intersect_analysis(["HRU1.shp", "pente_poly.shp"],"HRU2","ALL")

# delete HRU1 from directory and unnecessary fields in attribute table of HRU2
arcpy.Delete_management("HRU1.shp")
arcpy.Delete_management("soil_poly.shp")
arcpy.Delete_management("pente_poly.shp")
arcpy.Delete_management("LU_poly.shp")
arcpy.DeleteField_management("HRU2.shp",["FID_HRU1","FID_soil_p","FID_LU_pol","FID_pente_","Id","Id_1","Id_12"])
########################################################################################################
print ('section 3')
# identity to seperate HRUs based on subwatershed boundaries. Identity tool exists in Advanced ARCGIS licens. following is a workaround
# for basic/standard ArcGIS license. the idea is to use SAGA GIS command line to run the Identity module
# The details can be found here: http://www.saga-gis.org/saga_api_python/installation.html

#arcpy.Identity_analysis(in_features=HRU,identity_features=subwatershed,out_feature_class=HRU2,
 #                       join_attributes="ALL",cluster_tolerance=None,relationship=None)
HRU2 = os.path.join(workspace,"HRU2"+"."+"shp")
HRU3 = os.path.join(workspace,"HRU3"+"."+"shp")


os.system("saga_cmd shapes_polygons 19 -A " + HRU2 + " -B " + subwatershed + " -RESULT " + HRU3)
arcpy.DeleteField_management(HRU3,["NAME"])
arcpy.DeleteField_management(HRU3,["Dowstr_ID"])
arcpy.DeleteField_management(HRU3,["PROFILE"])
arcpy.DeleteField_management(HRU3,["Length_km"])
arcpy.DeleteField_management(HRU3,["GAUGED"])
arcpy.DeleteField_management(HRU3,["Type"])
arcpy.DeleteField_management(HRU3,["Troncon_id"])
#########################################################################################################
# Overlay lakes with the created HRU map. A lake is a unique HRU
print ('section 4')
arcpy.Intersect_analysis(["HRU3.shp","lacs.shp"],"HRU_intersect","ALL")
arcpy.Union_analysis(["HRU3.shp","lacs.shp"],"HRU_union","ALL")

arcpy.MakeFeatureLayer_management('HRU_intersect.shp', 'HRU_intersect_lyr')
arcpy.MakeFeatureLayer_management('HRU_union.shp', 'HRU_union_lyr')
arcpy.SelectLayerByLocation_management ("HRU_union_lyr", "ARE_IDENTICAL_TO", "HRU_intersect_lyr")
if arcpy.Describe ("HRU_union_lyr").FIDSet:
    arcpy.DeleteFeatures_management ("HRU_union_lyr")


arcpy.CopyFeatures_management("HRU_union_lyr", "HRU4.shp")
arcpy.DeleteField_management("HRU4.shp",["FID_lacs","ident","FID_HRU3"])
#arcpy.DeleteField_management("HRU4.shp",["ident"])
#arcpy.DeleteField_management("HRU4.shp",["FID_HRU3"])
HRUintersect = os.path.join(workspace,"HRU_intersect"+"."+"shp")
arcpy.Delete_management(HRUintersect)
HRUunion = os.path.join(workspace,"HRU_union"+"."+"shp")
arcpy.Delete_management(HRUunion)
arcpy.Delete_management(HRU2)
arcpy.Delete_management(HRU3)
#########################################################################################################
print ('section 5')
outMerge = os.path.join(workspace,"output.gdb","HRU5")
#arcpy.CopyFeatures_management("HRU4.shp", outMerge)
arcpy.Merge_management(["HRU4.shp","lacs.shp"],outMerge)
# add latitude, longitude, elevation, area (km2), to the HRU feature class
arcpy.DeleteField_management(outMerge,["POLY_AREA"])
arcpy.AddGeometryAttributes_management(outMerge, "AREA", "METERS", "SQUARE_KILOMETERS") # area in km2

#add longitude, latitude fields
arcpy.AddField_management(outMerge, "latitude", "DOUBLE", "", "", 16)
arcpy.AddField_management(outMerge, "longitude", "DOUBLE", "", "", 16)

#gcs = arcpy.Describe("HRU.shp").spatialReference  # HRU.shp is a projected coordinate system. for latitude, longitude we need geographic coordinate system.
sr = arcpy.SpatialReference(4269) #EPSG oce of NAD83=4269

with arcpy.da.UpdateCursor(outMerge, ['SHAPE@', 'latitude', 'longitude']) as rows:
    for row in rows:
        pnt_sr = row[0].projectAs(sr)
        row[1:] = [pnt_sr.centroid.Y, pnt_sr.centroid.X] #will be in decimal degrees
        rows.updateRow(row)
del rows

#Replace none values in attribute table
with arcpy.da.UpdateCursor(outMerge, ['soil_type', 'LU_type', 'slope']) as rows:
    for row in rows:
        if row[0]==None:
            row[0]="1"
        if row[1]==None:
            row[1]="1"
        if row[2]==None:
            row[2]="1"
        rows.updateRow(row)
del rows

# add mean elevation to the field

arcpy.RasterToPoint_conversion("altitude.tif","elev_point.shp", "Value")

fieldmappings = arcpy.FieldMappings()
#fieldmappings.addInputField("HRU.shp","Mean_elev")
fieldmappings.addTable(outMerge) #add attribute table of HRU feature class to the fieldmap
fieldmappings.addTable("elev_point.shp") #add attribute table of elev_point feature class to the fieldmap

elevpntFieldIndex = fieldmappings.findFieldMapIndex("grid_code")
fieldmap = fieldmappings.getFieldMap(elevpntFieldIndex)

# Get the output field's properties as a field object
field = fieldmap.outputField

# Rename the field and pass the updated field object back into the field map
field.name = "Mean_Elev"
field.aliasName = "Mean_Elev"
fieldmap.outputField = field

# Set the merge rule to mean and then replace the old fieldmap in the mappings object
# with the updated one
fieldmap.mergeRule = "mean"
fieldmappings.replaceFieldMap(elevpntFieldIndex, fieldmap)

# Run the Spatial Join tool, using the defaults for the join operation and join type
HRU6 = os.path.join(workspace,"output.gdb","HRU6")
arcpy.SpatialJoin_analysis(outMerge, "elev_point.shp", HRU6, "#", "#", fieldmappings)

# Numbering the HRU feature class
arcpy.AddField_management(HRU6, "HRU_ID", "LONG", "", "", 16)
HRU_ID = 1
with arcpy.da.UpdateCursor(HRU6, "HRU_ID") as cursor:
    for row in cursor:
            row[0] = HRU_ID
            HRU_ID = HRU_ID + 1
            cursor.updateRow(row)

###########################################################################
print ('section 6')
#extracting subbasin ID into the HRU attribute table
HRU_final = os.path.join(workspace,"output.gdb","HRU_final")

fms = arcpy.FieldMappings()

#loading all field objects from joinFC into the <FieldMappings object>
fms.addTable(subwatershed)

fields_sequence = ['Troncon_id']
#remove fieldmaps for those fields that are not needed in the output joined fc
fields_to_delete = [f.name for f in fms.fields if f.name not in fields_sequence]
for field in fields_to_delete:
    fms.removeFieldMap(fms.findFieldMapIndex(field))

#currently field mappings from counties have just two fields we have left
#[f.name for f in fms.fields] [u'NAME', u'CNTY_FIPS']

#now need to create a new fms and loat all fields from cities fc
#compiling output fms - all fields from cities
fms_out = arcpy.FieldMappings()
fms_out.addTable(HRU6)

# we need to add Troncon_ID to fieldmapping
for field in fields_sequence:
    mapping_index = fms.findFieldMapIndex(field)
    field_map = fms.fieldMappings[mapping_index]
    fms_out.addFieldMap(field_map)

#[f.name for f in fms_out.fields] [all HRU5 fields ] + [Troncon_id]

arcpy.SpatialJoin_analysis(target_features=HRU6, join_features=subwatershed,
                          out_feature_class=HRU_final,
                          join_operation='JOIN_ONE_TO_ONE',join_type='KEEP_ALL',
                          field_mapping=fms_out,match_option='WITHIN',
                          search_radius=None,distance_field_name=None)

arcpy.DeleteField_management(HRU_final,["ident","Join_Count","TARGET_FID","FID_pente_","Id","Id_1","Id_12"])
