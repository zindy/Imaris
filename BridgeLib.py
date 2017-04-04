# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 Egor Zindy <egor.zindy@manchester.ac.uk>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:

import numpy
import ImarisLib
import Ice
import sys
import time

#make tType available
_M_Imaris = Ice.openModule('Imaris')
tType = _M_Imaris.tType

imaris_types = {'eTypeUInt8':numpy.uint8,'eTypeUInt16':numpy.uint16,'eTypeFloat':numpy.float32}

DEBUG = False

###########################################################################
## Helper functions
###########################################################################
def Reconnect(newId):
    """Given an ImarisId, Get the associated Application and DataSet instances

    Useful inside an interactive sesssion.
    """
    vImarisLib = ImarisLib.ImarisLib()
    vServer = vImarisLib.GetServer()
    vImaris,vDataSet = None,None

    for vIndex in range(vServer.GetNumberOfObjects()):
        vId = vServer.GetObjectID(vIndex)
        if vId == newId:
            vApp = vImarisLib.GetApplication(vId)
            vImaris = vImarisLib.GetApplication(newId)
            vDataSet = vImaris.GetDataSet()
            if vDataSet is None:
                print "Warning! No Dataset."
            break

    return vImaris,vDataSet

def GetType(vDataSet):
    """Get the numpy dtype of the dataset"""
    return imaris_types[str(vDataSet.GetType())]

def GetRange(vDataSet):
    """Get the pixel intensity range of the dataset"""
    nc = vDataSet.GetSizeC()
    maset = 0
    for i in range(nc):
        ma = vDataSet.GetChannelRangeMax(i)
        if ma > maset:
            maset = ma
    maset = numpy.power(2,numpy.ceil(numpy.log2(maset)))-1
    return 0,maset

    #dtype = GetType(vDataSet)
    #if dtype == numpy.uint8 or dtype == numpy.uint16:
    #    info = numpy.iinfo(dtype)
    #else:
    #    info = numpy.finfo(dtype)
    #return info.min,info.max

def GetTimepoint(vDataSet, tpi):
    dt = vDataSet.GetTimePoint(tpi)[:-4]
    pattern = '%Y-%m-%d %H:%M:%S.%f'
    return int(time.mktime(time.strptime(dt,pattern)))+float("0."+dt.split(".")[1])

def GetTimepoints(vDataSet,tpis):
    """Given a list of timepoint indexes, return the timepoints"""

    t0 = GetTimepoint(vDataSet,0)
    nt = len(tpis)
    ret = numpy.zeros(nt)

    for i in range(nt):
        ret[i] = GetTimepoint(vDataSet,tpis[i])-t0

    return ret

def GetExtent(vDataSet):
    """Get the X,Y,Z extents of a dataset"""
    return [vDataSet.GetExtendMinX(),vDataSet.GetExtendMaxX(),
            vDataSet.GetExtendMinY(),vDataSet.GetExtendMaxY(),
            vDataSet.GetExtendMinZ(),vDataSet.GetExtendMaxZ()]

def SetExtent(vDataSet,extent):
    """Get the X,Y,Z extents of a dataset"""
    vDataSet.SetExtendMinX(extent[0])
    vDataSet.SetExtendMaxX(extent[1])
    vDataSet.SetExtendMinY(extent[2])
    vDataSet.SetExtendMaxY(extent[3])
    vDataSet.SetExtendMinZ(extent[4])
    vDataSet.SetExtendMaxZ(extent[5])

def GetResolution(vDataSet):
    """Get the X,Y,Z pixel resolution of a dataset"""
    xmin,xmax,ymin,ymax,zmin,zmax = GetExtent(vDataSet)
    nx,ny,nz = vDataSet.GetSizeX(),vDataSet.GetSizeY(),vDataSet.GetSizeZ()

    return (xmax-xmin)/nx, (ymax-ymin)/ny, (zmax-zmin)/nz

def GetDataSlice(vDataSet,z,c,t):
    """Given z, channel, time indexes, return a numpy array"""
    dtype = GetType(vDataSet)
    if dtype == numpy.uint8 or dtype == numpy.uint16:
        arr = numpy.array(vDataSet.GetDataSliceShorts(z,c,t),dtype)
    else:
        arr = numpy.array(vDataSet.GetDataSliceFloats(z,c,t),dtype)
    return arr

