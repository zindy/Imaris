# -*- coding: utf-8 -*-
# Copyright (C) 2015, Egor Zindy <egor.zindy@manchester.ac.uk>
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
from TkDialog import TkDialog

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
    from matplotlib.figure import Figure
    import matplotlib as mpl
    mpl.use('TkAgg')
    import numpy as np
    hasMPL = True
except:
    hasMPL = False


#It's convenient to make the combobox choices global lists.
list_colourcoding = ["No colour coding","Start time","Length","Speed"]
list_plots = ["3D plot", "Projection"]

###########################################################################
## The dialog
###########################################################################
class TrackPlotDialog(TkDialog):
    def __init__(self,is3D = False):
        TkDialog.__init__(self)

        #Here you can make things pretty
        self.arraychannel = None

        self.wm_geometry("700x800")
        self.title("Tracks plotter - Copyright (c) 2015 Egor Zindy")

        #widget = [ttk.Combobox(self.mainframe, textvariable=self.arrayvar("objects"), values=[], exportselection=0, state="readonly"),
        #        ttk.Combobox(self.mainframe, textvariable=self.arrayvar("cc_type"), values=list_colourcoding, exportselection=0, state="readonly")]
        #self.add_control("Object and coding",widget, "ctrl_objects")

        widget = ttk.Combobox(self.mainframe, textvariable=self.arrayvar("objects"), values=[], exportselection=0, state="readonly")
        tick = self.arrayvar("check_selected", "off"), "Selected"
        self.add_control("Spot object",widget, name="ctrl_objects", tick=tick)
        widget = [ttk.Button(self.mainframe, text="Update objects", command=self.OnUpdateObjects, name="btn0"),
                ttk.Button(self.mainframe, text="Save settings", command=self.OnSaveSettings, name="btn1"),
                ttk.Button(self.mainframe, text="Load settings", command=self.OnLoadSettings, name="btn2")]
        self.add_control("",widget)

        if is3D:
            widget = ttk.Combobox(self.mainframe, textvariable=self.arrayvar("plot_type"), values=list_plots, exportselection=0, state="readonly")
            self.add_control("Plot type",widget, name="ctrl_plots", tick=tick)



        #widget = ttk.Combobox(self.mainframe, textvariable=self.arrayvar("cc_type"), values=list_colourcoding, exportselection=0, state="readonly")
        #self.add_control("Colour coding",widget, name="ctrl_colourcoding")

        widget = ttk.Entry(self.mainframe,textvariable=self.arrayvar("title"))
        tick = self.arrayvar("check_title", "off"), "Display"
        self.add_control("Title string",widget,tick=tick)

        if is3D:
            widget = [ttk.Entry(self.mainframe,textvariable=self.arrayvar("xsize")),
                    ttk.Entry(self.mainframe,textvariable=self.arrayvar("ysize")),
                    ttk.Entry(self.mainframe,textvariable=self.arrayvar("zsize"))]
            tick = self.arrayvar("check_defaultsize", "on"), "Default"
            self.add_control("Voxel um size X/Y/Z",widget,tick=tick)
        else:
            widget = [ttk.Entry(self.mainframe,textvariable=self.arrayvar("xsize")),
                    ttk.Entry(self.mainframe,textvariable=self.arrayvar("ysize"))]
            tick = self.arrayvar("check_defaultsize", "on"), "Default"
            self.add_control("Voxel um size X/Y",widget,tick=tick)

        widget = [ttk.Entry(self.mainframe,textvariable=self.arrayvar("xmin")),
                ttk.Entry(self.mainframe,textvariable=self.arrayvar("xmax"))]
        tick = self.arrayvar("xauto", "on"), "Auto"
        self.add_control("X range (min/max)",widget,tick=tick)

        widget = [ttk.Entry(self.mainframe,textvariable=self.arrayvar("ymin")),
                ttk.Entry(self.mainframe,textvariable=self.arrayvar("ymax"))]
        tick = self.arrayvar("yauto", "on"), "Auto"
        self.add_control("Y range (min/max)",widget,tick=tick)

        if is3D:
            widget = [ttk.Entry(self.mainframe,textvariable=self.arrayvar("zmin")),
                    ttk.Entry(self.mainframe,textvariable=self.arrayvar("zmax"))]
            tick = self.arrayvar("zauto", "on"), "Auto"
            self.add_control("Z range (min/max)",widget,tick=tick)

            widget = [ttk.Entry(self.mainframe,textvariable=self.arrayvar("azimuth")),
                    ttk.Entry(self.mainframe,textvariable=self.arrayvar("elevation"))]
            self.add_control("Azimuth / Elevation",widget) #,tick=tick)


        self.figure = Figure(figsize=(10,10), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure,master=self.mainframe)
        self.add_control("",self.canvas.get_tk_widget())
        #self.toolbar = NavigationToolbar2TkAgg(self.canvas, self.mainframe) 
        #self.add_control("",self.toolbar)

        widget = ttk.Button(self.mainframe, text="Save high resolution figure", command=self.OnSaveFigure, name="btn3")
        self.add_control("",widget)


        #we have all the ingredients, now bake the dialog box!
        self.bake(has_cancel=False) #, has_preview=True) #"Calculate")

    def SetDefaults(self):
        #Here you set default values
        self.arrayvar["cc_type"] = list_colourcoding[0]
        self.arrayvar["plot_type"] = list_plots[0]

    def SetObjects(self, object_list, selected=0):
        self.SetDefaults()

        n_objects = len(object_list)
        self.ctrl_objects['values'] = object_list
        self.ctrl_objects.current(selected)

    #This is specific to the dialog validation and update.
    #Additionally, the Validate and Update methods are also called.
    def _Validate(self, arrayvar, elementname):
        pass

    def _Update(self, arrayvar, elementname):
        if arrayvar[elementname] == 'None':
            return

    def OnLoadSettings(self,*args):
        self.LoadSettings()

    def LoadSettings(self):
        print "Loading some settings..."

    def OnSaveSettings(self,*args):
        self.SaveSettings()

    def SaveSettings(self):
        print "Saving some settings..."

    def OnSaveFigure(self,*args):
        self.SaveFigure()

    def SaveFigure(self):
        print "Saving the figure..."

    def OnUpdateObjects(self,*args):
        self.UpdateObjects(update=True)

    def UpdateObjects(self, *args, **kwargs):
        print "Updating the objects..."

if __name__ == "__main__":
    app=TrackPlotDialog(is3D=True)
    app.mainloop()



