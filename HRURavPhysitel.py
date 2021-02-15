
import arcpy,os,re
from arcpy.sa import *
from arcpy import env
import shutil

pathtoDirectory = r"C:\Users\mohbiz1\Desktop\Dossier_travail\Hydrotel\DEH\MG24HA\ABIT_MG24HA_2020\physitel"
workspace = os.path.join(pathtoDirectory+ "\HRU")

shutil.copytree(pathtoDirectory,workspace)

# set the environment workspace for arcpy
arcpy.env.workspace = workspace
subwatershed = os.path.join(workspace,"uhrh_diss"+"."+"shp") #subwatershed map created by Hydrotel_Raven code
arcpy.env.scratchWorkspace = workspace

# calling the sections
# running section 1
from section1 import slopeaspect
slopeaspect(workspace)

# running section 2
from section2 import hru1
intslope = os.path.join(workspace,"times"+"."+"tif")
hru1(workspace,intslope)

# running section 3
HRU2 = os.path.join(workspace,"HRU2"+"."+"shp")
HRU3 = os.path.join(workspace,"HRU3"+"."+"shp")
from section3 import identity_SAGA
identity_SAGA(workspace,subwatershed)

# running section 4
from section4 import overlay
overlay(workspace)

# running section 5
arcpy.CreateFileGDB_management(workspace, "output.gdb")
outMerge = os.path.join(workspace, "output.gdb", "HRU5")
arcpy.Merge_management(["HRU4.shp", "lacs.shp"], outMerge)
workspace2 = os.path.join(workspace+ "\output.gdb")
from section5 import hru2
hru2(workspace,workspace2,outMerge)

# running section 6
from section6 import addsubwatershed
addsubwatershed(workspace2,subwatershed)