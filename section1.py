def slopeaspect(path):
    import arcpy, os, re
    from arcpy.sa import Slope,Times,Aspect,Int
    from arcpy import env
    arcpy.env.workspace = path

    print('creating slope and aspect raster map')
    arcpy.CheckOutExtension("Spatial")  # activating spetial analyst module

    # Transforming altitude, soil type, landuse and slope raster maps to polygon
    # cellsize = arcpy.GetRasterProperties_management("altitude.tif","CELLSIZEX")  #Extracting the raster cell size
    # cellsize1 = float(cellsize.getOutput(0))
    # cellarea = cellsize1*cellsize1/1000000.0

    slope1 = Slope("altitude.tif", 'DEGREE')  # SLOPE IN DEGREE
    slope1.save("slope_in_deg.tif")
    const = 100.0
    OutRas = Times("slope_in_deg.tif", 100.0)
    intslope = Int(OutRas)
    intslope.save("times.tif")
    #
    aspect1 = Aspect("altitude.tif")  # ATTENTION: Aspect in Arcgis is calculated clockwise so East is 90. in Raven's manual Aspect is assumed to be counterclockwise i.e., west 90
    aspect1.save("aspect")
    print('done!')
