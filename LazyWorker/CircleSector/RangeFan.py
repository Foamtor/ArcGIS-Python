# ------------------------------------------------------------------------------
# Copyright 2015 Esri
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------
# RangeFan.py
# Description: Create Range Fan
# Requirements: ArcGIS Desktop Standard
# -----------------------------------------------------------------------------
# 2/5/2015 - mf - Updates to change Web Mercator to user-selected coordinate system
# 2/18/2015 - ps - addition to allow floating point angle
#

# IMPORTS ==========================================
import os, sys, math, traceback
import arcpy
from arcpy import env


# CONSTANTS ========================================
gravitationalConstant = 9.80665  # meters/second^2, approx. 32.174 ft/sec^2


# FUNCTIONS ========================================
def Geo2Arithmetic(inAngle):
    inAngle = math.fmod(inAngle, 360.0)
    # 0 to 90
    if (inAngle >= 0.0 or inAngle <= 90.0):
        outAngle = math.fabs(inAngle - 90.0)

    # 90 to 360
    if (inAngle >= 90.0 or inAngle < 360.0):
        outAngle = 360.0 - (inAngle - 90.0)

    return float(outAngle)


def frange3(start, end=None, inc=None):
    """A range function, that does accept float increments..."""
    """http://code.activestate.com/recipes/66472-frange-a-range-function-with-float-increments/"""
    if end == None:
        end = start + 0.0
        start = 0.0
    else:
        start += 0.0  # force it to be a float

    if inc == None:
        inc = 1.0
    count = int(math.ceil((end - start) / inc))
    count += 1

    L = [None, ] * count

    L[0] = start
    for i in range(1, count):
        L[i] = L[i - 1] + inc
    return L

# ARGUMENTS & LOCALS ===============================
argCount = arcpy.GetArgumentCount()

inFeature = arcpy.GetParameterAsText(0)
dRange = float(arcpy.GetParameterAsText(1))  # 1000.0 # meters
bearing = float(arcpy.GetParameterAsText(2))  # 45.0 # degrees
traversal = float(arcpy.GetParameterAsText(3))  # 60.0 # degrees
outFeature = arcpy.GetParameterAsText(4)
outputCoordinateSystem = arcpy.GetParameter(5)
outputCoordinateSystemAsText = arcpy.GetParameterAsText(5)

# Debug Parameters
# inFeature = r"D:\IncidentSupport2015\AllforTest\ArGISTutorTest\AT_America\America.gdb\AmericanVectors_3857\cities_P"
# dRange = 1000  # 1000.0 # meters
# bearing = 45  # 45.0 # degrees
# traversal = 60  # 60.0 # degrees
# outFeature = r"D:\IncidentSupport2015\AllforTest\ArGISTutorTest\AT_America\America.gdb\cities_Sector"
# outputCoordinateSystem = ""
# outputCoordinateSystemAsText = ""


deleteme = []
debug = False
leftAngle = 0.0  # degrees
rightAngle = 90.0  # degrees

