#
#
#  TrackPlot Python XTension  
#
#  Copyright (C) 2014, Egor Zindy <egor.zindy@manchester.ac.uk>
#  BSD-style copyright and disclaimer apply
#
#    <CustomTools>
#      <Menu name = "Python plugins">
#       <Item name="Track Plot" icon="Python" tooltip="Track plot (2D and 3D plots).">
#         <Command>PythonXT::XTTrackPlot(%i)</Command>
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


import matplotlib as mpl
from mpl_toolkits.mplot3d import Axes3D

import TrackPlotDialog
import Tkinter as tk
import tkFileDialog
import ttk

import ImarisLib
import BridgeLib

import time

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib.patheffects
import matplotlib.patches as patches
from mpl_toolkits.axes_grid1 import make_axes_locatable
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import numpy as np
import sys, traceback


###########################################################################
## Matplotlib centred spines
## http://stackoverflow.com/questions/4694478/center-origin-in-matplotlib
## Tried getting the emf format back into matplotlib. Loads missing (proper
## handling of linewidths, text centering, TeX support
###########################################################################
def center_spines(ax=None, centerx=0, centery=0,is_emf=False):
    """Centers the axis spines at <centerx, centery> on the axis "ax", and
    places arrows at the end of the axis spines."""
    if ax is None:
        ax = plt.gca()

    if is_emf:
        width_spine = 3
        width_major = 1
        width_minor = 0.1
    else:
        width_spine = 1.5
        width_major = 0.5
        width_minor = 0.1

    # Set the axis's spines to be centered at the given point
    # (Setting all 4 spines so that the tick marks go in both directions)
    #ax.spines['left'].set_position(('data', centerx))
    #ax.spines['bottom'].set_position(('data', centery))
    #ax.spines['right'].set_position(('data', centerx - 1))
    #ax.spines['top'].set_position(('data', centery - 1))
    ax.spines['left'].set_linewidth(width_spine)
    ax.spines['bottom'].set_linewidth(width_spine)
    ax.spines['right'].set_linewidth(width_spine)
    ax.spines['top'].set_linewidth(width_spine)

    # Draw an arrow at the end of the spines
    #ax.spines['left'].set_path_effects([EndArrow()])
    #ax.spines['bottom'].set_path_effects([EndArrow()])

    # Hide the line (but not ticks) for "extra" spines
    #for side in ['right', 'top']:
    #    ax.spines[side].set_color('none')

    # On both the x and y axes...
    for axis, center in zip([ax.xaxis, ax.yaxis], [centerx, centery]):
        # Turn on minor and major gridlines and ticks
        axis.set_ticks_position('both')
        axis.grid(True, 'major', ls='solid', lw=width_major, color='k')
        axis.grid(True, 'minor', ls='solid', lw=width_minor, color='k')
        axis.set_minor_locator(mpl.ticker.AutoMinorLocator())

        # Hide the ticklabels at <centerx, centery>
        #formatter = CenteredFormatter()
        #formatter.center = center
        #axis.set_major_formatter(formatter)

    # Add offset ticklabels at <centerx, centery> using annotation
    # (Should probably make these update when the plot is redrawn...)
    #xlabel, ylabel = map(formatter.format_data, [centerx, centery])
    #ax.annotate('(%s, %s)' % (xlabel, ylabel), (centerx, centery),
    #        xytext=(-4, -4), textcoords='offset points',
    #        ha='right', va='top')

    ax.axhline(linewidth=width_spine, color='k')
    ax.axvline(linewidth=width_spine, color='k')

def make_cross(ax,xlabel=None,ylabel=None,nbins=None):
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')
    ax.xaxis.set_ticks_position('bottom')
    ax.spines['bottom'].set_position(('data',0))
    ax.yaxis.set_ticks_position('left')
    ax.spines['left'].set_position(('data',0))
    ax.set_aspect('auto')
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)

    if nbins is not None:
        ax.locator_params(tight=True,nbins=nbins)
    #if ny is not None:
    #    ax.locator_params(nbins=ny)

