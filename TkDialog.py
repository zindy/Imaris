# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 Egor Zindy <egor.zindy@manchester.ac.uk>
#
# * ArrayElementVar and ArrayVar based on Bryan Oakley's code from
#     http://stackoverflow.com/questions/3876229/how-to-run-a-code-whenever-a-tkinter-widget-value-changes
# * clean() lambda from
#     https://stackoverflow.com/questions/3303312/how-do-i-convert-a-string-to-a-valid-variable-name-in-python
# * TooltipBase by Eli Bendersky <eliben@gmail.com>
#     https://hg.python.org/cpython/file/63a00d019bb2/Lib/idlelib/ToolTip.py
# * Icon as a zlib compressed base64 file inspired by
#     http://stackoverflow.com/questions/550050/removing-the-tk-icon-on-a-tkinter-window
# * Imaris icons used with permission from Bitplane
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
import tkMessageBox
import tkFileDialog
import traceback
import textwrap
import tempfile
import json
import os
import functools
import re

# tries to convert a string into a valid variable name
clean = lambda varStr: re.sub('\W|^(?=\d)','_', varStr)

# general purpose 'tooltip' routines - currently unused in idlefork
# (although the 'calltips' extension is partly based on this code)
# may be useful for some purposes in (or almost in ;) the current project scope
# Ideas gleaned from PySol
class ToolTipBase:
    def __init__(self, button):
        self.button = button
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self._id1 = self.button.bind("<Enter>", self.enter)
        self._id2 = self.button.bind("<Leave>", self.leave)
        self._id3 = self.button.bind("<ButtonPress>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.button.after(500, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.button.after_cancel(id)

    def showtip(self):
        if self.tipwindow:
            return
        # The tip window must be completely outside the button;
        # otherwise when the mouse enters the tip window we get
        # a leave event and it disappears, and then we get an enter
        # event and it reappears, and so on forever :-(
        x = self.button.winfo_rootx() + 20
        y = self.button.winfo_rooty() + self.button.winfo_height() + 1
        self.tipwindow = tw = tk.Toplevel(self.button)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        self.showcontents()

    def showcontents(self, text="Your text here"):
        # Override this in derived class
        label = tk.Label(self.tipwindow, text=text, justify=tk.LEFT,
                      background="#ffffe0", relief=tk.SOLID, borderwidth=1)
        label.pack() #fill='both', expand=True)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class ToolTip(ToolTipBase):

    def __init__(self, button, text, width=60):
        ToolTipBase.__init__(self, button)

        lines = text.splitlines()
        tt = []
        for t in lines:
            tt += textwrap.wrap(t, width=width)
        
        self.text = "\n".join(tt)

    def showcontents(self):
        ToolTipBase.showcontents(self, self.text)


class ListboxToolTip(ToolTipBase):

    def __init__(self, button, items):
        ToolTipBase.__init__(self, button)
        self.items = items

    def showcontents(self):
        listbox = tk.Listbox(self.tipwindow, background="#ffffe0",height=1)
        listbox.pack(fill='both', expand=True)
        for item in self.items:
            listbox.insert(tk.END, item)

#This is to embed matplotlib
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
    from matplotlib.figure import Figure
    import numpy as np

    hasMPL = True
except:
    hasMPL = False

class ArrayElementVar(tk.StringVar):
    '''A StringVar that represents an element of an array'''
    _default = ""

    def __init__(self, varname, elementname, master):
        #self._master = master
        self._tk = master.tk
        self._name = "%s(%s)" % (varname, elementname)
        self.set(self._default)

    def __del__(self):
        """Unset the variable in Tcl."""
        self._tk.globalunsetvar(self._name)

class ArrayVar(tk.Variable):
    '''A variable that works as a Tcl array variable'''

    _default = {}
    _elementvars = {}
    _is_enabled = False
    _callback = None

    def __init__(self,master):
        self._master=master
        tk.Variable.__init__(self,master)

    def __del__(self):
        self._tk.globalunsetvar(self._name)
        for elementvar in self._elementvars:
            del elementvar

    def __setitem__(self, elementname, value):
        self.disable_events()
        if elementname not in self._elementvars:
            v = ArrayElementVar(varname=self._name, elementname=elementname, master=self._master)
            self._elementvars[elementname] = v

        self._elementvars[elementname].set(value)
        self.enable_events()

    def __getitem__(self, name):
        if name in self._elementvars:
            return self._elementvars[name].get()
        return None

    def __call__(self, elementname, value=None):
        '''Create a new StringVar as an element in the array'''
        if elementname not in self._elementvars:
            v = ArrayElementVar(varname=self._name, elementname=elementname, master=self._master)
            self._elementvars[elementname] = v

            if value is not None:
                self._elementvars[elementname].set(value)

        return self._elementvars[elementname]

    def set(self, dictvalue):
        # this establishes the variable as an array 
        # as far as the Tcl interpreter is concerned
        self._master.eval("array set {%s} {}" % self._name) 

        for (k, v) in dictvalue.iteritems():
            self._tk.call("array","set",self._name, (k, v))

    def get(self):
        '''Return a dictionary that represents the Tcl array'''
        value = {}
        for (elementname, elementvar) in self._elementvars.iteritems():
            value[elementname] = elementvar.get()
        return value

    #These are for saving data in a human readable form
    def get_json(self, indent=2, separators=(',', ': '),exclude=[]):
        dic = self.get()
        for key in exclude:
            if key in dic.keys():
                dic.pop(key)
        return json.dumps(self.get(), sort_keys=True, indent=indent, separators=separators)

    def set_json(self,s,exclude=[]):
        exclude.append("menuitem")
        dic = json.loads(s)
        for key in exclude:
            if key in dic.keys():
                dic.pop(key)
        self.set(dic)

    def callback(self,function):
        '''Add a trace callback to watch for modifications'''
        self._callback = function
        self.enable_events()

    def disable_events(self):
        '''Disable update events'''
        if self._callback is not None and self._is_enabled is True:
            self.trace_vdelete("w",self._observer)
            self._is_enabled = False

    def enable_events(self):
        '''Enable update events'''
        if self._callback is not None and self._is_enabled is False:
            self._observer = self.trace_variable(mode="w",callback=self._callback)
            self._is_enabled = True

class TkDialog(tk.Tk):
    '''Example app that uses Tcl arrays'''

    def __init__(self,title=None):

        self._controlnames = []
        self._controls = {}
        self._parents = {}
        self._tickcontrols = {}
        self._labels = {}
        self._tooltips = {}
        self._menubar = None

        #if multiple widgets to put in the "centre" columns, then increase the span
        self._spanwidgets = 1

        #The temporary icon path
        self.icon_path = ""

        tk.Tk.__init__(self)
        self.protocol("WM_DELETE_WINDOW", self.OnCancel)

        content = ttk.Frame(self,name="dialog")
        content.pack(fill='both', expand=True)
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)

        self.mainframe = ttk.Frame(content, borderwidth=5)

        #Corrects for classic view in Windows 7.
        self.style = ttk.Style()
        self.style.map("TCombobox",
            selectbackground=[
                ('!readonly', '!focus', 'SystemWindow'),
                ('readonly', '!focus', 'SystemWindow'),
                ],
            fieldbackground=[
                ('readonly', 'focus', 'SystemHighlight'),
                ('readonly', 'SystemWindow')
                ],
            )

        if title != "":
            self.title(title)

        self.arrayvar = ArrayVar(self)

        #The grid
        self.mainframe.grid(column=0, row=0, columnspan=3, rowspan=2, sticky=(tk.N, tk.W, tk.E, tk.S))
        #self.mainframe.columnconfigure(1, weight=1)
        self.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _makename(self,widget):
        widget_type = widget.__class__.__name__.strip()
        i = 0
        while(1):
            widget_name = widget_type+str(i)
            if not widget_name in self._controlnames:
                break
            i+=1
        return widget_name

    def _addwidget(self,widget,name=None):
        if name is None:
            try:
                name=widget.cget("textvariable")[8:-1]
            except:
                if hasattr(widget,"winfo_name"): name = widget.winfo_name()

            if name == "": name = self._makename(widget)
            #print("*** name",name,widget.winfo_class())

        if name in self._controlnames:
            print("Warning: Name already defined '%s'" % name)

        setattr(self,name,widget)
        return name

    def add_menu(self,label,menu_array):
        if self._menubar is None:
            self._menubar = tk.Menu(self)
            self.config(menu=self._menubar)
            variable = self.arrayvar("menuitem")

        new_menu = tk.Menu(self._menubar,tearoff=0)
        for item in menu_array:
            if item == "|":
                new_menu.add_separator()
            elif item.startswith("1_") or item.startswith("0_"):
                if item.startswith("1"):
                    b = "on"
                else:
                    b = "off"

                item = item[2:]
                var_name = clean(clean(label)+"_"+clean(item))

                variable = self.arrayvar(var_name)
                self.arrayvar[var_name] = b
                new_menu.add_checkbutton(label=item,
                        onvalue="on", offvalue="off",
                        variable=variable,
                        command=functools.partial(self.OnMenu,label+"/"+item))
            else:
                #create a variable name based on the menu / item
                new_menu.add("command",label=item,
                        command=functools.partial(self.OnMenu,label+"/"+item)) #variable=self.arrayvar(varname))

        self._menubar.add_cascade(label=label, menu=new_menu)

    def OnMenu(self,item):
        self.arrayvar["menuitem"]=item
        self._Update(self.arrayvar,"menuitem")
        self.Update(self.arrayvar,"menuitem")

    def OnButton(self,name):
        self._Update(self.arrayvar,name)
        self.Update(self.arrayvar,name)

    def add_control(self,label="", widget=None, name=None, tick=None,row=None,tooltip=None,tooltip1=None):
        if widget is None:
            return

        #find the parent (to avoid [None,None,None,None,None] type lists)
        parent = None
        if type(widget) == list:
            for w in widget:
                if w is not None:
                    parent = w.nametowidget(w.winfo_parent())
                    break

            if parent == self.mainframe:
                parent = None
                if len(widget) > self._spanwidgets:
                    self._spanwidgets = len(widget)

            nw = len(widget)
            for i in range(nw):
                w = widget[i]
                if w is None:
                    continue

                name = self._addwidget(w)
                self._labels[name]=label
                        
        else:
            name = self._addwidget(widget,name)

        self._controlnames.append(name)
        self._controls[name]=widget
        self._parents[name]=parent
        self._labels[name]=label
        self._tooltips[name] = tooltip


        if tick is not None and (type(tick) == list or type(tick) == tuple):
            tickvariable, ticktext = tick
            tick = ttk.Checkbutton(self.mainframe, variable=tickvariable, text=ticktext, onvalue="on", offvalue="off")
            if tooltip1 is not None:
                tip = ToolTip(tick, tooltip1)

        self._tickcontrols[name]=tick

    def _bakewidget(self,widget,row,col,span=1):
        widget.grid(column=col, row=row,columnspan=span)
        padx,pady = 5,5
        if widget.winfo_class() == "Canvas":
            hasCanvas = True
            widget.grid_configure(sticky=(tk.N,tk.S,tk.E,tk.W))
            self.mainframe.rowconfigure(row, weight=1)
            padx,pady = 0,0
        else:
            hasCanvas = False
            widget.grid_configure(sticky=(tk.E,tk.W))
            if widget.winfo_class() == "Frame": padx,pady = 0,0
            if widget.winfo_class() == "TButton":
                #We want to use our Update method, so here's a chance to add a default callback
                if widget.cget("command") == "":
                    def callback():
                        #Recipe from https://stackoverflow.com/questions/41291779/how-to-get-widget-name-in-event
                        name = str(widget).split(".")[-1]
                        self.OnButton(name)
                    widget.configure(command=callback)

        widget.grid_configure(padx=padx,pady=pady)


        return hasCanvas

    def bake(self, has_cancel=False, has_live=None, has_preview=None, has_ok=False):
        '''Given a list of controls and labels, bake the dialog'''

        #adding the controls / labels to the mainframe
        n_widgets = len(self._controls)

        #If there's a Canvas, make that the expanding object. Otherwise the last row is.
        hasCanvas = 0

        # The central columns configurationuration
        for i in range(self._spanwidgets):
            self.mainframe.columnconfigure(i+1, weight=self._spanwidgets)

        for i in range(n_widgets):
            ctrl_name = self._controlnames[i]
            label = self._labels[ctrl_name]
            tooltip = self._tooltips[ctrl_name]

            #This is the span if no label, no tick:
            span = 2 + self._spanwidgets

            #The widget column. Set to 0 if no label...
            if label is not None:
                span -= 1
                if label.strip() != "":
                    l = ttk.Label(self.mainframe, text=label.strip()+' :')
                    l.grid(column=0, row=i, sticky=(tk.E,tk.W))
                    if tooltip is not None:
                        tip = ToolTip(l, tooltip)
                col_widget = 1
            else:
                col_widget = 0

            #Now add the widget
            widget = self._controls[ctrl_name]
            widget_parent = self._parents[ctrl_name]
            tickcontrol = self._tickcontrols[ctrl_name]

            if widget is None:
                continue

            #we need to add multiple widgets
            if type(widget) == list:
                nw = len(widget)
                if widget_parent == None:
                    if tickcontrol is None:
                        nw = nw - 1
                    total_span = self._spanwidgets
                    for j in range(nw):
                        w = widget[j]
                        if j == nw-1:
                            span = total_span
                        else:
                            span = 1
                        if w is not None:
                            hasCanvas += self._bakewidget(w,i,col_widget+j,span)
                        total_span -= 1
                else:
                    widget_parent.pack(side=tk.TOP, fill=tk.X, padx=0, pady=0)
                    
                    if tickcontrol is not None:
                        span -= 1
                    for j in range(nw):
                        w = widget[j]
                        if j < nw-1:
                            padx = (0,10)
                        else:
                            padx = 0
                        w.pack(side=tk.LEFT, expand=tk.YES, fill=tk.X,padx=padx)
                    hasCanvas += self._bakewidget(widget_parent,i,col_widget,span)
            else:
                if tickcontrol is not None:
                    span -= 1
                hasCanvas += self._bakewidget(widget,i,col_widget,span)

            #Now add the tick
            if tickcontrol is None and type(widget) == list:
                tickcontrol = widget[-1]

            if tickcontrol is not None and type(tickcontrol)!=int:
                tickcontrol.grid(column=1+self._spanwidgets, row=i,columnspan=1)
                tickcontrol.grid_configure(padx=0,pady=5)
                tickcontrol.grid_configure(sticky=(tk.W,tk.E))

        #Separator line (used to either pull the canvas down and / or push the OK/Cancel buttons to the bottom)
        if hasCanvas > 0:
            weight = 0
            sticky=(tk.S,tk.N,tk.E,tk.W)
        else:
            weight = 1
            sticky=(tk.S,tk.E,tk.W)

        if True in [has_preview, has_live, has_ok, has_cancel]:
            widget = ttk.Separator(self.mainframe, orient=tk.HORIZONTAL)
            widget.grid_configure(padx=0,pady=5)
            widget.grid(column=0, row=n_widgets, columnspan=self._spanwidgets+2, sticky=sticky)
            self.mainframe.rowconfigure(n_widgets, weight=weight)

            #live preview and Cancel/OK buttons
            if has_preview is not None and has_preview != False:
                if has_preview is True:
                    has_preview = "Preview"
                widget = ttk.Button(self.mainframe,text=has_preview, command=self.OnPreview)
                widget.grid(column=0, row=n_widgets+1, sticky=(tk.S,tk.W))

            elif has_live is not None and has_live != False:
                if has_live is True:
                    has_live = "Live"
                widget = ttk.Checkbutton(self.mainframe,text=has_live, variable=self.arrayvar("check_liveview"), onvalue="on", offvalue="off")
                widget.grid(column=0, row=n_widgets+1, sticky=(tk.S,tk.W), padx=0)

            if has_cancel:
                c = self._spanwidgets
                if has_ok == False:
                    c += 1

                widget = ttk.Button(self.mainframe,text="Cancel", command=self.OnCancel)
                widget.grid(column=c, row=n_widgets+1, sticky=(tk.S,tk.E))

            if has_ok:
                widget = ttk.Button(self.mainframe,text="OK", command=self.OnOK)
                widget.grid(column=self._spanwidgets+1, row=n_widgets+1, sticky=(tk.S,tk.E))

        #self.mainframe.rowconfigure(n_widgets+1, weight=0)

        self._old_arrayvar = self.arrayvar.get()
        widget_type = widget.__class__.__name__.strip()
        self.arrayvar.callback(self.OnTrace)

    def enable(self,varname,enable=True):
        if varname in self._controlnames:
            if enable == True or enable == "on":
                state = 'normal'
            else:
                state = 'disabled'

            control = self._controls[varname]
            if type(control) == list:
                for c in control:
                    c.config(state=state)
            else:
                control.config(state=state)
        else:
            print(self._controlnames)
            print("Warning: Cannot enable %s" % varname)

    def disable(self,varname,disable=True):
        if varname in self._controlnames:
            if disable == True or disable == "on":
                state = 'disabled'
            else:
                state = 'normal'

            control = self._controls[varname]
            if type(control) == list:
                for c in control:
                    c.config(state=state)
            else:
                control.config(state=state)
        else:
            print(self._controlnames)
            print("Warning: Cannot disable %s" % varname)

    #Get a dictionary of all the labels
    def get_labels(self):
        return self._labels

    #http://stackoverflow.com/questions/550050/removing-the-tk-icon-on-a-tkinter-window
    def set_icon(self,icon):
        #Unfortunately, we need to write this a temporary file which we can then set as the app icon...
        try:
            icon_file = tempfile.NamedTemporaryFile(delete=False)
            icon_file.write(icon)
            icon_file.close()
            self.icon_path = icon_file.name
        finally:
            if os.path.exists(self.icon_path):
                self.iconbitmap(default=self.icon_path)

    def _on_exit(self):
        self.Quit()

    def default_json(self):
        #get a default json name for that particular dialog.
        return self.__class__.__name__.lower().replace("dialog","")+".conf"

    def OnTrace(self, varname, elementname, mode):
        '''The callback for monitoring widget changes'''

        #print("Tracing...")
        arr = self.arrayvar.get()
        #print(arr)
        if self._old_arrayvar == arr:
            return

        #Validate the dialog then update
        self.arrayvar.disable_events()

        try:
            self._Validate(self.arrayvar,elementname)
            self.Validate(self.arrayvar,elementname)
            self._Update(self.arrayvar,elementname)
            self.Update(self.arrayvar,elementname)
        except Exception, e: 
            print(e)
            print(traceback.print_exc())

        self._old_arrayvar = arr
        self.arrayvar.enable_events()

    #def OnMenu(self,*args):
    #    self.Update(*args)

    def OnPreview(self,*args):
        '''Preview button action'''
        self.Preview()

    def OnOK(self,*args):
        '''OK button action'''
        self.ExitOK()

    def OnCancel(self,*args):
        '''Cancel button action'''
        self.ExitCancel()

    def Preview(self,*args):
        print("You pressed Preview!")

    def ExitOK(self):
        print("You pressed OK!")
        #call Quit() to close the window and delete the temporary icon if one was created
        self.Quit()

    def ExitCancel(self):
        print("You pressed Cancel!")
        #call Quit() to close the window and delete the temporary icon if one was created
        self.Quit()

    def _Validate(self, arrayvar, elementname):
        '''Validate the dialog'''

    def Validate(self, arrayvar, elementname):
        '''Validate the dialog'''

    #At a minimum, these are connected menu items and functions.
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

    def Update(self, arrayvar, elementname):
        '''Show the new value in a label'''
        s = "Update: %s changed; new value='%s'" % (elementname, arrayvar[elementname])
        print(s)

    def OpenConfig(self):
        if self.arrayvar["fn_json"] is None or self.arrayvar["fn_json"] == "":
            d,f = "",""
        else:
            d,f = os.path.split(self.arrayvar["fn_json"])

        file_path = tkFileDialog.askopenfilename(
                initialdir = d,
                initialfile = f,
                defaultextension=".conf", filetypes = [ 
                    ("Config file",'*.conf')],
                parent=self, title="Set parameters from a configuration file")

        if not os.path.exists(file_path):
            return

        self.arrayvar["fn_json"] = file_path

        s = open(file_path).read()
        try:
            self.arrayvar.set_json(s)
        except:
            tkMessageBox.showerror("Error", "Invalid configurationuration file")


    def SaveConfig(self):
        if self.arrayvar["fn_json"] == "":
            d,f = "",""
        else:
            d,f = os.path.split(self.arrayvar["fn_json"])

        file_path = tkFileDialog.asksaveasfilename(
                initialdir = d,
                initialfile = f,
                defaultextension=".conf", filetypes = [ 
                    ("Config file",'*.conf')],
                parent=self, title="Save the current settings")

        if file_path == "":
            return

        self.arrayvar["fn_json"] = file_path

        s = self.arrayvar.get_json()
        f = open(file_path,"w")
        f.write(s)
        f.close()

    def About(self):
        '''An about dialog'''
        tkMessageBox.showinfo("About TkDialog", "A (hopefully) simple prototype GUI builder\n\nEgor Zindy <egor.zindy@manchester.ac.uk>")

    def Quit(self):
        self.destroy()
        #This will remove the temporary icon file if one was created...
        if os.path.exists(self.icon_path):
            os.remove(self.icon_path)


