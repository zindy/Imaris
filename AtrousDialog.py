# -*- coding: utf-8 -*-
# Copyright (C) 2014, Egor Zindy <egor.zindy@manchester.ac.uk>
# vim: set ts=4 sts=4 sw=4 expandtab smartindent:
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

import Tkinter as tk
import ttk
import tkMessageBox
from TkDialog import TkDialog

#It's convenient to make the combobox choices global lists.
n_channels = 3

###########################################################################
## The dialog
###########################################################################
class AtrousDialog(TkDialog):
    def __init__(self):
        TkDialog.__init__(self)

        #Here you can make things pretty
        self.arraychannel = None

        self.wm_geometry("510x510")
        self.title("Wavelet analysis for Imaris v1.0.1 - Copyright (c) 2014-2018 Egor Zindy")

        self.add_menu("File",["Open configuration","Save configuration","|","Exit"])
        self.add_menu("Help",["About"])

        widget = ttk.Combobox(self.mainframe, textvariable=self.arrayvar("channel"), values=[], exportselection=0, state="readonly")
        tick = (self.arrayvar("check_channel", "off"),"Apply to All")
        tooltip = "Select a channel to filter using Wavelet analysis. A new channel will be created for each filtered channel."
        tooltip1 = "It is probably best to work on one channel at a time.\nHowever, checking this box will apply the same parameters to all the dataset channels."
        self.add_control("Channel",widget, name="ctrl_channels", tick=tick, tooltip=tooltip, tooltip1=tooltip1)

        widget = ttk.Combobox(self.mainframe, textvariable=self.arrayvar("kernel_type"), values=[], exportselection=0, state="readonly")
        tick  = (self.arrayvar("check_invert", "off"),"Invert first")
        tooltip = "Choose the 3x3 kernel for filtering small features and the 5x5 kernel for filtering large features. The Gaussian 7x7 kernel is a new addition and seems to work better than the 3x3 for detecting small/fine objects."
        tooltip1 = "Wavelet analysis considers bright features on a dark background.\nIf your image consists of dark features on a bright background (e.g. a brightfield or phase contrast image), click this to invert your image."
        self.add_control("Filter type",widget, name="ctrl_filters", tick=tick, tooltip=tooltip, tooltip1=tooltip1)

        widget = tk.Scale(self.mainframe, variable=self.arrayvar("low_scale"), from_=1, to=10, tickinterval=1, orient="horizontal", showvalue=True)
        tooltip = "The first low number scale to allow through the filter.\nIf you have a noisy image, you may want to disregard scale 1 and possibly scale 2."
        self.add_control("Lower limit", widget, name="ctrl_low_scale", tooltip=tooltip)

        widget = tk.Scale(self.mainframe, variable=self.arrayvar("high_scale"), from_=1, to=10, tickinterval=1, orient="horizontal", showvalue=True)
        tooltip = "The largest number scale to allow through the filter. To create a band-pass filter, set this to be the same scale as the lower limit scale.\nFor example, to detect spots with diameters around the 16 to 20 pixel mark, try using the 3x3 kernel and set both lower and upper limits to 4."
        self.add_control("Upper limit", widget, name="ctrl_high_scale", tooltip=tooltip)

        widget1 = ttk.Checkbutton(self.mainframe, variable=self.arrayvar("check_threshold","on"), text="Threshold output", onvalue="on", offvalue="off")

        #widget = ttk.Checkbutton(self.mainframe, variable=self.arrayvar("check_delete","off"), text="(click to zero pixels above top threshold)", onvalue="on", offvalue="off")
        #tooltip = "The normal operation for pixels whose intensity is above the high threshold is to clip their intensity value to that of the high threshold. Checking this box will set their intensity to the minimum threshold value.\nThis can be interesting if high intensity objects need to be discarded from the filtered image."
        #self.add_control("Bright pixels", widget, tooltip=tooltip)

        widget2 = ttk.Checkbutton(self.mainframe, variable=self.arrayvar("check_normalise","on"), text="Normalise output", onvalue="on", offvalue="off")

        widget3 = ttk.Checkbutton(self.mainframe, variable=self.arrayvar("check_lowpass","off"), text="Residual low-pass", onvalue="on", offvalue="off")

        tooltip1 = "Check the threshold box to use the sliders below to clip the low / high pixel intensity values.\nIn Threshold only (no normalisation) mode, pixels whose intensity is below the minimum threshold are set to 0."
        tooltip2 = "Check the normalise box to scale the output intensity range to that of the input image.\nFor example, if the input image is 16 bits, the normalised output image range will span 0 to 65535.\nFor quantitative comparisons where pixel intensity is important, you will want to work with non-normalised images."
        tooltip3 = "Check the low pass residual box to add the residual low-pass filter to the output (generally not needed as you will most certainly try to remove the background)."

        self.add_control("Options", [widget1, widget2, widget3], tooltip=tooltip1+"\n"+tooltip2+"\n"+tooltip3)

        widget = tk.Scale(self.mainframe, variable=self.arrayvar("low_thresh"), from_=0., to=255., resolution=0.5, tickinterval=25., orient="horizontal", showvalue=True)
        tooltip = "This threshold clips low intensity / negative intensity pixels."
        self.add_control("Threshold min", widget, name="ctrl_low_thresh", tooltip=tooltip)

        widget = tk.Scale(self.mainframe, variable=self.arrayvar("high_thresh"), from_=0., to=255., resolution=0.5, tickinterval=25., orient="horizontal", showvalue=True)
        tooltip = "This threshold clips high intensity pixels."
        self.add_control("Threshold max", widget, name="ctrl_high_thresh", tooltip=tooltip)

        widget = ttk.Button(self.mainframe, text="Preview filtered data for current timepoint", command=self.OnPreview, name="btn1")
        tooltip = "Click preview to filter a data set for the current timepoint and display the filtered data in Imaris.\nFiltered data is cached so that calculations are performed unnecessarily. Also, click preview to update the filtered image's pixel intensity range."
        self.add_control("Preview",widget, tooltip=tooltip)

        widget = ttk.Button(self.mainframe, text="Apply filter to all timepoints", command=self.OnCalculate, name="btn2")
        tooltip = "Click this filter every timepoint in your image/volume timelapse (this may take sone time)."
        self.add_control("Apply",widget, tooltip=tooltip)

        widget = ttk.Progressbar(self.mainframe, variable=self.arrayvar("progress"), maximum=100, mode='determinate', orient="horizontal")
        self.add_control("Progress",widget, name="ctrl_progress")

        #we have all the ingredients, now bake the dialog box!
        self.bake(has_live=False, has_cancel=False) #, has_preview=True) #"Calculate")

        #self.SetDefaults()
        #self.SetChannels(["Red","Green","Blue"],1)

    def About(self):
        '''About XTAtrous'''
        tkMessageBox.showinfo("About XTAtrous", "\"A trous\" Wavelet analysis extension for Imaris\n\nPlease consider citing this software in your paper if you use it.\nSource code available from https://github.com/zindy/libatrous/\n\nAuthor: Egor Zindy <egor.zindy@manchester.ac.uk>\nWellcome Centre for Cell-Matrix Research")

    def SetDefaults(self):
        #Here you set default values
        self.arrayvar["low_scale"] = 1
        self.arrayvar["high_scale"] = 10
        self.arrayvar["low_thresh"] = 0
        self.arrayvar["high_thresh"] = 255
        self.ctrl_progress["value"]=0
        #self.arrayvar["check_liveview"] = "on"


    def SetKernels(self,kernel_list, index=0):
        self.ctrl_filters['values'] = kernel_list
        self.ctrl_filters.current(index)
        self.arrayvar["kernel_type"] = kernel_list[index]

    def SetChannels(self, channel_list, index=0):
        self.SetDefaults()

        n_channels = len(channel_list)
        self.ctrl_channels['values'] = channel_list
        self.ctrl_channels.current(index)
        #Here we save n_channel + 1 views in arraychannel. This is used to record a different set of parameters for all the channels.
        #Channels will start at 1, so we use 0 for the "apply to all the channels" settings.
        self.arraychannel = []
        self.arraychannel_last = []
        for index in range(n_channels+1):
            array = self.arrayvar.get()
            array.pop("channel")

            if index == 0:
                array["check_channel"] = "on"
            else:
                array["check_channel"] = "off"

            self.arraychannel.append(array)
            self.arraychannel_last.append(None)

    #This is specific to the dialog validation and update.
    #Additionally, the Validate and Update methods are also called.
    def _Validate(self, arrayvar, elementname):
        low_scale = int(arrayvar["low_scale"])
        high_scale = int(arrayvar["high_scale"])
        low_thresh = float(arrayvar["low_thresh"])
        high_thresh = float(arrayvar["high_thresh"])

        if elementname == "low_scale":
            if low_scale > high_scale:
                arrayvar["high_scale"] = low_scale 

        elif elementname == "high_scale":
            if high_scale < low_scale:
                arrayvar["low_scale"] = high_scale

        elif elementname == "low_thresh":
            if low_thresh > high_thresh:
                arrayvar["high_thresh"] = low_thresh 

        elif elementname == "high_thresh":
            if high_thresh < low_thresh:
                arrayvar["low_thresh"] = high_thresh

        elif elementname == "check_threshold":
            if arrayvar[elementname] == "on":
                #self.enable("check_delete")
                self.enable("ctrl_low_thresh")
                self.enable("ctrl_high_thresh")
            else:
                #self.disable("check_delete")
                self.disable("ctrl_low_thresh")
                self.disable("ctrl_high_thresh")

    def _Update(self, arrayvar, elementname):
        if arrayvar[elementname] == 'None':
            return

        if elementname == "menuitem":
            if arrayvar[elementname] == "File/Open configuration":
                self.OpenConfig()
            elif arrayvar[elementname] == "File/Save configuration":
                self.SaveConfig()
            elif arrayvar[elementname] == "File/Exit":
                self.Quit()
            elif arrayvar[elementname] == "Help/About":
                self.About()

        if elementname == "check_channel":
            if arrayvar[elementname] == "on":
                self.disable("ctrl_channels")
            else:
                self.enable("ctrl_channels")
                self.ctrl_channels["state"]="readonly"

        #have we changed the channels? Doesn't matter if the channels are not defined yet...
        if self.arraychannel is None:
            return

        channel = self.GetChannel()+1 #int(self.arrayvar["channel"])+1
        array = self.arrayvar.get()
        if self.arrayvar["check_channel"] == "on":
            channel = 0

        if elementname == "check_channel" or elementname == "channel":
            self.arrayvar.set(self.arraychannel[channel])
        else:
            self.arraychannel[channel] = array

    def GetChannel(self):
        return self.ctrl_channels.current()

    def GetFilter(self):
        return self.ctrl_filters.current()

    def OnCalculate(self,*args):
        '''Calculate button action'''
        self.Calculate()

    def Calculate(self,*args):
        print("calculating...")

if __name__ == "__main__":
    app=AtrousDialog()
    app.SetKernels(["Kernel 1", "Kernel 2", "Kernel 3"],0)
    app.SetChannels(["Channel 1", "Channel 2", "Channel 3"],0)
    app.mainloop()