# Note: I'm implementing the arrows as a path effect rather than a custom 
#       Spines class. In the long run, a custom Spines class would be a better
#       way to go. One of the side effects of this is that the arrows aren't
#       reversed when the axes are reversed!

class EndArrow(mpl.patheffects.AbstractPathEffect):
    """A matplotlib patheffect to add arrows at the end of a path."""
    def __init__(self, headwidth=5, headheight=5, facecolor=(0,0,0), **kwargs):
        super(mpl.patheffects.AbstractPathEffect, self).__init__()
        self.width, self.height = headwidth, headheight
        self._gc_args = kwargs
        self.facecolor = facecolor

        self.trans = mpl.transforms.Affine2D()

        self.arrowpath = mpl.path.Path(
                np.array([[-0.5, -0.2], [0.0, 0.0], [0.5, -0.2], 
                          [0.0, 1.0], [-0.5, -0.2]]),
                np.array([1, 2, 2, 2, 79]))

    def draw_path(self, renderer, gc, tpath, affine, rgbFace):
        scalex = renderer.points_to_pixels(self.width)
        scaley = renderer.points_to_pixels(self.height)

        x0, y0 = tpath.vertices[-1]
        dx, dy = tpath.vertices[-1] - tpath.vertices[-2]
        azi =  np.arctan2(dy, dx) - np.pi / 2.0 
        trans = affine + self.trans.clear(
                ).scale(scalex, scaley
                ).rotate(azi
                ).translate(x0, y0)

        gc0 = renderer.new_gc()
        gc0.copy_properties(gc)
        self._update_gc(gc0, self._gc_args)

        if self.facecolor is None:
            color = rgbFace
        else:
            color = self.facecolor

        renderer.draw_path(gc0, self.arrowpath, trans, color)
        renderer.draw_path(gc, tpath, affine, rgbFace)
        gc0.restore()

class CenteredFormatter(mpl.ticker.ScalarFormatter):
    """Acts exactly like the default Scalar Formatter, but yields an empty
    label for ticks at "center"."""
    center = 0
    def __call__(self, value, pos=None):
        if value == self.center:
            return ''
        else:
            return mpl.ticker.ScalarFormatter.__call__(self, value, pos)

def find_renderer(fig):
    if hasattr(fig.canvas, "get_renderer"):
        #Some backends, such as TkAgg, have the get_renderer method, which 
        #makes this easy.
        renderer = fig.canvas.get_renderer()
    else:
        #Other backends do not have the get_renderer method, so we have a work 
        #around to find the renderer.  Print the figure to a temporary file 
        #object, and then grab the renderer that was used.
        #(I stole this trick from the matplotlib backend_bases.py 
        #print_figure() method.)
        import io
        fig.canvas.print_pdf(io.BytesIO())
        renderer = fig._cachedRenderer
    return(renderer)

