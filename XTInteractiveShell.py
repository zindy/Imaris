#
#
#  Python Interactive Shell XTension  
#
#  Copyright (c) 2013 Egor Zindy (egor.zindy@manchester.ac.uk), BSD-style copyright and disclaimer apply
#
#    <CustomTools>
#      <Menu>
#       <Item name="Interactive Shell" icon="Python" tooltip="Opens an interactive shell.">
#         <Command>PythonXT::XTInteractiveShell(%i)</Command>
#       </Item>
#      </Menu>
#    </CustomTools>

import ImarisLib
import time

import code
import numpy


def GetType(dataset):
    imaris_types = {'eTypeUInt8':numpy.uint8,'eTypeUInt16':numpy.uint16,'eTypeFloat':numpy.float32}
    return imaris_types[str(dataset.GetType())]

def GetDataSlice(dataset,z,c,t):
    dtype = GetType(dataset)
    if dtype == numpy.uint8 or dtype == numpy.uint16:
        arr = numpy.array(dataset.GetDataSliceShorts(z,c,t),dtype)
    else:
        arr = numpy.array(dataset.GetDataSliceFloats(z,c,t),dtype)
    return arr

def SetDataSlice(dataset,arr,z,c,t):
    dtype = GetType(dataset)
    if dtype == numpy.uint8 or dtype == numpy.uint16:
        dataset.SetDataSliceShorts(arr.tolist(),z,c,t)
    else:
        dataset.SetDataSliceFloats(arr.tolist(),z,c,t)

def XTInteractiveShell(aImarisId):
    # Create an ImarisLib object
    vImarisLib = ImarisLib.ImarisLib()

    # Get an imaris object with id aImarisId
    vImaris = vImarisLib.GetApplication(aImarisId)

    # Check if the object is valid
    if vImaris is None:
        print "Could not connect to Imaris!"
        time.sleep(2)
        return

    # Get the dataset
    vDataSet = vImaris.GetDataSet()

    # Check if the object is valid
    if vDataSet is None:
        print "Warning: No dataset!\n"
    
    vars = globals().copy()
    vars.update(locals())

    shell = code.InteractiveConsole(vars)
    shell.interact()

