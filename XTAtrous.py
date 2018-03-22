#
#
#  Atrous Python XTension  
#
#  Copyright (C) 2014 Egor Zindy <egor.zindy@manchester.ac.uk>, MIT license
#
#    <CustomTools>
#      <Menu name = "Python plugins">
#       <Item name="Wavelet analysis" icon="Python" tooltip="Wavelet analysis for Imaris (2D and 3D kernels).">
#         <Command>PythonXT::XTAtrous(%i)</Command>
#       </Item>
#      </Menu>
#    </CustomTools>
#
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.
#
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:

import hotswap
import AtrousDialog
import Tkinter as tk
import ttk

import ImarisLib
import BridgeLib

import time
import numpy as np
import libatrous

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

        resx, resy, resz = BridgeLib.GetVoxelSize(self.vDataSet)

        #Setting the grid resolution
        libatrous.set_grid(resx, resy, resz) 

        self.wavelet_data = None

        #For now, only save the parameters for the current channel. When changing channel, this data is erased.
        self.arrayvar_last = None

        self.InitDialog()

    def InitDialog(self):
        #Build the dialog
        self.Dialog=AtrousDialog.AtrousDialog()
        self.Dialog.set_icon(BridgeLib.GetIcon())

        #Get the right icon...
        fn_icon = './Imaris_128.ico'
        if '8.' in self.vImaris.GetVersion(): fn_icon = './Imaris8_128.ico'
        #self.Dialog.wm_iconbitmap(fn_icon)

        self.Dialog.ExitOK = self.ExitOK
        self.Dialog.ExitCancel = self.ExitCancel
        self.Dialog.Update = self.Update
        self.Dialog.Preview = self.Preview
        self.Dialog.Calculate = self.Calculate

        nc = self.vdataset_nc
        self.names = []
        self.indexes = []
        self.indexdic = {}

        for i in range(nc):
            cname = self.vDataSet.GetChannelName(i)
            if ' (filtered)' in cname:
                continue
            elif cname == '' or cname == '(name not specified)':
                cname = 'Channel %d' % (i+1)
                self.vDataSet.SetChannelName(i,cname)
            self.names.append(cname)
            self.indexes.append(i)
            self.indexdic[cname] = i

        self.current_channel = 0

        #Set filters and current filter
        self.Dialog.SetKernels(libatrous.get_names(),0)
        #Set channels and current channel
        self.Dialog.SetChannels(self.names,self.current_channel)
        #Threshold scale
        self.SetThresholdScales()

        self.Dialog.mainloop()

    def SetThresholdScales(self,channel=None):
        #The threshold values
        if channel is None:
            channel = self.current_channel

        michan = self.vDataSet.GetChannelRangeMin(channel)
        machan = self.vDataSet.GetChannelRangeMax(channel)
        self.Dialog.ctrl_low_thresh.config(from_=michan, to=machan,tickinterval=(machan-michan)/8.)
        self.Dialog.ctrl_high_thresh.config(from_=michan, to=machan,tickinterval=(machan-michan)/8.)

        self.Dialog.arrayvar["low_thresh"] =michan 
        self.Dialog.arrayvar["high_thresh"] = machan

    def GetUpdated(self,old,new):
        """Check which parameters have changed between old and new dic"""
        return [x for x in set(old) & set(new) if old[x] != new[x]]

    def Update(self, arrayvar, elementname):
        '''Show the new value in a label'''

        if elementname == "channel": 
            channel = self.indexdic[arrayvar[elementname]]
            self.current_channel = channel

            #Corresponding channel_out - Get any json information from its description
            #We do not want to create a new channel at this point
            channel_out = self.GetMatchedChannel(self.current_channel, create=False)
            if channel_out != -1:
                json = BridgeLib.GetChannelDescription(self.vDataSet,channel_out)
                if json != "":
                    self.Dialog.arrayvar.set_json(json)

            self.arrayvar_last = None

        elif elementname == "check_channel":
            self.arrayvar_last = None

        if 1:
            pass
            #any condition (for now)
            #channel_out = self.GetMatchedChannel(self.current_channel)
            #print("updating threshold",self.current_channel,channel_out,elementname)
            #self.SetThresholdScales(channel_out)

        #Do we need to preview?
        if (arrayvar["check_liveview"] == "on"):
            self.Preview()



    def GetMatchedChannel(self,cindex,create=True):
        """Finds the matched filtered channel for a particular channel index.
        If none found and the keyword create is set to true, this method will create a new channel and return its new index"""

        ret = -1
        cname = self.vDataSet.GetChannelName(cindex)
        nc = self.vDataSet.GetSizeC()
        for i in range(nc):
            name = self.vDataSet.GetChannelName(i)
            if name == cname+" (filtered)":
                ret = i
                break

        if create == True and ret == -1:
            self.vDataSet.SetSizeC(nc+1)
            ret = nc
            print(nc)
            self.vDataSet.SetChannelName(ret,cname+" (filtered)")
            rgba = self.vDataSet.GetChannelColorRGBA(cindex)
            #rgba = rgba ^ 0x00ffffff
            self.vDataSet.SetChannelColorRGBA(ret,rgba)

        return ret

    def Calculate(self,preview=False):
        """Bulk of the calculation
        preview: current timepoint, otherwise, calculate all
        when applying threshold: In preview, will leave visibility alone
        otherwise, turn visibility off during data transfer to Imaris (faster)
        """

        #Check between last and current, what actually needs recomputing.
        arrayvar = self.Dialog.arrayvar.get()
        list_filters = libatrous.get_names()
        kernel_type = list_filters.index(arrayvar["kernel_type"])
        kernel = libatrous.get_kernel(kernel_type)

        low_scale = int(arrayvar["low_scale"])
        high_scale = int(arrayvar["high_scale"])
        low_thresh = float(arrayvar["low_thresh"])
        high_thresh = float(arrayvar["high_thresh"])
        check_invert = (arrayvar["check_invert"] == "on")
        check_lowpass = (arrayvar["check_lowpass"] == "on")
        check_threshold = (arrayvar["check_threshold"] == "on")
        #check_delete = (arrayvar["check_delete"] == "on")
        check_normalise = (arrayvar["check_normalise"] == "on")
        check_delete = False

        #Two things we need to check. Do we need to update both wavelet and threshold
        #Do we need to do one time point or all.
        update_wavelet = False
        update_threshold = False

        #All the channels or just the current selected channel (from dropdown menu)
        if self.Dialog.arrayvar["check_channel"] == "on":
            channel_indexes = self.indexes
        else:
            channel_indexes = [self.current_channel]

        #This is a sure sign that we have NOT done any calculations yet
        if self.arrayvar_last is None:
            update_wavelet = True
            update_threshold = True
            self.wavelet_data = {}

        else:
            changed = set(self.GetUpdated(self.arrayvar_last, arrayvar))
            if set(["kernel_type", "check_invert", "check_lowpass", "low_scale", "high_scale"]) & changed:
                update_wavelet = True
                update_threshold = True
            #elif set(["low_thresh", "high_thresh", "check_threshold", "check_delete", "check_normalise"]) & changed:
            elif set(["low_thresh", "high_thresh", "check_threshold", "check_normalise"]) & changed:
                update_threshold = True

        #Do we need to update any of the wavelet data?
        for channel in channel_indexes:
            if channel not in self.wavelet_data.keys():
                tps = range(self.vdataset_nt)
                self.wavelet_data[channel] = [None]*self.vdataset_nt

        #Now, this is where we define what the timepoints are. That depends on preview (single timepoint)
        #Updating the preview keyword makes sure we only process one timepoint in preview
        #... then process all the timepoints the second time round
        if preview:
            arrayvar["preview"] = True
            tps = [self.vImaris.GetVisibleIndexT()]
        else:
            arrayvar["preview"] = False
            tps = range(self.vdataset_nt)

        if self.arrayvar_last is not None and self.arrayvar_last["preview"]==True and preview==False:
            update_wavelet = True
            update_threshold = True

        ############################################################
        # Update the wavelet if needed
        ############################################################
        if update_wavelet:
            miarr,maarr = None, None
            michan,machan = BridgeLib.GetRange(self.vDataSet)
            #michan = self.vDataSet.GetChannelRangeMin(channel)
            #machan = self.vDataSet.GetChannelRangeMax(channel)

            for channel in channel_indexes:
                for tp in tps:
                    if self.vdataset_nz == 1:
                        dataset = BridgeLib.GetDataSlice(self.vDataSet,0,channel,tp).astype(np.float32)
                    else:
                        dataset = BridgeLib.GetDataVolume(self.vDataSet,channel,tp).astype(np.float32)
                    if check_invert:
                        dataset = machan - dataset

                    atrous_sub = libatrous.get_bandpass(dataset,low_scale-1,high_scale-1,kernel,check_lowpass)
                    mi = np.min(atrous_sub)
                    ma = np.max(atrous_sub)

                    if miarr is None or mi < miarr:
                        miarr = mi
                    if maarr is None or ma > maarr:
                        maarr = ma

                    self.wavelet_data[channel][tp] = atrous_sub
                    self.Dialog.ctrl_progress["value"]=(100.*(tp/float(len(tps)*len(channel_indexes))))
                    self.Dialog.ctrl_progress.update()

            time.sleep(0.2)
            self.Dialog.ctrl_progress["value"]=0
            self.Dialog.ctrl_progress.update()

            self.Dialog.ctrl_low_thresh.config(from_=miarr, to=maarr,tickinterval=(maarr-miarr)/8.)
            self.Dialog.ctrl_high_thresh.config(from_=miarr, to=maarr,tickinterval=(maarr-miarr)/8.)

        ############################################################
        # Update the threshold if needed
        ############################################################
        if update_threshold:
            michan,machan = BridgeLib.GetRange(self.vDataSet)
            #michan = self.vDataSet.GetChannelRangeMin(channel)
            #machan = self.vDataSet.GetChannelRangeMax(channel)
            channel_visibility = []

            if preview == False:
                for i in range(nc):
                    channel_visibility.append(self.vImaris.GetChannelVisibility(i))
                    self.vImaris.SetChannelVisibility(i,0)

            i = 0
            for channel in channel_indexes:
                channel_out = self.GetMatchedChannel(channel)

                #Update the channel description...
                BridgeLib.SetChannelDescription(self.vDataSet,channel_out,self.Dialog.arrayvar.get_json())

                #michan = self.vDataSet.GetChannelRangeMin(channel)
                #machan = self.vDataSet.GetChannelRangeMax(channel)

                for tp in tps:
                    array_out  = self.wavelet_data[channel][tp].copy()
                    miarr = array_out.min()
                    maarr = array_out.max()

                    #do threshold
                    if check_threshold:
                        mi, ma = low_thresh, high_thresh
                    else:
                        mi, ma = miarr, maarr

                    if mi == ma:
                        ma = mi + (maarr-miarr)/100.

                    if check_delete:
                        pass
                        #array_out[array_out < mi] = mi
                        #deleting objects brighter than max value
                        #array_out[array_out > ma] = mi
                    else:
                        #we really don't want any hot background.
                        if check_normalise:
                            #when normalising, this isn't an issue as normalisation occurs after clipping.
                            array_out[array_out < mi] = mi
                        else:
                            #Here, we are not normalising so values below the minimum value mi should be set to 0 rather than the mi value...
                            #unless mi is itself below 0 (although that would be an odd thing to do, but still need to be accounted for).
                            if mi < 0:
                                zeromi = mi
                            else:
                                zeromi = 0

                            array_out[array_out < mi] = zeromi

                        array_out[array_out > ma] = ma

                    #do normalisation
                    if check_normalise:
                        mi = np.min(array_out)
                        ma = np.max(array_out)
                        array_out = (machan-michan)*(array_out-mi)/(ma-mi)+michan

                    #convert the data back to the original format...
                    array_out = array_out.astype(BridgeLib.GetType(self.vDataSet))

                    #push back
                    if self.vdataset_nz == 1:
                        BridgeLib.SetDataSlice(self.vDataSet,array_out,0,channel_out,tp)
                    else:
                        BridgeLib.SetDataVolume(self.vDataSet,array_out,channel_out,tp)
                    #self.vDataSet.SetChannelRange(channel_out,michan,machan)

                    self.Dialog.ctrl_progress["value"]=(100.*(tp/float(len(tps)*len(channel_indexes))))
                    self.Dialog.ctrl_progress.update()
                    self.vImaris.SetDataSet(self.vDataSet)

            if preview == False:
                for i in range(nc):
                    self.vImaris.SetChannelVisibility(i,channel_visibility[i])

            time.sleep(0.2)
            self.Dialog.ctrl_progress["value"]=0
            self.Dialog.ctrl_progress.update()

            #Keeping the arrayvar values
            self.arrayvar_last = arrayvar

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

def XTAtrous(aImarisId):
    # Create an ImarisLib object
    vImarisLib = ImarisLib.ImarisLib()

    # Get an imaris object with id aImarisId
    vImaris = vImarisLib.GetApplication(aImarisId)

    # Check if the object is valid
    if vImaris is None:
        print("Could not connect to Imaris!")
        exit(1)

    vDataSet = vImaris.GetDataSet()
    if vDataSet is None:
        print("No data available!")
        exit(1)

    #The hotswap module watcher...
    _watcher = hotswap.ModuleWatcher()
    _watcher.run()

    aModule = MyModule(vImaris)

