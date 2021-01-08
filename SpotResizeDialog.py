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
import tkMessageBox
from TkDialog import TkDialog

###########################################################################
## The dialog
###########################################################################
class Dialog(TkDialog):
    def __init__(self,is3D = False):
        TkDialog.__init__(self)

        #Here you can make things pretty
        self.arraychannel = None

        self.wm_geometry("600x120")
        self.title("Spot Resizer - Copyright (c) 2018 Egor Zindy")

        self.add_menu("File",["Update objects", "Open configuration", "Save configuration","|","Exit"])
        self.add_menu("Help",["About"])


        #widget = [ttk.Combobox(self.mainframe, textvariable=self.arrayvar("objects"), values=[], exportselection=0, state="readonly"),
        #        ttk.Combobox(self.mainframe, textvariable=self.arrayvar("cc_type"), values=list_colourcoding, exportselection=0, state="readonly")]
        #self.add_control("Object and coding",widget, "ctrl_objects")

        widget = ttk.Combobox(self.mainframe, textvariable=self.arrayvar("objects"), values=[], exportselection=0, state="readonly")
        self.add_control("Spot object",widget, name="ctrl_objects", tick=None)

        widget = [ttk.Entry(self.mainframe,textvariable=self.arrayvar("xsize")),
                ttk.Entry(self.mainframe,textvariable=self.arrayvar("ysize"))]
        label = "Spot um size X/Y"
        if is3D:
            widget.append( ttk.Entry(self.mainframe,textvariable=self.arrayvar("zsize")) )
            label +="/Z"

        self.add_control(label,widget,tick=None)

        widget = ttk.Button(self.mainframe, text="Apply", name="btn3")
        self.add_control("",widget)


        #we have all the ingredients, now bake the dialog box!
        self.bake(has_cancel=False) #, has_preview=True) #"Calculate")

    def About(self):
        '''About XTSpotSize'''
        tkMessageBox.showinfo("About XTSpotResize", "Source code available from https://github.com/zindy/Imaris/\n\nAuthor: Egor Zindy <egor.zindy@manchester.ac.uk>\nWellcome Centre for Cell-Matrix Research\nUniversity of Manchester (UK)")

    def SetDefaults(self):
        #Here you set default values
        #self.arrayvar["plot_type"] = list_plots[0]
        pass

    def SetObjects(self, object_list, selected=0):
        self.SetDefaults()

        n_objects = len(object_list)
        self.ctrl_objects['values'] = object_list
        self.ctrl_objects.current(selected)

    def OnSaveFigure(self,*args):
        self.SaveFigure()

    def SaveFigure(self):
        print "Saving the figure..."

if __name__ == "__main__":
    app=Dialog(is3D=True)
    app.mainloop()

