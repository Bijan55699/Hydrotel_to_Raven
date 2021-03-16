def overlay(path):

    import arcpy, os, re
    # from arcpy.sa import *
    from arcpy import env
    arcpy.env.workspace = path

    print('Overlaying the HRU map with lakes')

    HRU2 = os.path.join(path, "HRU2" + "." + "shp")
    HRU3 = os.path.join(path, "HRU3" + "." + "shp")
    HRU4 = os.path.join(path, "HRU4" + "." + "shp")

    arcpy.Intersect_analysis([HRU3, "lacs.shp"], "HRU_intersect", "ALL")
    arcpy.Union_analysis([HRU3, "lacs.shp"], "HRU_union", "ALL")

    arcpy.MakeFeatureLayer_management('HRU_intersect.shp', 'HRU_intersect_lyr')
    arcpy.MakeFeatureLayer_management('HRU_union.shp', 'HRU_union_lyr')
    arcpy.SelectLayerByLocation_management("HRU_union_lyr", "ARE_IDENTICAL_TO", "HRU_intersect_lyr")
    if arcpy.Describe("HRU_union_lyr").FIDSet:
        arcpy.DeleteFeatures_management("HRU_union_lyr")

    arcpy.CopyFeatures_management("HRU_union_lyr", HRU4)
    arcpy.DeleteField_management(HRU4, ["FID_lacs", "ident", "FID_HRU3"])
    # arcpy.DeleteField_management("HRU4.shp",["ident"])
    # arcpy.DeleteField_management("HRU4.shp",["FID_HRU3"])
    HRUintersect = os.path.join(path, "HRU_intersect" + "." + "shp")
    arcpy.Delete_management(HRUintersect)
    HRUunion = os.path.join(path, "HRU_union" + "." + "shp")
    arcpy.Delete_management(HRUunion)
    arcpy.Delete_management(HRU2)
    arcpy.Delete_management(HRU3)
    
    print('done!')
