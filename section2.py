def hru1(path,intslope):
    import arcpy, os, re
   #from arcpy.sa import *
    from arcpy import env
    arcpy.env.workspace = path

    print('converting landuse, soil, and slope raster to polygon and delineation of HRU map')
    # converting landuse, slope, and soil rasters to feature class and overlaying the created feature classes

    arcpy.RasterToPolygon_conversion("type_sol.tif", 'soil_poly', "NO_SIMPLIFY", "VALUE")
    arcpy.RasterToPolygon_conversion("occupation_sol.tif", 'LU_poly', "NO_SIMPLIFY", "VALUE")
    arcpy.RasterToPolygon_conversion(intslope, 'pente_poly', "NO_SIMPLIFY","VALUE")  # raster to polygon conversion accepts only the integer type raster

    # add the new fields in created polygons and copy the value into it.
    arcpy.AddField_management("soil_poly.shp", "soil_type", "SHORT", "", "", "", "", "", "", "")
    arcpy.AddField_management("LU_poly.shp", "LU_type", "SHORT", "", "", "", "", "", "", "")
    arcpy.AddField_management("pente_poly.shp", "slope", "FLOAT", "", "", 32, "", "", "", "")

    arcpy.Delete_management("times.tif")
    arcpy.Delete_management("slope_in_deg.tif")

    # copy the created fields to new fields
    arcpy.CalculateField_management("soil_poly.shp", "soil_type", "!gridcode!", "PYTHON_9.3")
    arcpy.DeleteField_management("soil_poly.shp", "gridcode")
    arcpy.CalculateField_management("LU_poly.shp", "LU_type", "!gridcode!", "PYTHON_9.3")
    arcpy.DeleteField_management("LU_poly.shp", "gridcode")
    arcpy.CalculateField_management("pente_poly.shp", "slope", "!gridcode!/100.0", "PYTHON_9.3")
    arcpy.DeleteField_management("pente_poly.shp", "gridcode")
    # overlain the soil type, land use, and slope for creating the HRU map
    arcpy.Intersect_analysis(["soil_poly.shp", "LU_poly.shp"], "HRU1", "ALL")
    arcpy.Intersect_analysis(["HRU1.shp", "pente_poly.shp"], "HRU2", "ALL")

    # delete HRU1 from directory and unnecessary fields in attribute table of HRU2
    arcpy.Delete_management("HRU1.shp")
    arcpy.Delete_management("soil_poly.shp")
    arcpy.Delete_management("pente_poly.shp")
    arcpy.Delete_management("LU_poly.shp")
    arcpy.DeleteField_management("HRU2.shp",["FID_HRU1", "FID_soil_p", "FID_LU_pol", "FID_pente_", "Id", "Id_1", "Id_12"])
    print('done!')