def SetDataSlice(vDataSet,arr,z,c,t):
    """Given an array and z, channel, time indexes, replace a slice in an Imaris Dataset"""
    dtype = GetType(vDataSet)
    if dtype == numpy.uint8 or dtype == numpy.uint16:
        arr2 = arr.copy()
        dtype = arr2.dtype
        if dtype != numpy.uint16 or dtype != numpy.uint8:
            arr2[arr2 < 0] = 0
            arr2[arr2 > 65535] = 65535
            arr = arr2.astype(numpy.uint16)
        vDataSet.SetDataSliceShorts(arr,z,c,t)
    else:
        vDataSet.SetDataSliceFloats(arr.tolist(),z,c,t)

def GetDataVolume(vDataSet,aIndexC,aIndexT):
    """Given channel, time indexes, return a numpy array corresponding to the volume"""
    nx = vDataSet.GetSizeX()
    ny = vDataSet.GetSizeY()
    nz = vDataSet.GetSizeZ()
    dtype = GetType(vDataSet)
    if DEBUG:
        print "GetDataVolume"
        print "vDataSet:",(nz,ny,nx),GetType(vDataSet)
        print aIndexC
        print aIndexT

    arr = None
    if dtype == numpy.uint8:
        s = vDataSet.GetDataVolumeAs1DArrayBytes(aIndexC,aIndexT)
        arr = numpy.fromstring(s,GetType(vDataSet)).reshape((nz,ny,nx))
    elif dtype == numpy.uint16:
        s = vDataSet.GetDataVolumeAs1DArrayShorts(aIndexC,aIndexT)
        arr = numpy.array(s).reshape((nz,ny,nx)).astype(numpy.uint16)
    elif dtype == numpy.float32:
        s = vDataSet.GetDataVolumeAs1DArrayFloats(aIndexC,aIndexT)
        arr = numpy.array(s).reshape((nz,ny,nx))
    return arr

def SetDataVolume(vDataSet,arr,aIndexC,aIndexT):
    """Given a numpy array, a channel and a time index, send the array back to Imaris"""
    nx = vDataSet.GetSizeX()
    ny = vDataSet.GetSizeY()
    nz = vDataSet.GetSizeZ()
    dtype = GetType(vDataSet)
    if DEBUG:
        print "SetDataVolume"
        print "vDataSet:",(nz,ny,nx),GetType(vDataSet)
        print arr.shape
        print arr.dtype
        print aIndexC
        print aIndexT

    miset,maset = GetRange(vDataSet)
    arr[arr<miset]=miset
    arr[arr>maset]=maset

    if dtype == numpy.uint8:
        s = arr.ravel().tolist()
        vDataSet.SetDataVolumeAs1DArrayBytes(s,aIndexC,aIndexT)
    elif dtype == numpy.uint16:

        s = arr.ravel().astype(numpy.int16)
        vDataSet.SetDataVolumeAs1DArrayShorts(s,aIndexC,aIndexT)
    elif dtype == numpy.float32:
        s = arr.ravel() #.tolist()
        vDataSet.SetDataVolumeAs1DArrayFloats(s,aIndexC,aIndexT)

def GetVoxelSize(vDataSet):
    """Returns the X,Y,X, voxel dimensions"""
    nx = vDataSet.GetSizeX()
    ny = vDataSet.GetSizeY()
    nz = vDataSet.GetSizeZ()

    if nx > 0: nx = abs(vDataSet.GetExtendMaxX()-vDataSet.GetExtendMinX())/nx;
    if ny > 0: ny = abs(vDataSet.GetExtendMaxY()-vDataSet.GetExtendMinY())/ny;
    if nz > 0: nz = abs(vDataSet.GetExtendMaxZ()-vDataSet.GetExtendMinZ())/nz;

    return nx,ny,nz

def GetChannelColorRGBA(vDataSet,aIndexC):
    """Returns the R,G,B,alpha values (0-255) given a channel index"""

    rgba = vDataSet.GetChannelColorRGBA(aIndexC)
    r = rgba & 255
    g = (rgba >> 8) & 255
    b = (rgba >> 16) & 255
    a = (rgba >> 24) & 255
    return r,g,b,a

def SetChannelColorRGBA(vDataSet,aIndexC,color):
    """Sets the colour of a channel given its index and the R,G,B,alpha values (0-255) values"""

    a = 0
    r,g,b = color[0], color[1], color[2]
    if len(color) > 3: a = color[3]

    rgba = (int(a) << 24) + (int(b) << 16) + (int(g) << 8) + (int(r))
    #print r,g,b,a,rgba
    vDataSet.SetChannelColorRGBA(aIndexC,rgba)