try:

    if (outputCoordinateSystemAsText == ""):
        outputCoordinateSystem = arcpy.Describe(inFeature).spatialReference
        arcpy.AddWarning("Spatial Reference is not defined. Using Spatial Reference of input features: " + str(
            outputCoordinateSystem.name))

    env.outputCoordinateSystem = outputCoordinateSystem
    currentOverwriteOutput = env.overwriteOutput
    env.overwriteOutput = True
    installInfo = arcpy.GetInstallInfo("desktop")
    installDirectory = installInfo["InstallDir"]
    scratch = env.scratchWorkspace
    # scratch = r"D:\IncidentSupport2015\AllforTest\ArGISTutorTest\AT_America\America.gdb"

    prjInFeature = os.path.join(scratch, "prjInFeature")
    arcpy.AddMessage("Projecting input points to " + str(outputCoordinateSystem.name) + " ...")
    arcpy.Project_management(inFeature, prjInFeature, outputCoordinateSystem)
    deleteme.append(prjInFeature)

    if traversal < 360:

        initialBearing = bearing
        bearing = Geo2Arithmetic(
            bearing)  # need to convert from geographic angles (zero north clockwise) to arithmetic (zero east counterclockwise)
        if traversal == 0:traversal = 1  # modify so there is at least 1 degree of angle.
        leftAngle = bearing - (traversal / 2.0)
        rightAngle = bearing + (traversal / 2.0)

        centerPoints = []
        arcpy.AddMessage("Getting centers ....")
        shapefieldname = arcpy.Describe(prjInFeature).ShapeFieldName
        rows = arcpy.SearchCursor(prjInFeature)
        for row in rows:
            feat = row.getValue(shapefieldname)
            pnt = feat.getPart()
            centerPointX = pnt.X
            centerPointY = pnt.Y
            centerPoints.append([centerPointX, centerPointY])
        del row
        del rows

        paths = []
        arcpy.AddMessage("Creating paths ...")
        for centerPoint in centerPoints:
            path = []
            centerPointX = centerPoint[0]
            centerPointY = centerPoint[1]
            path.append([centerPointX, centerPointY])  # add first point
            step = 1  # step in degrees
            # print "Left Angle, Right Angle" #UPDATE
            if debug == True: arcpy.AddMessage("Left Angle, Right Angle")
            # print leftAngle,rightAngle #UPDATE
            if debug == True: arcpy.AddMessage("leftAngle: " + str(leftAngle) + ", rightAngle: " + str(rightAngle))
            # for d in xrange(int(leftAngle),int(rightAngle),step): #UPDATE
            # for d in range(int(leftAngle),int(rightAngle),step):
            for d in frange3(leftAngle, rightAngle, step):
                if debug == True: arcpy.AddMessage("dRange: " + str(dRange))
                a = math.cos(math.radians(d))
                x = centerPointX + (dRange * a)
                if debug == True: arcpy.AddMessage("x + " + str(dRange * a))
                b = math.sin(math.radians(d))
                y = centerPointY + (dRange * b)
                if debug == True:
                    arcpy.AddMessage("y + " + str(dRange * b))
                    arcpy.AddMessage("d: " + str(math.sqrt(math.pow(a, 2) + math.pow(b, 2))))
                path.append([x, y])
            path.append([centerPointX, centerPointY])  # add last point
            paths.append(path)

        arcpy.AddMessage("Creating target feature class ...")
        arcpy.CreateFeatureclass_management(os.path.dirname(outFeature), os.path.basename(outFeature), "Polygon", "#",
                                            "DISABLED", "DISABLED", outputCoordinateSystem)
        arcpy.AddField_management(outFeature, "Range", "DOUBLE")
        arcpy.AddField_management(outFeature, "Bearing", "DOUBLE")

        arcpy.AddMessage("Building " + str(len(paths)) + " fans ...")
        cur = arcpy.InsertCursor(outFeature)
        for outPath in paths:
            lineArray = arcpy.Array()
            for vertex in outPath:
                pnt = arcpy.Point()
                pnt.X = vertex[0]
                pnt.Y = vertex[1]
                lineArray.add(pnt)
                del pnt
            feat = cur.newRow()
            feat.shape = lineArray
            feat.Range = dRange
            feat.Bearing = initialBearing
            cur.insertRow(feat)
            del lineArray
            del feat
        del cur

    else:
        if debug == True: arcpy.AddMessage("Traversal is 360 degrees, buffering instead ...")
        distance = str(dRange) + " Meters"
        arcpy.Buffer_analysis(prjInFeature, outFeature, distance)

    arcpy.SetParameter(4, outFeature)
    env.overwriteOutput = currentOverwriteOutput


except arcpy.ExecuteError:
    # Get the tool error messages 
    msgs = arcpy.GetMessages()
    arcpy.AddError(msgs)
    # print msgs #UPDATE
    print(msgs)

except:
    # Get the traceback object
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]

    # Concatenate information together concerning the error into a message string
    pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
    msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages() + "\n"

    # Return python error messages for use in script tool or Python Window
    arcpy.AddError(pymsg)
    arcpy.AddError(msgs)

    # Print Python error messages for use in Python / Python Window
    # print pymsg + "\n" #UPDATE
    print(pymsg + "\n")
    # print msgs #UPDATE
    print(msgs)

finally:
    # cleanup intermediate datasets
    if debug == True: arcpy.AddMessage("Removing intermediate datasets...")
    for i in deleteme:
        arcpy.Delete_management(i)
        if debug == True: arcpy.AddMessage("Removing: " + str(i))
    if debug == True: arcpy.AddMessage("Done")
