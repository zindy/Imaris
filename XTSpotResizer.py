# -*- coding: utf-8 -*-
#
#
#  SpotResize Python XTension  
#
#    <CustomTools>
#      <Menu name = "Python plugins">
#       <Item name="Spot Resizer" icon="Python" tooltip="Resize spots">
#         <Command>PythonXT::XTSpotResize(%i)</Command>
#       </Item>
#      </Menu>
#    </CustomTools>
#
# 
# Copyright (c) 2015 Egor Zindy <egor.zindy@manchester.ac.uk>
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

import hotswap

import SpotResizeDialog
import Tkinter as tk
import tkFileDialog
import ttk

import ImarisLib
import BridgeLib

import time

import numpy as np
import sys, traceback


###########################################################################
## Main application module
###########################################################################
class MyModule:
    def __init__(self,vImaris):
        self.vImaris = vImaris
        self.vDataSet = vImaris.GetDataSet()
        self.object_names = []

        #the range values for all axis (will be set when needed)
        self._xrange = None
        self._yrange = None
        self._zrange = None

        #Get the voxel sizes...
        nz = self.vDataSet.GetSizeZ()
        self.is3D = nz > 1

        self.InitDialog()

    def onHotswap(self):
        print "swap!"

    def InitDialog(self):
        #Build the dialog
        self.arrayvar_last = []

        self.Dialog=SpotResizeDialog.Dialog(self.is3D)
        self.Dialog.set_icon(BridgeLib.GetIcon())
        self.Dialog.Update = self.Update

        self.UpdateObjects()
        self.Dialog.mainloop()

    def GetUpdated(self,old,new):
        """Check which parameters have changed between old and new dic"""
        return [x for x in set(old) & set(new) if old[x] != new[x]]

    def UpdateGui(self):
            vDataItem = self.SurpassObjects[self.Dialog.arrayvar["objects"]]
            spots = vDataItem.GetRadiiXYZ()
            if len(spots) > 0:
                self.Dialog.arrayvar["xsize"] = spots[0][0]
                self.Dialog.arrayvar["ysize"] = spots[0][1]

                if self.is3D:
                    self.Dialog.arrayvar["zsize"] = spots[0][2]

    def UpdateObjects(self,force=False,update=False):
        self.SurpassObjects = BridgeLib.GetSurpassObjects(self.vImaris,"spots")
        self.SurpassObjects.update(BridgeLib.GetSurpassObjects(self.vImaris,"surfaces"))
        object_names = self.SurpassObjects.keys()
        object_names.sort()

        if object_names != self.object_names or force:
            self.object_names = object_names
            self.indexdic = {}
            nobjs = len(object_names)
            for i in range(nobjs):
                oname = object_names[i]
                self.indexdic[oname] = i

            #Reset the current object selection
            self.current_object = 0

            #Change the dropdown menu and select default
            self.Dialog.SetObjects(self.object_names,self.current_object)
            self.UpdateGui()

        if update:
            self.Update(self.Dialog.arrayvar,"objects")

    def Update(self, arrayvar, elementname):
        '''Updating everything...'''

        useDefault = (self.Dialog.arrayvar["check_defaultsize"] == "on")

        self.Dialog.config(cursor="wait")
        #changed = set(self.GetUpdated(self.arrayvar_last, arrayvar))
        replot = False

        if elementname == "menuitem":
            if arrayvar[elementname] == "File/Update objects":
                self.UpdateObjects(update=True)

        elif elementname == "btn3":
            self.SetSize()

        elif elementname == "objects":
            self.current_object = self.indexdic[arrayvar[elementname]]
            self.vDataItem = self.SurpassObjects[arrayvar[elementname]]
            self.UpdateGui()

        self.arrayvar_last = arrayvar
        self.Dialog.config(cursor="")

    def SetSize(self):
        xsize = float(self.Dialog.arrayvar["xsize"])
        ysize = float(self.Dialog.arrayvar["ysize"])

        nspots = len(self.vDataItem.GetRadiiXYZ())

        if self.is3D:
            zsize = float(self.Dialog.arrayvar["zsize"])
            spot = [xsize, ysize,zsize]
        else:
            spot = [xsize, ysize,1]

        spots = [spot]*nspots
        print spots[:10]
        self.vDataItem.SetRadiiXYZ(spots)

        print 

def XTSpotResize(aImarisId):
    # Create an ImarisLib object
    vImarisLib = ImarisLib.ImarisLib()

    # Get an imaris object with id aImarisId
    vImaris = vImarisLib.GetApplication(aImarisId)

    # Check if the object is valid
    if vImaris is None:
        print "Could not connect to Imaris!"
        exit(1)

    vDataSet = vImaris.GetDataSet()
    if vDataSet is None:
        print "No data available!"
        exit(1)

    #The hotswap module watcher...
    _watcher = hotswap.ModuleWatcher()
    _watcher.run()

    aModule = MyModule(vImaris)