class TestDialog(TkDialog):
    def __init__(self):
        TkDialog.__init__(self)

        #Here you can make things pretty
        self.wm_geometry("700x700")
        self.title("Test Tk/Ttk Dialog")

        #How you might add an icon...
        #self.wm_iconbitmap('./my_icon.ico')
        #Or use (with binary_string from decompressing say a base64 zlib compressed icon in a string.
        #self.set_icon(binary_string)

        #build a list of controls and labels

        #First, add a simple menu...
        #The options menu items are checkable. The variable associated with each menu item is the sanitized menu_name_menu_item
        self.add_menu("File",["Open configuration","Save configuration","|","Exit"])
        self.add_menu("Edit",["Copy","Paste"])
        self.add_menu("Options",["1_Option 1","0_Option 2","0_Option 3"])
        self.add_menu("Help",["About"])

        self.labelvar = tk.StringVar()
        self.labelvar.set("Click on a widget to see this message change. Mouse-over the label to see a tooltip")
        # in some cases, it can be advantageous to name the widget via the "name" argument.
        # This widget will then be available through TestDialog.name
        # In most cases though, you only need to specify an arrayvar variable and the arrayvar name will be used instead
        widget = ttk.Label(self.mainframe,textvariable=self.labelvar,name="label1")
        tooltip = "The following message is changed in Update() in response to any changes to the UI"
        self.add_control("Info",widget,tooltip=tooltip)

        widget = [ttk.Radiobutton(self.mainframe, variable=self.arrayvar("radiobutton"), text="one", value=1),
                ttk.Radiobutton(self.mainframe, variable=self.arrayvar("radiobutton"), text="two", value=2),
                ttk.Radiobutton(self.mainframe, variable=self.arrayvar("radiobutton"), text="three", value=3),
                ttk.Radiobutton(self.mainframe, variable=self.arrayvar("radiobutton"), text="four", value=4)]
        self.add_control("Radio",widget)

        widget = [
                ttk.Checkbutton(self.mainframe, variable=self.arrayvar("checkbutton1"), text="Option 1",
                    onvalue="on", offvalue="off"),
                ttk.Checkbutton(self.mainframe, variable=self.arrayvar("checkbutton2"), text="Option 2",
                    onvalue="on", offvalue="off"),
                ttk.Checkbutton(self.mainframe, variable=self.arrayvar("checkbutton3"), text="Option 3",
                    onvalue="on", offvalue="off"),
                ]
        self.add_control("Checkbox",widget)

        widget = ttk.Entry(self.mainframe,textvariable=self.arrayvar("entry"))
        self.add_control("Entry",widget)

        if 1:
            #This is the safe way of doing this.
            row = self.mainframe
        else:
            #XXX Works in Windows for some reason, but really isn't advised. For instance, won't work in Linux.
            #As of Tkinter 8.5, we can't change the parent of a tk widget.
            #so (on Windows) we can define a ttk.Frame, then use it as a parent for more widgets
            row = ttk.Frame(self.mainframe)

        widget = [ttk.Entry(row,textvariable=self.arrayvar("entryx"),width=2),
                ttk.Entry(row,textvariable=self.arrayvar("entryy"),width=2),
                ttk.Entry(row,textvariable=self.arrayvar("entryz"),width=2)]
        tick = self.arrayvar("line_tick", "off"), "Click me"
        self.add_control("Multiple entries",widget,"linewidget",tick=tick)

        values = ["Value 1","Value 2"]
        widget = ttk.Combobox(self.mainframe, textvariable=self.arrayvar("combobox"), state="readonly", values=values)
        self.add_control("Combobox",widget)
        self.combobox_values = values

        widget = spinbox = tk.Spinbox(self.mainframe, textvariable=self.arrayvar("spinbox"), from_=1, to=11)
        tick = self.arrayvar("spinbox_tick", "off"), "Click me"
        self.add_control("Spinbox + tick",widget,tick=tick)

        # Here we need to specify a name to access via app("scale2") (for example, to enable/disable the widget)
        widget = tk.Scale(self.mainframe, variable=self.arrayvar("scale1"), from_ = 0, to=100, tickinterval=20, orient="horizontal", showvalue=True, name="scale1")
        self.add_control("Scale 0-100",widget)

        widget = tk.Scale(self.mainframe, variable=self.arrayvar("scale2"), from_ = 0, to=100, tickinterval=20, orient="horizontal", showvalue=True, name="scale2")
        tick = self.arrayvar("scale_tick", "on"), "Enabled"
        self.add_control("Scale + tick",widget,tick=tick)

        widget = ttk.Button(self.mainframe, text="click to display values array", command=self.OnDump)
        self.add_control("Button",widget)

        self.figure = Figure(figsize=(10,10), dpi=80)
        self.canvas = FigureCanvasTkAgg(self.figure,master=self.mainframe)
        self.add_control(None,self.canvas.get_tk_widget())
        if 0:
            #XXX This does not work in Mint 17
            self.toolbar = NavigationToolbar2TkAgg(self.canvas, self.mainframe) 
            self.add_control(None,self.toolbar)

        #we have all the ingredients, bake me a dialog box!
        self.bake(has_live=True,has_cancel=True)

        #Here you do the vars
        print("setting some values...")
        self.arrayvar["scale_tick"] = "on"
        self.arrayvar["spinbox_tick"] = "off"
        self.arrayvar["entry"] = "something witty"
        self.arrayvar["entryx"] = "1"
        self.arrayvar["entryy"] = "2"
        self.arrayvar["entryz"] = "3"
        self.arrayvar["radiobutton"] = 2
        self.arrayvar["checkbutton"] = "on"
        self.arrayvar["spinbox"] = 11
        self.arrayvar["combobox"] = self.combobox_values[0]

        ax1 = self.figure.add_axes([0.1, 0.1, 0.8, 0.8])
        t = np.arange(0.0, 2.0, 0.01)
        s = np.sin(2*np.pi*t)
        ax1.plot(t, s)

        ax1.set_xlabel('time (s)')
        ax1.set_ylabel('voltage (mV)')
        ax1.set_title('About as simple as it gets, folks')
        ax1.grid(True)

    def OnDump(self,*args):
        '''Print the contents of the array'''

        #This displays the array
        #print(self.arrayvar.get())

        #This displays the json values...
        print(self.arrayvar.get_json())

