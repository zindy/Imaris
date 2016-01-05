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

def GetType(dataset):
    """Get the numpy dtype of the dataset"""
    return imaris_types[str(dataset.GetType())]

def GetRange(dataset):
    """Get the pixel intensity range of the dataset"""
    dtype = GetType(dataset)
    if dtype == numpy.uint8 or dtype == numpy.uint16:
        info = numpy.iinfo(dtype)
    else:
        info = numpy.finfo(dtype)
    return info.min,info.max

def GetExtent(dataset):
    """Get the X,Y,Z extents of a dataset"""
    return [dataset.GetExtendMinX(),dataset.GetExtendMaxX(),
            dataset.GetExtendMinY(),dataset.GetExtendMaxY(),
            dataset.GetExtendMinZ(),dataset.GetExtendMaxZ()]

def GetResolution(dataset):
    """Get the X,Y,Z pixel resolution of a dataset"""
    xmin,xmax,ymin,ymax,zmin,zmax = GetExtent(dataset)
    nx,ny,nz = dataset.GetSizeX(),dataset.GetSizeY(),dataset.GetSizeZ()

    return (xmax-xmin)/nx, (ymax-ymin)/ny, (zmax-zmin)/nz

def GetDataSlice(dataset,z,c,t):
    """Given z, channel, time indexes, return a numpy array"""
    dtype = GetType(dataset)
    if dtype == numpy.uint8 or dtype == numpy.uint16:
        arr = numpy.array(dataset.GetDataSliceShorts(z,c,t),dtype)
    else:
        arr = numpy.array(dataset.GetDataSliceFloats(z,c,t),dtype)
    return arr

def SetDataSlice(dataset,arr,z,c,t):
    """Given an array and z, channel, time indexes, replace a slice in an Imaris Dataset"""
    dtype = GetType(dataset)
    if dtype == numpy.uint8 or dtype == numpy.uint16:
        arr2 = arr.copy()
        dtype = arr2.dtype
        if dtype != numpy.uint16 or dtype != numpy.uint8:
            arr2[arr2 < 0] = 0
            arr2[arr2 > 65535] = 65535
            arr = arr2.astype(numpy.uint16)
        dataset.SetDataSliceShorts(arr,z,c,t)
    else:
        dataset.SetDataSliceFloats(arr.tolist(),z,c,t)

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
        arr = numpy.array(s).reshape((nz,ny,nx))
    elif dtype == numpy.float32:
        s = vDataSet.GetDataVolumeAs1DArrayShorts(aIndexC,aIndexT)
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

    if dtype == numpy.uint8:
        s = arr.ravel().tolist()
        vDataSet.SetDataVolumeAs1DArrayBytes(s,aIndexC,aIndexT)
    elif dtype == numpy.uint16:
        s = arr.ravel() #.tolist()
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
        if search.lower() == "spots":
            if vFactory.IsSpots(vChild):
                vSpots = vFactory.ToSpots(vChild)
                vName = vChild.GetName()
                ret[vName] = vSpots
        elif search.lower() == "surfaces":
            if vFactory.IsSurfaces(vChild):
                vSurfaces = vFactory.ToSurfaces(vChild)
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

def SetSurpassObject(vImaris,search="spots",name=None):
    vFactory = vImaris.GetFactory()
    vScene = vImaris.GetSurpassScene()

    if vScene is None:
        return None

    nChildren = vScene.GetNumberOfChildren()
    if search.lower() == "spots":
        vChild = vFactory.CreateSpots()
    elif search.lower() == "surfaces":
        vChild = vFactory.CreateSurfaces()
    else:
        return None

    if name is not None:
        vChild.SetName(name)

    vScene.AddChild(vChild,nChildren)
    return vChild

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
    
