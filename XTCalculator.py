# -*- coding: utf-8 -*-
#
#
#  Calculator Python XTension  
#  Inspired by the ImageJ image calculator
#
#    <CustomTools>
#      <Menu name = "Python plugins">
#       <Item name="Channel Calculator" icon="Python" tooltip="Channel Calculator for Imaris.">
#         <Command>PythonXT::XTCalculator(%i)</Command>
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

import CalculatorDialog
import Tkinter as tk
import ttk

import ImarisLib
import BridgeLib

import time
import numpy as np

###########################################################################
## Main application module
###########################################################################
class MyModule:
    def __init__(self,vImaris):
        self.vImaris = vImaris

        #Use a clone
        self.vDataSet = vImaris.GetDataSet().Clone()


        #Keep all these in memory
        self.vdataset_nt = self.vDataSet.GetSizeT()
        self.vdataset_nx = self.vDataSet.GetSizeX()
        self.vdataset_ny = self.vDataSet.GetSizeY()
        self.vdataset_nz = self.vDataSet.GetSizeZ()
        self.vdataset_nc = self.vDataSet.GetSizeC()

        vdataset_resx = float(self.vDataSet.GetExtendMaxX()) / self.vdataset_nx
        vdataset_resy = float(self.vDataSet.GetExtendMaxY()) / self.vdataset_ny
        vdataset_resz = float(self.vDataSet.GetExtendMaxZ()) / self.vdataset_nz

        #For now, only save the parameters for the current channel. When changing channel, this data is erased.
        self.arrayvar_last = None
        self.InitDialog()

    def InitDialog(self):
        #Build the dialog
        self.Dialog=CalculatorDialog.Dialog()
        self.Dialog.set_icon(BridgeLib.GetIcon())

        self.Dialog.ExitOK = self.ExitOK
        self.Dialog.ExitCancel = self.ExitCancel
        self.Dialog.Update = self.Update
        self.Dialog.Preview = self.Preview
        self.Dialog.Calculate = self.Calculate

        nc = self.vdataset_nc
        self.names = []
        self.indexes = []
        self.indexdic = {}
        self.operation_data = {}

        for i in range(nc):
            cname = self.vDataSet.GetChannelName(i)
            if ' (masked)' in cname:
                continue
            elif cname == '' or cname == '(name not specified)':
                cname = 'Channel %d' % (i+1)
                self.vDataSet.SetChannelName(i,cname)
            self.names.append(cname)
            self.indexes.append(i)
            self.indexdic[cname] = i

        self.current_tp = self.vImaris.GetVisibleIndexT()
        self.Dialog.SetChannels(self.names)# ,current_chan_a, current_chan_b)

        #Check if we already have an output channel and if json info is contained in the description
        output_channel = self.GetOutputChannel()
        self.SetThresholdScales(output_channel)

        json = BridgeLib.GetChannelDescription(self.vDataSet, output_channel)
        if json != "":
            self.Dialog.arrayvar.set_json(json)

        self.Dialog.mainloop()


    def SetThresholdScales(self,channel=None):
        #The threshold values
        if type(channel) == tuple or type(channel) == list:
            michan = channel[0]
            machan = channel[1]
        else:
            if channel is None or channel < 0:
                channel = self.Dialog.arrayvar["chana_input"]

            michan = self.vDataSet.GetChannelRangeMin(channel)
            machan = self.vDataSet.GetChannelRangeMax(channel)

        self.Dialog.ctrl_lothresh.config(from_=michan, to=machan,tickinterval=(machan-michan)/8.)
        self.Dialog.ctrl_hithresh.config(from_=michan, to=machan,tickinterval=(machan-michan)/8.)

        self.Dialog.arrayvar["lothresh"] =michan 
        self.Dialog.arrayvar["hithresh"] = machan

    def GetUpdated(self,old,new):
        """Check which parameters have changed between old and new dic"""
        return [x for x in set(old) & set(new) if old[x] != new[x]]

    def Update(self, arrayvar, elementname):
        '''Show the new value in a label'''

        #Do we need to preview?
        if (arrayvar["check_liveview"] == "on"):
            self.Preview()

    def GetOutputChannel(self,match="(calc)",create=False):
        """Finds the output channel for this plugin.
        If none found, this method will create a new channel and return its new index
        In any case, channel name reflects channels and operation"""

        arrayvar = self.Dialog.arrayvar.get()

        ret = -1
        nc = self.vDataSet.GetSizeC()
        for i in range(nc):
            name = self.vDataSet.GetChannelName(i)
            if match in name:
                ret = i
                break

        if ret == -1 and create == True:
            self.vDataSet.SetSizeC(nc+1)
            ret = nc

            current_chan_a = self.Dialog.arrayvar["chana_input"]
            current_chan_b = self.Dialog.arrayvar["chanb_input"]

            try:
                current_chan_a = self.indexdic[current_chan_a]
                current_chan_b = self.indexdic[current_chan_b]
            except:
                print "channels A or B not available?"
            else:
                rgba = self.vDataSet.GetChannelColorRGBA(current_chan_a)
                self.vDataSet.SetChannelColorRGBA(ret,rgba)

            check_inverta = (arrayvar["check_inverta"] == "on")
            check_invertb = (arrayvar["check_invertb"] == "on")

            cname_a = self.vDataSet.GetChannelName(current_chan_a)
            cname_b = self.vDataSet.GetChannelName(current_chan_b)

            if check_inverta:
                cname_a = "!"+cname_a

            if check_invertb:
                cname_b = "!"+cname_b

            operation_name = arrayvar["operation_type"]
            self.vDataSet.SetChannelName(ret,"%s(%s,%s) %s" % (operation_name,cname_a,cname_b,match))

        return ret

    def Calculate(self,preview=False):
        """Bulk of the calculation
        preview: current timepoint, otherwise, calculate all
        when applying threshold: In preview, will leave visibility alone
        otherwise, turn visibility off during data transfer to Imaris (faster)
        """

        update_operation = False

        #Check between last and current, what actually needs recomputing.
        arrayvar = self.Dialog.arrayvar.get()
        lothresh = float(arrayvar["lothresh"])
        hithresh = float(arrayvar["hithresh"])
        check_inverta = (arrayvar["check_inverta"] == "on")
        check_invertb = (arrayvar["check_invertb"] == "on")
        check_threshold = (arrayvar["check_threshold"] == "on")
        check_normalise = (arrayvar["check_normalise"] == "on")

        current_chan_a = self.indexdic[arrayvar["chana_input"]]
        current_chan_b = self.indexdic[arrayvar["chanb_input"]]

        try:
            factor_a = float(arrayvar["factor_a"])
        except:
            factor_a = 1.0

        try:
            factor_b = float(arrayvar["factor_b"])
        except:
            factor_b = 1.0

        current_tp = self.vImaris.GetVisibleIndexT()

        operation_type = CalculatorDialog.list_operations.index(arrayvar["operation_type"])

        nt = self.vdataset_nt
        nx = self.vdataset_nx
        ny = self.vdataset_ny
        nz = self.vdataset_nz
        nc = self.vdataset_nc

        #Two things we need to check. Do we need to update both operation and threshold
        #Do we need to do one time point or all.

        #This is a sure sign that we have NOT done any calculations yet
        if self.arrayvar_last is None:
            update_operation = True
        else:
            changed = set(self.GetUpdated(self.arrayvar_last, arrayvar))
            if set(["factor_a","factor_b","operation_type","chana_input","chanb_input","check_inverta", "check_invertb"]) & changed:
                update_operation = True

        #Now, this is where we define what timepoints need updating. That depends on preview (single timepoint)
        #Updating the preview keyword makes sure we only process one timepoint in preview
        #... then process all the timepoints the second time round
        if preview:
            arrayvar["preview"] = True
            tps = [current_tp]
            if self.current_tp != current_tp:
                self.current_tp = current_tp
                if not current_tp in self.operation_data.keys():
                    update_operation = True
        else:
            arrayvar["preview"] = False
            tps = range(nt)
            for tp in tps:
                 if not tp in self.operation_data.keys():
                     update_operation = True
                     break

        #The output channel is created if needed. In any case, the name will be updated (if needed)
        channel_out = self.GetOutputChannel(create=True)

        #Update the channel description...
        print "Updating?"
        BridgeLib.SetChannelDescription(self.vDataSet,channel_out,self.Dialog.arrayvar.get_json())

        if preview == False:
            channel_visibility = []
            for i in range(nc):
                channel_visibility.append(self.vImaris.GetChannelVisibility(i))
                self.vImaris.SetChannelVisibility(i,0)

        michan,machan = BridgeLib.GetRange(self.vDataSet)

        n_ops = len(tps)
        i = 0
        ############################################################
        # Update the operation if needed
        ############################################################
        if update_operation:
            n_ops *= 2
            #For each timepoint... First create the mask... then apply the mask to all the channels
            miarr,maarr = None, None

            mitp = None
            matp = None
            for tp in tps:
                if nz == 1:
                    array_a = BridgeLib.GetDataSlice(self.vDataSet,0,current_chan_a,tp).astype(float)
                    array_b = BridgeLib.GetDataSlice(self.vDataSet,0,current_chan_b,tp).astype(float)
                else:
                    array_a = BridgeLib.GetDataVolume(self.vDataSet,current_chan_a,tp).astype(float)
                    array_b = BridgeLib.GetDataVolume(self.vDataSet,current_chan_b,tp).astype(float)

                if check_inverta:
                    array_a = machan - array_a

                if check_invertb:
                    array_b = machan - array_b

                array_a = array_a * factor_a
                array_b = array_b * factor_b

                if operation_type == 0: #Add
                    array_op = array_a + array_b
                elif operation_type == 1: #Subtract
                    array_op = array_a - array_b
                elif operation_type == 2: #Multiply
                    array_op = array_a * array_b
                elif operation_type == 3: #Divide
                    array_op = array_a / array_b
                else:
                    array_op = np.zeros(array_a.shape)

                #record the current operation data

                array_op[array_op == np.inf] = michan
                array_op[np.isnan(array_op)] = michan
                array_op[array_op < michan] = michan
                array_op[array_op > machan] = machan
                self.operation_data[tp] = array_op
                mi = np.min(array_op)
                ma = np.max(array_op)
                if mitp is None:
                    mitp = mi
                    matp = ma
                elif mi < mitp:
                    mitp = mi
                elif ma > matp:
                    matp = ma

                #Update the progress bar
                i+=1
                self.Dialog.ctrl_progress["value"]=(100.*i)/n_ops
                self.Dialog.ctrl_progress.update()

            self.SetThresholdScales([mitp,matp])

        #apply any threshold and get the data back to imaris
        for tp in tps:
            array_op = self.operation_data[tp].copy()
            miarr = array_op.min()
            maarr = array_op.max()

            #do threshold
            if check_threshold:
                mi, ma = lothresh, hithresh
            else:
                mi, ma = miarr, maarr

            if mi == ma:
                if miarr != maarr:
                    ma = mi + (maarr-miarr)/100.
                else:
                    ma = mi+1

            if check_normalise:
                #when normalising, this isn't an issue as normalisation occurs after clipping.
                array_op[array_op < mi] = mi
                array_op[array_op > ma] = ma
            else:
                #Here, we are not normalising so values below the minimum value mi should be set to 0 rather than the mi value...
                #unless mi is itself below 0 (although that would be an odd thing to do, but still need to be accounted for).
                if mi < 0:
                    zeromi = mi
                else:
                    zeromi = 0

                array_op[array_op < mi] = zeromi
                array_op[array_op > ma] = ma

            #do normalisation
            if check_normalise:
                mi = np.min(array_op)
                ma = np.max(array_op)
                array_op = (machan-michan)*(array_op-mi)/(ma-mi)+michan

            #convert the data back to the original format...
            array_op = array_op.astype(BridgeLib.GetType(self.vDataSet))

            #push back
            if nz == 1:
                BridgeLib.SetDataSlice(self.vDataSet,array_op,0,channel_out,tp)
            else:
                BridgeLib.SetDataVolume(self.vDataSet,array_op,channel_out,tp)

            #Update the progress bar
            i+=1
            self.Dialog.ctrl_progress["value"]=(100.*i)/n_ops
            self.Dialog.ctrl_progress.update()

        if preview == False:
            for i in range(nc):
                self.vImaris.SetChannelVisibility(i,channel_visibility[i])

        #Keeping the arrayvar values
        self.arrayvar_last = arrayvar
        self.Dialog.ctrl_progress["value"]=0.
        self.vImaris.SetDataSet(self.vDataSet)

    def Preview(self):
        self.Calculate(preview=True)

    def ExitOK(self):
        '''OK button action'''
        self.Dialog.destroy()
        exit(0)

    def ExitCancel(self):
        '''Cancel button action'''
        self.Dialog.destroy()
        exit(0)

def XTCalculator(aImarisId):
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

    aModule = MyModule(vImaris)