###########################################################################
## Main application module
###########################################################################
class MyModule:
    def __init__(self,vImaris):
        self.vImaris = vImaris
        self.vDataSet = vImaris.GetDataSet()
        self.object_names = []
        self.positions = None

        #the range values for all axis (will be set when needed)
        self._xrange = None
        self._yrange = None
        self._zrange = None

        #Get the voxel sizes...
        xsize,ysize,zsize = BridgeLib.GetVoxelSize(self.vDataSet)
        self._size = (xsize,ysize,zsize)
        nz = self.vDataSet.GetSizeZ()
        self.is3D = nz > 1

        self.InitDialog()

    def onHotswap(self):
        print "swap!"

    def InitDialog(self):
        #Build the dialog
        self.Dialog=TrackPlotDialog.TrackPlotDialog(self.is3D)

        self.Dialog.Save = self.SaveFigure
        self.Dialog.UpdateObjects = self.UpdateObjects
        self.arrayvar_last = []

        #Get the right icon...
        fn_icon = './icons/Imaris_128.ico'
        if "8." in self.vImaris.GetVersion(): fn_icon = './icons/Imaris8_128.ico'
        self.Dialog.wm_iconbitmap(fn_icon)

        self.Dialog.ExitOK = self.ExitOK
        self.Dialog.ExitCancel = self.ExitCancel
        self.Dialog.Update = self.Update

        self.UpdateObjects()
        self.Dialog.mainloop()

    def GetTrackIds(self,i=None,onlySelected=True):
        if i is None: i = self.current_object
        vSpot = self.SurpassObjects[self.object_names[i]]

        if onlySelected:
            sid = np.array(vSpot.GetSelectedIds())
            tid = sid[sid >= 1000000000]
        else:
            tid = np.array(vSpot.GetTrackIds())
            tid = np.unique(tid)

        return tid

    #return tracks and range for the given object.
    #If no object id given, then use currently selected
    #All the tracks or selected tracks...
    def GetSizeFactor(self,pixelSize=None):
        useDefault = (self.Dialog.arrayvar["check_defaultsize"] == "on")
        ret = 1.0,1.0,1.0
        if not useDefault or pixelSize is not None:
            _xsize,_ysize,_zsize = self._size[0], self._size[1], self._size[2]

            xs = self.Dialog.arrayvar["xsize"]
            ys = self.Dialog.arrayvar["ysize"]

            if self.is3D:
                zs = self.Dialog.arrayvar["zsize"]
            else:
                zs = "1.0"

            try:
                if pixelSize is None:
                    xf = float(xs) / _xsize
                    yf = float(ys) / _ysize
                    zf = float(zs) / _zsize
                else:
                    xf = pixelSize[0] / _xsize
                    yf = pixelSize[1] / _ysize
                    zf = 1
            except:
                print "Can't convert (%s,%s,%s) to float!" % (xs,ys,zs)
            else:
                ret = xf,yf,zf

        return ret

    #Take p, remove frame to frame mean for each timepoint then return p...
    def CorrectDrift(self,p,pe,tid,tpid,selection):
        tselect = np.unique(tpid)
        nt = tselect.shape[0]

        ret = p.copy()

        #make tables for pp and tt [label]
        pps = {}
        tts = {}
        idxs = {}
        for label in selection:
            wh = (tid == label )
            idx = pe[wh,:]
            idx = np.append(idx[:,0],idx[-1,1])
            #positions for the track...
            pp = p[idx,:]
            tt = tpid[idx]
            #timepoints for the track
            pps[label] = pp
            tts[label] = tt
            idxs[label] = idx

        #now check timepoint pairs.

        for i in range(nt-1):
            t0 = tselect[i]
            t1 = tselect[i+1]

            #looking for tracks with tpid t and tpid t+1
            nfound = 0
            meanval = np.zeros(3,'f')

            for label in selection:
                pp = pps[label]
                tt = tts[label]
                if not (t1 in tt and t0 in tt): continue

                i0 = np.where(tt==t0)[0][0]
                i1 = np.where(tt==t1)[0][0]

                newval = pp[i1,:]-pp[i0,:]
                meanval += pp[i1,:]-pp[i0,:]
                nfound+=1

            meanval /= nfound

            #print t0,t1,meanval,nfound
            for label in selection:
                idx = idxs[label]
                tt = tts[label]
                if not (t1 in tt and t0 in tt): continue
                i1 = np.where(tt==t1)[0][0]
                ret[idx[i1],:] -= meanval

        return ret

    def GetTracksAndRange(self,i=None,onlySelected=None,pixelSize=None):
        if i is None: i = self.current_object

        if onlySelected is None:
            onlySelected = (self.Dialog.arrayvar["check_selected"] == "on")

        xf,yf,zf = self.GetSizeFactor(pixelSize)
        vSpot = self.SurpassObjects[self.object_names[i]]

        if BridgeLib.isSpot(self.vImaris,vSpot):
            p = np.array(vSpot.GetPositionsXYZ())
            pe = np.array(vSpot.GetTrackEdges())
            tid = np.array(vSpot.GetTrackIds())
            tpid = np.array(vSpot.GetIndicesT())
        else:
            pe = np.array(vSpot.GetTrackEdges())
            tid = np.array(vSpot.GetTrackIds())
            n = vSpot.GetNumberOfSurfaces()
            p = np.zeros((n,3),float)
            tpid = np.zeros(n,int)

            for j in range(n):
                p[j,:] = vSpot.GetCenterOfMass(j)[0]
                tpid[j] = vSpot.GetTimeIndex(j)

        selection = self.GetTrackIds(i,onlySelected=onlySelected)
        if self.positions is None:
            self.positions = self.CorrectDrift(p,pe,tid,tpid,selection)

        
        p = self.positions * [xf,yf,zf]

        tracks = []
        xmi,ymi,zmi = None,None,None
        xma,yma,zma = None,None,None

        for label in selection:
            wh = (tid == label)
            idx = pe[wh,:]
            idx = np.append(idx[:,0],idx[-1,1])
            pp = p[idx,:]
            track = pp-pp[0]
            tracks.append(track)

            _xmi,_ymi,_zmi = np.min(track,axis=0)
            _xma,_yma,_zma = np.max(track,axis=0)

            if xmi is None or _xmi < xmi: xmi = _xmi
            if ymi is None or _ymi < ymi: ymi = _ymi
            if zmi is None or _zmi < zmi: zmi = _zmi
            if xma is None or _xma > xma: xma = _xma
            if yma is None or _yma > yma: yma = _yma
            if zma is None or _zma > zma: zma = _zma

        return tracks,(xmi,ymi,zmi),(xma,yma,zma)

    def GetUpdated(self,old,new):
        """Check which parameters have changed between old and new dic"""
        return [x for x in set(old) & set(new) if old[x] != new[x]]

    def Plot(self,fig,xr,yr,zr):
        plot_type = TrackPlotDialog.list_plots.index(self.Dialog.arrayvar["plot_type"])
        xmi,xma = xr
        ymi,yma = yr
        zmi,zma = zr

        for ax in fig.axes:
            fig.delaxes(ax)

        if self.is3D and plot_type == 0:
            #depending on the figure type...
            ax1 = fig.add_axes([0.1, 0.1, 0.85, 0.85],projection='3d')
            for track in self.tracks:
                t = track.copy()
                wh = np.bitwise_or(track[:,0] < xmi,track[:,0] > xma)
                t[wh,0]=np.nan
                wh = np.bitwise_or(track[:,1] < ymi,track[:,1] > yma)
                t[wh,1]=np.nan
                wh = np.bitwise_or(track[:,2] < zmi,track[:,2] > zma)
                t[wh,2]=np.nan
                ax1.plot(t[:,0],t[:,1],t[:,2],c='black')

                #ax1.plot(track[-1,0],track[-1,1],track[-1,2],'o',c='black')
            ax1.set_xlabel('X axis [$\mu$m]')
            ax1.set_ylabel('Y axis [$\mu$m]')
            ax1.set_zlabel('Z axis [$\mu$m]')
            print zmi,zma
            ax1.set_zlim(zmi,zma)
            ax1.set_ylim(ymi,yma)
            ax1.set_xlim(xmi,xma)
        elif self.is3D and plot_type == 1:
            #Projection plot
            ax1 = fig.add_axes([0.1, 0.1, 0.85, 0.85])
            ax1.set_aspect(1.)

            # create new axes on the right and on the top of the current axes
            # The first argument of the new_vertical(new_horizontal) method is
            # the height (width) of the axes to be created in inches.
            divider = make_axes_locatable(ax1)
            axXZ = divider.append_axes("top", 1.3, pad=0.2, sharex=ax1)
            axZY = divider.append_axes("right", 1.3, pad=0.2, sharey=ax1)

            for track in self.tracks:
                ax1.plot(track[:,0],track[:,1],c='black')
                ax1.plot(track[-1,0],track[-1,1],'o',c='black')
                axXZ.plot(track[:,0],track[:,2],c='black')
                axXZ.plot(track[-1,0],track[-1,2],'o',c='black')
                axZY.plot(track[:,2],track[:,1],c='black')
                axZY.plot(track[-1,2],track[-1,1],'o',c='black')
                max_ticks = 4
                loc = plt.MaxNLocator(max_ticks)
                axZY.xaxis.set_major_locator(loc)
                axXZ.yaxis.set_major_locator(loc)

            #make_cross(ax1,"X","Y",nbins=5)
            #make_cross(axXZ,"X","Z",nbins=5)
            #make_cross(axZY,"Z","Y",nbins=5)
            center_spines(ax1)
            center_spines(axXZ)
            center_spines(axZY)

            ax1.set_xlabel('X axis [$\mu$m]')
            ax1.set_ylabel('Y axis [$\mu$m]')

            #axXZ.set_xlabel('X axis [$\mu$m]')
            axXZ.set_ylabel('Z axis [$\mu$m]')

            axZY.set_xlabel('Z axis [$\mu$m]')
            #axZY.set_ylabel('Y axis [$\mu$m]')

            txt = axXZ.text(0.01, 0.97, 'Number of tracks: %d' % len(self.tracks), transform=axXZ.transAxes,fontsize=12,backgroundcolor='w')

            ax1.set_xlim(xmi,xma)
            ax1.set_ylim(ymi,yma)
            axXZ.set_xlim(xmi,xma)
            axXZ.set_ylim(zmi,zma)
            axZY.set_xlim(zmi,zma)
            axZY.set_ylim(ymi,yma)

        else:
            ax1 = fig.add_axes([0.1, 0.1, 0.85, 0.85])
            for track in self.tracks:
                ax1.plot(track[:,0],track[:,1],c='black')
                ax1.plot(track[-1,0],track[-1,1],'o',c='black')
            ax1.set_xlabel('X axis [$\mu$m]')
            ax1.set_ylabel('Y axis [$\mu$m]')
            txt = ax1.text(0.01, 0.97, 'Number of tracks: %d' % len(self.tracks), transform=ax1.transAxes,fontsize=12,backgroundcolor='w')
            #ax1.grid(True)
            ax1.set_ylim(ymi,yma)
            ax1.set_xlim(xmi,xma)
            center_spines(ax1)

        useTitle = (self.Dialog.arrayvar["check_title"] == "on")
        if useTitle: ax1.set_title(self.Dialog.arrayvar["title"],fontsize=24)

        #r = find_renderer(fig)
        #bbox = txt.get_window_extent(r)
        #rect = patches.Rectangle([bbox.x0, bbox.y0], bbox.width, bbox.height, color = [1,0,0], fill = False, transform=fig.transFigure)
        #fig.patches.append(rect)

        #print "min/max",xmi,xma,ymi,yma

        #ax1.set_axis('equal')
        self.Dialog.canvas.draw()

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

            #Reset sizes
            self.Dialog.arrayvar["xsize"] = self._size[0]
            self.Dialog.arrayvar["ysize"] = self._size[1]
            if self.is3D:
                self.Dialog.arrayvar["zsize"] = self._size[2]

        if update:
            self.Update(self.Dialog.arrayvar,"objects")

    def LoadSettings(self):
        self.Update(self.Dialog.arrayvar,"btn1")

    def SaveSettings(self):
        self.Update(self.Dialog.arrayvar,"btn2")

    def SaveFigure(self):
        self.Update(self.Dialog.arrayvar,"btn3")

    def Update(self, arrayvar, elementname):
        '''Updating everything...'''

        self.Dialog.config(cursor="wait")
        #changed = set(self.GetUpdated(self.arrayvar_last, arrayvar))
        replot = False

        fig = self.Dialog.figure

        if elementname == "btn3":
            file_path = tkFileDialog.asksaveasfilename(
                    defaultextension=".tif", filetypes = [ 
                        ("TIFF bitmap format",'*.tif'),
                        ("PDF vector format",'*.pdf'),
                        ("PNG bitmap format",'*.png'),
                        ("SVG vector format",'*.svg'),
                        ("EMF vector format",'*.emf'),
                        ("All image files",('*.tif','*.pdf','*.png','*.svg','*.emf'))],
                    parent=self.Dialog, title="Save a High Resolution Figure")

            if file_path == "":
                elementname = None
            else:
                fig = plt.figure(figsize=(10,10), dpi=100)

        useDefault = (self.Dialog.arrayvar["check_defaultsize"] == "on")
        useTitle = (self.Dialog.arrayvar["check_title"] == "on")

        if elementname == "objects":
            self.current_object = self.indexdic[arrayvar[elementname]]
            self.positions = None

        if elementname == "xsize" and not useDefault:
            xf,yf,zf = self.GetSizeFactor()
            try:
                xmi = float(self.Dialog.arrayvar["xmin"])*xf
                xma = float(self.Dialog.arrayvar["xmax"])*xf
            except:
                print "Exception in user code:"
                print '-'*60
                traceback.print_exc(file=sys.stdout)
                print '-'*60
            else:
                self.Dialog.arrayvar["xmin"] = xmi
                self.Dialog.arrayvar["xmax"] = xma
        elif elementname == "ysize" and not useDefault:
            xf,yf,zf = self.GetSizeFactor()
            try:
                ymi = float(self.Dialog.arrayvar["ymin"])*yf
                yma = float(self.Dialog.arrayvar["ymax"])*yf
            except:
                print "Exception in user code:"
                print '-'*60
                traceback.print_exc(file=sys.stdout)
                print '-'*60
            else:
                self.Dialog.arrayvar["ymin"] = ymi
                self.Dialog.arrayvar["ymax"] = yma
        elif elementname == "zsize" and not useDefault:
            xf,yf,zf = self.GetSizeFactor()
            try:
                zmi = float(self.Dialog.arrayvar["zmin"])*zf
                zma = float(self.Dialog.arrayvar["zmax"])*zf
            except:
                print "Exception in user code:"
                print '-'*60
                traceback.print_exc(file=sys.stdout)
                print '-'*60
            else:
                self.Dialog.arrayvar["zmin"] = zmi
                self.Dialog.arrayvar["zmax"] = zma

        if elementname == "objects" or elementname == "check_selected" or elementname == "check_defaultsize" or ((elementname == "xsize" or elementname == "ysize") and not useDefault) or elementname == "btn1":
            tracks,mi,ma = self.GetTracksAndRange()
            self.tracks = tracks
            if mi is None: mi,ma = (0,0,0), (1,1,1)
            self._range = (mi,ma)

            #set onbjects and select the current object
            if self.Dialog.arrayvar["xauto"] == "on":
                self.Dialog.arrayvar["xmin"] = mi[0]
                self.Dialog.arrayvar["xmax"] = ma[0]
            if self.Dialog.arrayvar["yauto"] == "on":
                self.Dialog.arrayvar["ymin"] = mi[1]
                self.Dialog.arrayvar["ymax"] = ma[1]
            if self.is3D and self.Dialog.arrayvar["zauto"] == "on":
                self.Dialog.arrayvar["zmin"] = mi[2]
                self.Dialog.arrayvar["zmax"] = ma[2]
            replot = True

        if elementname == "xauto":
            if self.Dialog.arrayvar["xauto"] == "on":
                self._xrange = [self.Dialog.arrayvar["xmin"],self.Dialog.arrayvar["xmax"],0]
                mi,ma = self._range
                self.Dialog.arrayvar["xmin"] = mi[0]
                self.Dialog.arrayvar["xmax"] = ma[0]
            else:
                if self._xrange is None:
                    self._xrange = [self.Dialog.arrayvar["xmin"],self.Dialog.arrayvar["xmax"],0]
                else:
                    self.Dialog.arrayvar["xmin"] = self._xrange[0]
                    self.Dialog.arrayvar["xmax"] = self._xrange[1]
            replot = True

        if elementname == "yauto":
            if self.Dialog.arrayvar["yauto"] == "on":
                self._yrange = [self.Dialog.arrayvar["ymin"],self.Dialog.arrayvar["ymax"],0]
                mi,ma = self._range
                self.Dialog.arrayvar["ymin"] = mi[1]
                self.Dialog.arrayvar["ymax"] = ma[1]
            else:
                if self._yrange is None:
                    self._yrange = [self.Dialog.arrayvar["ymin"],self.Dialog.arrayvar["ymax"],0]
                else:
                    self.Dialog.arrayvar["ymin"] = self._yrange[0]
                    self.Dialog.arrayvar["ymax"] = self._yrange[1]
            replot = True

        if elementname == "zauto":
            if self.Dialog.arrayvar["zauto"] == "on":
                self._zrange = [self.Dialog.arrayvar["zmin"],self.Dialog.arrayvar["zmax"],0]
                mi,ma = self._range
                self.Dialog.arrayvar["zmin"] = mi[2]
                self.Dialog.arrayvar["zmax"] = ma[2]
            else:
                if self._zrange is None:
                    self._zrange = [self.Dialog.arrayvar["zmin"],self.Dialog.arrayvar["zmax"],0]
                else:
                    self.Dialog.arrayvar["zmin"] = self._zrange[0]
                    self.Dialog.arrayvar["zmax"] = self._zrange[1]
            replot = True

        if (elementname == "xmin" or elementname == "xmax"):
            try:
                xmi = float(self.Dialog.arrayvar["xmin"])
                xma = float(self.Dialog.arrayvar["xmax"])
            except:
                #nothing to worry about, just use the old values
                xmi = self._range[0][0]
                xma = self._range[1][0]
            self._xrange = [xmi,xma]

            if self.Dialog.arrayvar["xauto"] == "off":
                replot = True

        if (elementname == "ymin" or elementname == "ymax"):
            try:
                ymi = float(self.Dialog.arrayvar["ymin"])
                yma = float(self.Dialog.arrayvar["ymax"])
            except:
                #nothing to worry about, just use the old values
                ymi = self._range[0][1]
                yma = self._range[1][1]
            self._yrange = [ymi,yma]

            if self.Dialog.arrayvar["yauto"] == "off":
                replot = True

        if (elementname == "zmin" or elementname == "zmax"):
            try:
                zmi = float(self.Dialog.arrayvar["zmin"])
                zma = float(self.Dialog.arrayvar["zmax"])
            except:
                #nothing to worry about, just use the old values
                zmi = self._range[0][2]
                zma = self._range[1][2]
            self._zrange = [zmi,zma]

            if self.Dialog.arrayvar["yauto"] == "off":
                replot = True

        print elementname
        if elementname == "plot_type":
            print "plot type has changed..."
            replot = True

        if elementname == "check_title" or (elementname == "title" and useTitle):
            print "title has changed..."
            replot = True

        if replot:
            print "replotting..."
            xmi = self._range[0][0]
            xma = self._range[1][0]
            ymi = self._range[0][1]
            yma = self._range[1][1]
            zmi = self._range[0][2]
            zma = self._range[1][2]

            if (self.Dialog.arrayvar["xauto"] == "off") and hasattr(self,"_xrange"):
                xmi = float(self._xrange[0])
                xma = float(self._xrange[1])
            if (self.Dialog.arrayvar["yauto"] == "off") and hasattr(self,"_yrange"):
                ymi = float(self._yrange[0])
                yma = float(self._yrange[1])
            if self.is3D and ((self.Dialog.arrayvar["zauto"] == "off") and hasattr(self,"_zrange")):
                zmi = float(self._zrange[0])
                zma = float(self._zrange[1])
            self.Plot(fig,[xmi,xma],[ymi,yma],[zmi,zma])

        if elementname == "btn1":
            fig.savefig(file_path, bbox_inches='tight')
            del fig

        self.arrayvar_last = arrayvar
        self.Dialog.config(cursor="")

    def ExitOK(self):
        '''OK button action'''
        self.Dialog.destroy()
        exit(0)

    def ExitCancel(self):
        '''Cancel button action'''
        self.Dialog.destroy()
        exit(0)

def XTTrackPlot(aImarisId):
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