if __name__ == "__main__":
    #These functions sit outside the Test Dialog.
    #We can also use the _Update / _Validate methods which are "private" to the dialog class

    def Validate(arrayvar, elementname):
        print("Validating %s"%elementname)

        ####################################################
        #Showing how to enable / disable a widget when clicking on the tick
        if elementname == "scale_tick":
            if arrayvar[elementname] == "on":
                app.enable("scale2")
            else:
                app.disable("scale2")

        ####################################################
        #Showing how to link two scales.
        #I use this a lot for min/max threshold settings, e.g. contrast stretching.
        #Additionally, convert stored values to floating point
        lothresh = float(arrayvar["scale1"])
        hithresh = float(arrayvar["scale2"])

        if elementname == "scale1":
            arrayvar["scale1"] = lothresh
            if lothresh > hithresh:
                arrayvar["scale2"] = lothresh 

        elif elementname == "scale2":
            arrayvar["scale2"] = hithresh
            if hithresh < lothresh:
                arrayvar["scale1"] = hithresh
        #
        ####################################################

    def Update(arrayvar, elementname):
        '''Show the new value in a label'''
        s = "%s changed; new value='%s'" % (elementname, arrayvar[elementname])
        print(s)
        app.labelvar.set(s)

    app=TestDialog()

    # These steps customise the dialog further.
    #
    # Validate() is called first, this allows to change widgets relative to each other before calling Update()
    # Update() is then called when the various widgets are interacted with.
    # Actions on Exit or Cancel may be further customised through ExitOK() and ExitCancel()
    #app.Validate = Validate
    #app.Update = Update
    #app.ExitOK = ExitOK
    #app.ExitCancel = ExitCancel

    app.mainloop()

