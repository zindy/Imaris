# -*- coding: utf-8 -*-
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

import Tkinter as tk
import ttk
from TkDialog import TkDialog

#Feel free to add more!
list_operations = ["Add","Subtract", "Multiply", "Divide"]

###########################################################################
## The dialog
###########################################################################
class Dialog(TkDialog):
    def __init__(self):
        TkDialog.__init__(self)

        #Here you can make things pretty
        self.arraychannel = None

        self.wm_geometry("500x470")
        self.title("Channel Calculator XTension - Copyright (c) 2015 Egor Zindy")

        widget = [ttk.Combobox(self.mainframe, textvariable=self.arrayvar("chana_input"), values=[], exportselection=0, state="readonly"),
                ttk.Entry(self.mainframe,textvariable=self.arrayvar("factor_a"))]
        tick  = (self.arrayvar("check_inverta", "off"),"Invert channel")
        tooltip = "Select a channel and a scaling coefficient."
        tooltip1 = "Click to invert the channel."
        self.add_control("Channel A times",widget, tick=tick, tooltip=tooltip, tooltip1=tooltip1)

        widget = [ttk.Combobox(self.mainframe, textvariable=self.arrayvar("chanb_input"), values=[], exportselection=0, state="readonly"),
                ttk.Entry(self.mainframe,textvariable=self.arrayvar("factor_b"))]
        tick  = (self.arrayvar("check_invertb", "off"),"Invert channel")
        tooltip = "Select a channel and a scaling coefficient."
        tooltip1 = "Click to invert the channel."
        self.add_control("Channel B times",widget, tick=tick, tooltip=tooltip, tooltip1=tooltip1)

        widget = ttk.Combobox(self.mainframe, textvariable=self.arrayvar("operation_type"), values=list_operations, exportselection=0, state="readonly")
        tooltip = "Choose an operation to perform on Channel A and Channel B"
        self.add_control("Operation",widget, name="ctrl_operations", tooltip=tooltip)

        widget = ttk.Checkbutton(self.mainframe, variable=self.arrayvar("check_threshold","off"), text="(click to activate)", onvalue="on", offvalue="off")
        tooltip = "Check this box to use the sliders below to clip the low / high pixel intensity values of the resulting image.\nIn Threshold only (no normalisation) mode, pixels whose intensity is below the minimum threshold are set to 0."
        self.add_control("Threshold output", widget, tooltip=tooltip)

        widget = ttk.Checkbutton(self.mainframe, variable=self.arrayvar("check_normalise","on"), text="(click to activate)", onvalue="on", offvalue="off")
        tooltip = "Normalising the operational output image scales its intensity range to that of the input images.\nFor example, if the input images are 16 bits, the normalised output image range will span 0 to 65535.\nFor quantitative comparisons where pixel intensity is important, you will want to work with non-normalised images."
        self.add_control("Normalise output", widget, tooltip=tooltip)

        widget = tk.Scale(self.mainframe, variable=self.arrayvar("lothresh"), from_=0., to=255., resolution=0.5, tickinterval=25., orient="horizontal", showvalue=True)
        tooltip = "This threshold clips low intensity / negative intensity pixels."
        self.add_control("Threshold min", widget, name="ctrl_lothresh", tooltip=tooltip)

        widget = tk.Scale(self.mainframe, variable=self.arrayvar("hithresh"), from_=0., to=255., resolution=0.5, tickinterval=25., orient="horizontal", showvalue=True)
        tooltip = "This threshold clips high intensity pixels."
        self.add_control("Threshold max", widget, name="ctrl_hithresh", tooltip=tooltip)
        widget = ttk.Button(self.mainframe, text="Preview operation at current timepoint", command=self.OnPreview, name="btn1")
        tooltip = "Click preview to check your operation on a single timepoint."
        self.add_control("Preview",widget, tooltip=tooltip)

        widget = ttk.Button(self.mainframe, text="Apply operation to all timepoints", command=self.OnCalculate, name="btn2")
        tooltip = "Click this to apply the operation for every timepoint in your image/volume timelapse (this may take sone time)."
        self.add_control("Apply",widget, tooltip=tooltip)

        widget = ttk.Progressbar(self.mainframe, variable=self.arrayvar("progress"), maximum=100, mode='determinate', orient="horizontal")
        self.add_control("Progress",widget, name="ctrl_progress")

        #we have all the ingredients, now bake the dialog box!
        self.bake(has_live=True, has_cancel=False) #, has_preview=True) #"Calculate")

    def SetDefaults(self):
        #Here you set default values
        self.arrayvar["lothresh"] = 0
        self.arrayvar["hithresh"] = 255
        self.arrayvar["factor_a"] = "1.0"
        self.arrayvar["factor_b"] = "1.0"
        self.arrayvar["operation_type"] = list_operations[0]
        self.ctrl_progress["value"]=0
        #self.arrayvar["check_liveview"] = "on"

    def SetChannels(self, channel_list, chana=0, chanb=0):
        self.SetDefaults()

        n_channels = len(channel_list)
        self.chana_input['values'] = channel_list
        self.chana_input.current(chana)

        self.chanb_input['values'] = channel_list
        self.chanb_input.current(chanb)

    #This is specific to the dialog validation and update.
    #Additionally, the Validate and Update methods are also called.
    def _Validate(self, arrayvar, elementname):
        lothresh = float(arrayvar["lothresh"])
        hithresh = float(arrayvar["hithresh"])

        if elementname == "lothresh":
            if lothresh > hithresh:
                arrayvar["hithresh"] = lothresh 

        elif elementname == "hithresh":
            if hithresh < lothresh:
                arrayvar["lothresh"] = hithresh

    def _Update(self, arrayvar, elementname):
        if arrayvar[elementname] == 'None':
            return

    def OnCalculate(self,*args):
        '''Calculate button action'''
        self.Calculate()

    def Calculate(self,*args):
        print "calculating..."

if __name__ == "__main__":
    app=Dialog()
    app.mainloop()



