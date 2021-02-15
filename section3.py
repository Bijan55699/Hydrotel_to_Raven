def identity_SAGA(path,subwatershed):
    import arcpy, os, re
    # from arcpy.sa import *
    from arcpy import env
    arcpy.env.workspace = path

    print('Performing Identity using SAGA GIS')
  #  subwatershed = os.path.join(path, "uhrh_diss" + "." + "shp")  # subwatershed map created by Hydrotel_Raven code
    HRU2 = os.path.join(path, "HRU2" + "." + "shp")
    HRU3 = os.path.join(path, "HRU3" + "." + "shp")

    os.system("saga_cmd shapes_polygons 19 -A " + HRU2 + " -B " + subwatershed + " -RESULT " + HRU3)
    arcpy.DeleteField_management(HRU3, ["NAME"])
    arcpy.DeleteField_management(HRU3, ["Dowstr_ID"])
    arcpy.DeleteField_management(HRU3, ["PROFILE"])
    arcpy.DeleteField_management(HRU3, ["Length_km"])
    arcpy.DeleteField_management(HRU3, ["GAUGED"])
    arcpy.DeleteField_management(HRU3, ["Type"])
    arcpy.DeleteField_management(HRU3, ["Troncon_id"])
    print('done!')