def RemoveSurpassObject(vImaris,vChild):
    vScene = vImaris.GetSurpassScene()

    if vScene is None:
        return False

    vScene.RemoveChild(vChild)
    return True

#Factory objects
#Based on  XTGETSPOTFACES Get the Spots and Surfaces objects from Imaris
#spots, surfaces
def GetSurpassObjects(vImaris,search="spots"):
    ret = {}

    vFactory = vImaris.GetFactory()
    vScene = vImaris.GetSurpassScene()

    if vScene is None:
        return ret

    nChildren = vScene.GetNumberOfChildren()
    for i in range(nChildren):
        vChild = vScene.GetChild(i)
        if search.lower() == "frame":
            if vFactory.IsFrame(vChild):
                vFrame = vFactory.ToFrame(vChild)
                vName = vChild.GetName()
                ret[vName] = vFrame
        elif search.lower() == "spots":
            if vFactory.IsSpots(vChild):
                vSpots = vFactory.ToSpots(vChild)
                vName = vChild.GetName()
                ret[vName] = vSpots
        elif search.lower() == "surfaces":
            if vFactory.IsSurfaces(vChild):
                vSurfaces = vFactory.ToSurfaces(vChild)
                vName = vChild.GetName()
                ret[vName] = vSurfaces
        elif search.lower() == "filaments":
            if vFactory.IsFilaments(vChild):
                vSurfaces = vFactory.ToFilaments(vChild)
                vName = vChild.GetName()
                ret[vName] = vSurfaces
        elif search.lower() == "cells":
            if vFactory.IsCells(vChild):
                vSurfaces = vFactory.ToCells(vChild)
                vName = vChild.GetName()
                ret[vName] = vSurfaces

    return ret

def GetStatisticsNames(vImaris,vDataItem):
    vStatisticValues = vDataItem.GetStatistics()
    names = vs.mNames

    #return unique names...
    return list(set(names))

def isSpot(vImaris,vChild):
    ret = False
    vFactory = vImaris.GetFactory()
    if vFactory.IsSpots(vChild):
        ret = True
    return ret

def SetSurpassObject(vImaris,search="spots",name=None,pos=-1):
    vFactory = vImaris.GetFactory()
    vScene = vImaris.GetSurpassScene()

    if vScene is None:
        return None

    nChildren = vScene.GetNumberOfChildren()
    if search.lower() == "spots":
        vChild = vFactory.CreateSpots()
    elif search.lower() == "surfaces":
        vChild = vFactory.CreateSurfaces()
    elif search.lower() == "frame":
        vChild = vFactory.CreateFrame()
    else:
        return None

    if name is not None:
        vChild.SetName(name)

    vScene.AddChild(vChild,pos)
    return vChild

def FindChannel(vDataSet,match="(output)",create=True, color=None):
    """Finds a channel from a substring. If not found then create a new one (if create true)
    If none found and create is True, this method will create a new channel and return
    its new index. If not found and create is False, returns -1
    """

    ret = -1
    nc = vDataSet.GetSizeC()
    if match is not None:
        for i in range(nc):
            name = vDataSet.GetChannelName(i)
            if match in name:
                ret = i
                break

    miset,maset = GetRange(vDataSet)
    if ret == -1 and create == True:
        vDataSet.SetSizeC(nc+1)
        ret = nc
        vDataSet.SetChannelName(ret,match)
        vDataSet.SetChannelRange(ret,miset,maset)

    #allows to change the channel colour once the channel was found
    #color specified as 
    if ret >= 0 and color is not None:
        #r = 255.*color[0]/maset
        #g = 255.*color[1]/maset
        #b = 255.*color[2]/maset
        #a = 0.
        #if len(color) > 3:
        #    a = 255*color[2]/maset

        SetChannelColorRGBA(vDataSet,ret,color) #r,g,b,a)

    return ret

def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes":True,   "y":True,  "ye":True,
             "no":False,     "n":False}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")
    
def query_num(prompt="Type a number between 1 and 10", default=None, lims = [1,10]):
    if default is not None:
        if type(default) == int or type(default) == long:
            prompt = prompt+" (%d)" % default
        else:
            prompt = prompt+" (%.2f)" % default
    prompt += ": "

    while True:
        s = raw_input(prompt)

        if s == "":
            if default is None:
                continue
            else:
                val = default
                break

        try:
            if type(default) == int or type(default) == long:
                val = int(s)
            else:
                val = float(s)
        except ValueError:
            continue

        if lims is not None and (val < lims[0] or val > lims[1]):
            print "  Type a number between %d and %d" % (lims[0],lims[1])
            continue

        break

    return val

