def hru2(path0,path,outMerge):
    print ('add latitude,longitude, HRU ID, and Elevation information to the HRU feature class')
    import arcpy, os, re
    # from arcpy.sa import *
    from arcpy import env
    arcpy.env.workspace = path
 #   arcpy.env.scratchWorkspace = path
   # outMerge = os.path.join(path, "HRU5" + "." + "shp")
 #   outMerge = os.path.join(path, "output.gdb", "HRU5")

    # arcpy.CopyFeatures_management("HRU4.shp", outMerge)
    arcpy.DeleteField_management(outMerge, "ident")

    # add latitude, longitude, elevation, area (km2), to the HRU feature class
    arcpy.DeleteField_management(outMerge, ["POLY_AREA"])
    arcpy.AddGeometryAttributes_management(outMerge, "AREA", "METERS", "SQUARE_KILOMETERS")  # area in km2

    # add longitude, latitude fields
    arcpy.AddField_management(outMerge, "latitude", "DOUBLE", "", "", 16)
    arcpy.AddField_management(outMerge, "longitude", "DOUBLE", "", "", 16)

    # gcs = arcpy.Describe("HRU.shp").spatialReference  # HRU.shp is a projected coordinate system. for latitude, longitude we need geographic coordinate system.
    sr = arcpy.SpatialReference(4269)  # EPSG oce of NAD83=4269

    with arcpy.da.UpdateCursor(outMerge, ['SHAPE@', 'latitude', 'longitude']) as rows:
        for row in rows:
            pnt_sr = row[0].projectAs(sr)
            row[1:] = [pnt_sr.centroid.Y, pnt_sr.centroid.X]  # will be in decimal degrees
            rows.updateRow(row)
    del rows

    # Replace none values in attribute table
    with arcpy.da.UpdateCursor(outMerge, ['soil_type', 'LU_type', 'slope']) as rows:
        for row in rows:
            if row[0] == None:
                row[0] = "1"
            if row[1] == None:
                row[1] = "1"
            if row[2] == None:
                row[2] = "1"
            rows.updateRow(row)
    del rows

    # add mean elevation to the field
    #altitude = os.path.join(path, "HRU2" + "." + "shp")
    altitude = os.path.join(path0, "altitude" + "." + "tif")
    elev_point = os.path.join(path, "elev_point")

    arcpy.RasterToPoint_conversion(altitude, elev_point, "Value")
    # Split feature class into multiple polygons based on landuse ID and then run the spatial join to add mean elevation to the attribute table, and finaly merge all polygons

    arcpy.SplitByAttributes_analysis(outMerge, path, ['LU_type'])

    fci = ["T0_0","T1_0","T2_0","T3_0","T4_0","T5_0","T6_0","T7_0","T8_0","T9_0"]  #these are splitted shapefiles
    fco = ["T0_0_sj","T1_0_sj","T2_0_sj","T3_0_sj","T4_0_sj","T5_0_sj","T6_0_sj","T7_0_sj","T8_0_sj","T9_0_sj"]  #these are splitted shapefiles
    for i in range(len(fci)):
        fnp = os.path.join(path, fci[i])  # the input shapefile
        fieldmappings = arcpy.FieldMappings()
        # fieldmappings.addInputField("HRU.shp","Mean_elev")
        fieldmappings.addTable(fnp)  # add attribute table of HRU feature class to the fieldmap
        fieldmappings.addTable(elev_point)  # add attribute table of elev_point feature class to the fieldmap

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
  #      HRU6 = os.path.join(path, "output.gdb", "HRU6")
    #  HRU6 = os.path.join(path, "HRU6" + "." + "shp")

        arcpy.SpatialJoin_analysis(fci[i], elev_point, fco[i], "#", "#", fieldmappings)

    HRU6 = os.path.join(path, "HRU6")
    arcpy.Merge_management(fco,HRU6)

    arcpy.DeleteField_management(HRU6, ["ident","Join_Count","TARGET_FID"])
    arcpy.Delete_management(fci[0])
    arcpy.Delete_management(fci[1])
    arcpy.Delete_management(fci[2])
    arcpy.Delete_management(fci[3])
    arcpy.Delete_management(fci[4])
    arcpy.Delete_management(fci[5])
    arcpy.Delete_management(fci[6])
    arcpy.Delete_management(fci[7])
    arcpy.Delete_management(fci[8])
    arcpy.Delete_management(fci[9])

    arcpy.Delete_management(fco[0])
    arcpy.Delete_management(fco[1])
    arcpy.Delete_management(fco[2])
    arcpy.Delete_management(fco[3])
    arcpy.Delete_management(fco[4])
    arcpy.Delete_management(fco[5])
    arcpy.Delete_management(fco[6])
    arcpy.Delete_management(fco[7])
    arcpy.Delete_management(fco[8])
    arcpy.Delete_management(fco[9])

    # delete intermediate feature classes


    # Numbering the HRU feature class
    arcpy.AddField_management(HRU6, "HRU_ID", "LONG", "", "", 16)
    HRU_ID = 1
    with arcpy.da.UpdateCursor(HRU6, "HRU_ID") as cursor:
        for row in cursor:
            row[0] = HRU_ID
            HRU_ID = HRU_ID + 1
            cursor.updateRow(row)

    print('done!')



