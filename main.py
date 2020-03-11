from __future__ import division
from __future__ import print_function


import numpy as np
from matplotlib import pyplot as plt
import matplotlib.patches as patches
import pydicom, os
from collections import Counter
import seaborn as sns
import pandas as pd

sns.set_palette("muted")

import cProfile, pstats
from io import StringIO

try:
    from tkinter import *
    from tkinter import ttk
except:
    from Tkinter import *
    import ttk
    import tkFileDialog as filedialog

from classes import *

Gy = 1
dGy = 0.1
cGy = 0.01
mGy = 0.001
cc = 0.001

PROGRAM_VERSION = 1.0

lineColors = ["orange", "red", "blue", 'darkgoldenrod', 'black', 'crimson']
fillColors = ["wheat",  "lightcoral", "lightblue", 'goldenrod', 'darkgray', 'pink']
lightFillColors = ["oldlace", "mistyrose", "lavender", 'gold', 'lightgray', 'lightpink']

"""
# Start profiling
pr = cProfile.Profile()
pr.enable()
"""

class Tooltip:
    '''
    It creates a tooltip for a given widget as the mouse goes on it.

    see:

    http://stackoverflow.com/questions/3221956/           what-is-the-simplest-way-to-make-tooltips-
           in-tkinter/36221216#36221216

    http://www.daniweb.com/programming/software-development/
           code/484591/a-tooltip-class-for-tkinter

    - Originally written by vegaseat on 2014.09.09.

    - Modified to include a delay time by Victor Zaccardo on 2016.03.25.

    - Modified
        - to correct extreme right and extreme bottom behavior,
        - to stay inside the screen whenever the tooltip might go out on
          the top but still the screen is higher than the tooltip,
        - to use the more flexible mouse positioning,
        - to add customizable background color, padding, waittime and
          wraplength on creation
      by Alberto Vassena on 2016.11.05.

      Tested on Ubuntu 16.04/16.10, running Python 3.5.2
    '''

    def __init__(self, widget,
                 bg='#FFFFEA',
                 pad=(5, 3, 5, 3),
                 text='widget info',
                 waittime=400,
                 wraplength=250):

        self.waittime = waittime  # in miliseconds, originally 500
        self.wraplength = wraplength  # in pixels, originally 180
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.onEnter)
        self.widget.bind("<Leave>", self.onLeave)
        self.widget.bind("<ButtonPress>", self.onLeave)
        self.bg = bg
        self.pad = pad
        self.id = None
        self.tw = None

    def onEnter(self, event=None):
        self.schedule()

    def onLeave(self, event=None):
        self.unschedule()
        self.hide()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.show)

    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)

    def show(self):
        def tip_pos_calculator(widget, label, 
                    tip_delta=(10, 5), pad=(5, 3, 5, 3)):

            w = widget

            s_width, s_height = w.winfo_screenwidth(), w.winfo_screenheight()

            width, height = (pad[0] + label.winfo_reqwidth() + pad[2],
                             pad[1] + label.winfo_reqheight() + pad[3])

            mouse_x, mouse_y = w.winfo_pointerxy()

            x1, y1 = mouse_x + tip_delta[0], mouse_y + tip_delta[1]
            x2, y2 = x1 + width, y1 + height

            x_delta = x2 - s_width
            if x_delta < 0:
                x_delta = 0
            y_delta = y2 - s_height
            if y_delta < 0:
                y_delta = 0

            offscreen = (x_delta, y_delta) != (0, 0)

            if offscreen:
                if x_delta:
                    x1 = mouse_x - tip_delta[0] - width

                if y_delta:
                    y1 = mouse_y - tip_delta[1] - height

            offscreen_again = y1 < 0  # out on the top
            if offscreen_again: y1 = 0

            return x1, y1

        bg = self.bg
        pad = self.pad
        widget = self.widget

        # creates a toplevel window
        self.tw = Toplevel(widget)

        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)

        win = Frame(self.tw,
                       background=bg,
                       borderwidth=0)
        label = Label(win,
                          text=self.text,
                          justify=LEFT,
                          background=bg,
                          relief=SOLID,
                          borderwidth=0,
                          wraplength=self.wraplength)

        label.grid(padx=(pad[0], pad[2]),
                   pady=(pad[1], pad[3]),
                   sticky=NSEW)
        win.grid()

        x, y = tip_pos_calculator(widget, label)

        self.tw.wm_geometry("+%d+%d" % (x, y))

    def hide(self):
        tw = self.tw
        if tw:
            tw.destroy()
        self.tw = None

class Options():
    def __init__(self):
        self.registrationVector = StringVar(value="0.7 -0.6 -4.3")
        self.rotationEntry = StringVar(value="list")
        self.rotationList = StringVar(value="0 45 90")
        self.rotationRangeSteps = IntVar(value=10)
        self.dataFolderDS = StringVar(value=".")
        self.dataFolderRS = StringVar(value=".")
        self.useStructuresFromFolderTree = IntVar(value=0)
        self.structureNumberVar = IntVar(value=0)
        
        self.structureVariable = dict() # to be filled per instance
        self.seriesVariable = dict()

        self.vars = {'registrationVector' : self.registrationVector,
                     'rotationEntry' : self.rotationEntry,
                     'rotationList' : self.rotationList,
                     'rotationRangeSteps' : self.rotationRangeSteps,
                     'dataFolderDS' : self.dataFolderDS,
                     'dataFolderRS' : self.dataFolderRS,
                     'useStructuresFromFolderTree' : self.useStructuresFromFolderTree}

    def loadOptions(self):
        read = False
        if os.path.exists('config.cfg'):
            with open("config.cfg", "r") as configFile:
                for line in configFile.readlines():
                    linesplit = line.rstrip().split(",")
                    var = linesplit[0]
                    value = linesplit[1]
                    if value:
                        read = True
                        if var in list(self.vars.keys()): 
                            self.vars[var].set(value)
        return read

    def saveOptions(self):
        with open("config.cfg","w") as configFile:
            for key, var in list(self.vars.items()):
                configFile.write("{},{}\n".format(key, var.get()))
                
class MainMenu(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.parent = parent

        self.parent.protocol("WM_DELETE_WINDOW", self.myQuit)
        self.parent.title(f"WEPL calculator {PROGRAM_VERSION} - Helge Pettersen")
        self.window = None

        self.wraplength = 250
        self.button_width = 25
        self.imagePad = 5

        self.options = Options()
        res = self.options.loadOptions()

        if not os.path.exists("output"):
            os.makedirs("output")

        self.structureCheckbutton = dict()
        self.seriesCheckbutton = dict()
        self.extStructFile = None

        self.upperContainer = Frame(self, bd=5, relief=RIDGE, height=40)  # Title
        self.middleContainer = Frame(self, bd=5)
        self.bottomContainer = Frame(self, bd=20)

        self.middleLeftContainer = Frame(self.middleContainer, bd=5) # Load folders + options
        self.middleLeftUpperContainer = Frame(self.middleLeftContainer, bd=5) # Load folder tree (many RTDOSE)
        self.middleLeftLine1 = Frame(self.middleLeftContainer, bg="grey", relief=SUNKEN)
        self.middleLeftMiddleContainer = Frame(self.middleLeftContainer, bd=5) # Load individual files (single RTDOSE)
        self.middleLeftLine2 = Frame(self.middleLeftContainer, bg="grey", relief=SUNKEN)
        self.middleLeftLowerContainer = Frame(self.middleLeftContainer, bd=5) # Options
        self.middleRightLine = Frame(self.middleContainer, bg="grey", relief=SUNKEN)
        self.middleRightContainer = Frame(self.middleContainer, bd=5)
        self.middleRightUpperContainer = Frame(self.middleRightContainer, bd=5) # progress bar
        self.middleRightUpperLine = Frame(self.middleRightContainer, bd=5)
        self.middleRightMiddleContainer = Frame(self.middleRightContainer, bd=5) # Structure window
        self.middleRightMiddle1Container = Frame(self.middleRightMiddleContainer, bd=5)
        self.middleRightMiddle2Container = Frame(self.middleRightMiddleContainer, bd=5)
        self.middleRightMiddle3Container = Frame(self.middleRightMiddleContainer, bd=5)
        self.middleRightMiddle4Container = Frame(self.middleRightMiddleContainer, bd=5)
        self.middleRightMiddleLine = Frame(self.middleRightContainer, bd=5)
        self.middleRightLowerContainer = Frame(self.middleRightContainer, bd=5) # Series window
        self.middleRightLower1Container = Frame(self.middleRightLowerContainer, bd=5)
        self.middleRightLower2Container = Frame(self.middleRightLowerContainer, bd=5)
        self.middleRightLower3Container = Frame(self.middleRightLowerContainer, bd=5)
        self.middleRightLower4Container = Frame(self.middleRightLowerContainer, bd=5)
        
        self.bottomLine = Frame(self.bottomContainer, bg="grey", relief=SUNKEN)
        self.bottomContainer1 = Frame(self.bottomContainer) # Action buttons

        # Output options
        self.registrationVectorContainer = Frame(self.middleLeftLowerContainer)
        self.useStructuresFromFolderTreeContainer = Frame(self.middleLeftLowerContainer)
        self.rotationEntryContainer = Frame(self.middleLeftLowerContainer)
        self.rotationListContainer = Frame(self.middleLeftLowerContainer)
        self.rotationRangeContainer = Frame(self.middleLeftLowerContainer)
        self.structureNumberContainer = Frame(self.middleLeftLowerContainer)
        self.structureActionContainer = Frame(self.middleRightMiddleContainer)
        self.seriesActionContainer = Frame(self.middleRightLowerContainer)

        self.upperContainer.pack(fill=X)
        self.middleContainer.pack(fill=Y)

        self.middleLeftContainer.pack(side=LEFT,fill='both', expand=1, anchor=N)
        self.middleLeftUpperContainer.pack(fill=X)
        self.middleLeftLine1.pack(fill=X, padx=5, pady=5)
        self.middleLeftMiddleContainer.pack(fill=X)
        self.middleLeftLine2.pack(fill=X, padx=5, pady=5)
        self.middleLeftLowerContainer.pack(fill=X)
        
        self.middleRightLine.pack(side=LEFT, fill=Y, padx=5, pady=5, expand=1)
        self.middleRightContainer.pack(side=LEFT,fill=Y)
        self.middleRightUpperContainer.pack(fill=X)
        self.middleRightUpperLine.pack(fill=X, padx=5, pady=5)
        self.middleRightMiddleContainer.pack(anchor=N, fill=X)
        self.middleRightMiddleLine.pack(fill=X, padx=5, pady=5)
        self.middleRightLowerContainer.pack(anchor=N, fill=X)
        
        self.bottomLine.pack(fill=X, padx=5, pady=5, expand=1)
        self.bottomContainer.pack(fill=X, anchor=N, expand=1)
        self.bottomContainer1.pack(anchor=N, expand=1)

        Label(self.upperContainer,
              text=f'WEPL Calculator {PROGRAM_VERSION} - Helge pettersen').pack(anchor=N)

        self.loadFolderButton = Button(self.middleLeftUpperContainer, text='Load folder tree',
                                       command=self.loadFolderCommand, width=self.button_width)
        self.loadFolderButton.pack(anchor=N, pady=3)
        Tooltip(self.loadFolderButton, text='Loops through all subfolders in the indicated folders. '
                'Loads all the located image series, but gives the user the possibility of excluding '
                'unwanted series in the right pane. The selected folder should contain subfolders with '
                ' a single series / imaging date / phase each. ', wraplength=self.wraplength)

        self.loadRSFileButton = Button(self.middleLeftMiddleContainer, text='Load structure file',
                                       command=self.loadFileCommand, width=self.button_width)
        self.loadRSFileButton.pack(anchor=N, pady=3)

        Tooltip(self.loadRSFileButton, text='Load a structure set from a RS file. The structures '
                'should match the geometry from the above files.', wraplength=self.wraplength)

        Label(self.middleLeftLowerContainer, text='OPTIONS', font=('Helvetica', 10)).pack(anchor=N)

        # REGISTRATION VECTOR
        self.registrationVectorContainer.pack(anchor=W)
        Label(self.registrationVectorContainer, text="Image Registration Vector (\"x y z\"): ").pack(side=LEFT, anchor=W)
        Entry(self.registrationVectorContainer, textvariable=self.options.registrationVector, width=15).pack(side=LEFT)

        self.useStructuresFromFolderTreeContainer.pack(anchor=W)
        Label(self.useStructuresFromFolderTreeContainer, text="Use Structures from DICOM folder tree: ").pack(side=LEFT, anchor=W)
        for text, mode in [["Yes", 1], ["No", 0]]:
            Radiobutton(self.useStructuresFromFolderTreeContainer, text=text,
                        variable=self.options.useStructuresFromFolderTree, command=self.useStructuresFromFolderTreeCommand,
                        value=mode).pack(side=LEFT)
        
        # ROTATIONS
        self.rotationEntryContainer.pack(anchor=W)
        Label(self.rotationEntryContainer, text="Rotation entry type: ").pack(side=LEFT, anchor=W)
        for text, mode in [['List', 'list'], ['Range', 'range']]:
            Radiobutton(self.rotationEntryContainer, text=text, variable=self.options.rotationEntry, value=mode,
                        command=self.rotationEntrySelector).pack(side=LEFT, anchor=W)

        self.rotationListContainer.pack(anchor=W)
        Label(self.rotationListContainer, text="Rotation List: ").pack(side=LEFT, anchor=W)
        self.rotationList = Entry(self.rotationListContainer, textvariable=self.options.rotationList, width=15)
        self.rotationList.pack(side=LEFT)

        self.rotationRangeContainer.pack(anchor=W)
        Label(self.rotationRangeContainer, text="Rotation range number of steps: ").pack(side=LEFT, anchor=W)
        self.rotationRange = Entry(self.rotationRangeContainer, textvariable=self.options.rotationRangeSteps, width=5)
        self.rotationRange['state'] = 'disabled'
        self.rotationRange.pack(side=LEFT)

        self.structureNumberContainer.pack(anchor=W)
        Label(self.structureNumberContainer, text="Structure to choose if multiple: ").pack(side=LEFT, anchor=W)
        for text, mode in [['First', 0], ['Last', -1], ["All", 1]]:
            Radiobutton(self.structureNumberContainer, text=text, value=mode,
                        variable=self.options.structureNumberVar).pack(side=LEFT, anchor=W)

        self.progress = ttk.Progressbar(self.middleRightUpperContainer, orient=HORIZONTAL, maximum=100, mode='determinate')
        self.progress.pack(fill=X, pady=3)

        Label(self.middleRightMiddleContainer, text='STRUCTURES', font=('Helvetica',10)).pack(anchor=N)
        
        self.structureActionContainer.pack(anchor=N)
        self.structureActionCheckAllButton = Button(self.structureActionContainer, text='Check all',
                                                    command=self.structureCheckAllCommand,
               width=self.button_width, state=DISABLED)
        self.structureActionUncheckAllButton = Button(self.structureActionContainer, text='Uncheck all',
                                                      command=self.structureUncheckAllCommand,
               width=self.button_width, state=DISABLED)

        self.structureActionCheckAllButton.pack(side=LEFT)
        self.structureActionUncheckAllButton.pack(side=LEFT)

        self.middleRightMiddle1Container.pack(anchor=N, side=LEFT, fill=X, expand=Y)
        self.middleRightMiddle2Container.pack(anchor=N, side=LEFT, fill=X, expand=Y)
        self.middleRightMiddle3Container.pack(anchor=N, side=LEFT, fill=X, expand=Y)
        self.middleRightMiddle4Container.pack(anchor=N, side=LEFT, fill=X, expand=Y)

        # PUT STRUCTURES HERE WHEN / IF THEY ARE LOADED FROM SINGLE RS FILE
        Label(self.middleRightLowerContainer, text='SERIES', font=('Helvetica',10)).pack(anchor=N)
        
        self.seriesActionContainer.pack(anchor=N)
        self.seriesActionCheckAllButton = Button(self.seriesActionContainer, text='Check all',
                                                 command=self.seriesCheckAllCommand,
               width=self.button_width, state=DISABLED)
        self.seriesActionUncheckAllButton = Button(self.seriesActionContainer, text='Uncheck all',
                                                   command=self.seriesUncheckAllCommand,
               width=self.button_width, state=DISABLED)

        self.seriesActionCheckAllButton.pack(anchor=N, side=LEFT)
        self.seriesActionUncheckAllButton.pack(side=LEFT)

        self.middleRightLower1Container.pack(anchor=N, side=LEFT, fill=X, expand=Y)
        self.middleRightLower2Container.pack(anchor=N, side=LEFT, fill=X, expand=Y)
        self.middleRightLower3Container.pack(anchor=N, side=LEFT, fill=X, expand=Y)
        self.middleRightLower4Container.pack(anchor=N, side=LEFT, fill=X, expand=Y)

        # PUT SERIES HERE WHEN / IF THEY ARE LOADED FROM THE DS FILES

        """
        self.buttonPlotRTDoseSlicewise = Button(self.bottomContainer1, text='Plot RT dose + DVH per slice',
                                command=self.plotRTDoseSlicewiseCommand, width=self.button_width, state=DISABLED)
        self.buttonPlotDVH = Button(self.bottomContainer1, text='Plot DVH',
                                command=self.plotDVHCommand, width=self.button_width, state=DISABLED)
        self.buttonSaveDVH = Button(self.bottomContainer1, text='Save DVH file(s)', command=self.saveDVHCommand,
                                    width=self.button_width, state=DISABLED)
        """

        self.buttonPlotAllImages = Button(self.bottomContainer1, text="Plot image series",
                                          command=self.plotAllImageSeriesCommand, width=self.button_width, state=DISABLED)

        self.buttonMakeViolinPlot = Button(self.bottomContainer1, text="WEPL violin plot",
                                           command=self.makeViolinPlotCommand, width=self.button_width, state=DISABLED)

        self.buttonMakeVariationPlot = Button(self.bottomContainer1, text="WEPL variation vs phase",
                                              command=self.makeVariationPlotCommand, width=self.button_width, state=DISABLED)
        
        self.buttonQuit = Button(self.bottomContainer1, text='Exit', command=self.myQuit, width=self.button_width)

        for button in [self.buttonPlotAllImages, self.buttonMakeViolinPlot, self.buttonMakeVariationPlot, self.buttonQuit]:
            button.pack(side=LEFT, anchor=N, padx=5, pady=5)

        self.pack()

    def myQuit(self):
        self.options.saveOptions()
        self.parent.destroy()
        self.quit()

    def rotationEntrySelector(self):
        if self.options.rotationEntry.get() == "list":
            self.rotationRange['state'] = 'disabled'
            self.rotationList['state'] = 'normal'
        else:
            self.rotationRange['state'] = 'normal'
            self.rotationList['state'] = 'disabled'

    def useStructuresFromFolderTreeCommand(self):
        if self.options.useStructuresFromFolderTree.get():
            self.loadRSFileButton['state'] = 'disabled'
        else:
            self.loadRSFileButton['state'] = 'normal'

    def loadFolderCommand(self):
        dataFolder = filedialog.askdirectory(title="Get root directory for image series", initialdir=self.options.dataFolderDS.get())
        if not dataFolder:
            print("No directory selected, aborting.")
            return

        self.options.dataFolderDS.set(dataFolder)

        t = [float(k) for k in self.options.registrationVector.get().split(" ")]
        subfolders = [ root for root, dirs, files in os.walk(dataFolder) if len(files) ]

        self.imageCollection = [ Series(path=os.path.join(dataFolder, subFolder), translation=t, options=self.options)
                                for subFolder in subfolders ]

        self.progress['maximum'] = len(self.imageCollection)
        self.progress['value'] = 0
        
        seriesContainer = [self.middleRightLower1Container,
                           self.middleRightLower2Container,
                           self.middleRightLower3Container,
                           self.middleRightLower4Container]

        structureContainer = [self.middleRightMiddle1Container,
                              self.middleRightMiddle2Container,
                              self.middleRightMiddle3Container,
                              self.middleRightMiddle4Container]

        loaded_rs = False
        idx_struct = 0
        idx_names = 0

        for imageSeries in self.imageCollection:
            self.progress.step(1)
            self.progress.update_idletasks()

            load_rs = self.options.useStructuresFromFolderTree.get() and not loaded_rs
            imageSeries.loadImages(load_rs)

            if self.options.useStructuresFromFolderTree.get():
                # Load Structures onto Container for selection
                if imageSeries.rs and not loaded_rs:
                    self.progress['maximum'] = len(self.imageCollection) + len(imageSeries.rs.ROIContourSequence)
                    imageSeries.loadStructures(progress)
                    for structureName in imageSeries.listOfStructures:
                        if structureName in self.options.structureVariable.keys():
                            continue
                        
                        self.options.structureVariable[structureName] = IntVar(value=0)
                        self.structureCheckbutton[structureName] = Checkbutton(structureContainer[idx_struct%4], text=structureName,
                                                                        variable=self.options.structureVariable[structureName])
                        self.structureCheckbutton[structureName].pack(anchor=NW)
                        idx_struct += 1
                        
                    loaded_rs = True
                    self.structureActionCheckAllButton['state'] = 'normal'
                    self.structureActionUncheckAllButton['state'] = 'normal'

            # Load Series onto Container for selection
            for name, count in imageSeries.getAllDatesAndSeriesDescription().items():
                if name in self.options.seriesVariable.keys():
                    continue

                newName = f"{name[:-1]}, {count} slices)"

                self.options.seriesVariable[name] = IntVar(value=1)
                self.seriesCheckbutton[name] = Checkbutton(seriesContainer[idx_names%4], text=newName,
                                                           variable=self.options.seriesVariable[name])
                self.seriesCheckbutton[name].pack(anchor=NW)
                idx_names += 1

        # Activate buttons
        self.seriesActionCheckAllButton['state'] = 'normal'
        self.seriesActionUncheckAllButton['state'] = 'normal'

        self.buttonPlotAllImages['state'] = 'normal'
        self.buttonMakeViolinPlot['state'] = 'normal'
        self.buttonMakeVariationPlot['state'] = 'normal'

        self.progress['value'] = 0

    def loadFileCommand(self): # RS
        fileName = filedialog.askopenfilename(title='Get DICOM Structure File', initialdir=self.options.dataFolderRS.get())
        if not fileName:
            print("No files selected, aborting.")
            return

        self.options.dataFolderRS.set("/".join(fileName.split("/")[:-1]) + "/")
        
        try:
            self.extStructFile = Series(rs=fileName, options=self.options)
            
            self.progress['maximum'] = len(self.extStructFile.rs.ROIContourSequence)
            self.extStructFile.loadStructureNames(self.progress)
            self.progress['value'] = 0
            
            structureContainer = [self.middleRightMiddle1Container,
                                  self.middleRightMiddle2Container,
                                  self.middleRightMiddle3Container,
                                  self.middleRightMiddle4Container]
            
            for idx, structureName in enumerate(self.extStructFile.listOfStructures):
                self.options.structureVariable[structureName] = IntVar(value=0)
                self.structureCheckbutton[structureName] = Checkbutton(structureContainer[idx%4], text=structureName,
                                                                variable=self.options.structureVariable[structureName])
                self.structureCheckbutton[structureName].pack(anchor=NW)

            self.structureActionCheckAllButton['state'] = 'normal'
            self.structureActionUncheckAllButton['state'] = 'normal'

            self.buttonPlotAllImages['state'] = 'normal'
            self.buttonMakeViolinPlot['state'] = 'normal'
            self.buttonMakeVariationPlot['state'] = 'normal'
                
        except Exception as e:
            print(f"Error message: {e}")
            return
        
    def structureCheckAllCommand(self):
        for check in self.options.structureVariable.values():
            check.set(1)

    def structureUncheckAllCommand(self):
        for check in self.options.structureVariable.values():
            check.set(0)

    def seriesCheckAllCommand(self):
        for check in self.options.seriesVariable.values():
            check.set(1)

    def seriesUncheckAllCommand(self):
        for check in self.options.seriesVariable.values():
            check.set(0)

    def getRotationList(self):
        if self.options.rotationEntry.get() == "list":
            return [ float(k) for k in self.options.rotationList.get().split(" ") if k]
        else:
            return np.arange(0, 360, 360/int(self.options.rotationRangeSteps.get()))

    def makeReducedImageCollection(self):       
        selectedSeries = [ k for k,v in self.options.seriesVariable.items() if v.get() ]
        self.reducedImageCollection = list()
        for idx, s in enumerate(self.imageCollection):
            if any([k in selectedSeries for k in s.getAllDatesAndSeriesDescription().keys()]):
                self.reducedImageCollection.append(idx)

    def loadCheckedStructures(self):
        structures = [ k for k,v in self.options.structureVariable.items() if v.get() ]
                
        if self.extStructFile:
            for s in self.imageCollection:
                self.extStructFile.structures = structures
                self.extStructFile.loadStructures()
                s.contours = { k:v for k,v in self.extStructFile.contours.items() if self.options.structureVariable[k].get()}
                s.structures = structures                
                
        else:
            for s in self.imageCollection:
                s.contours = { k:v for k,v in s.contours.items() if self.options.structureVariable[k].get() }
                s.structures = structures

    def makeDataFrame(self):
        self.makeReducedImageCollection()
        self.loadCheckedStructures()

        rotations = self.getRotationList()
        dfSum = pd.DataFrame()

        thisDate = None

        for icIdx, s in enumerate(self.imageCollection):
            if not icIdx in self.reducedImageCollection:
                continue
            
            if self.extStructFile:
                UIDs = self.extStructFile.getUIDsFromStructures()
                zposList = sorted(self.extStructFile.getZposFromStructures())
            else:
                UIDs = s.getUIDsFromStructures()
                zposList = sorted(s.getZposFromStructures()) # NEW

            self.progress['maximum'] = len(self.reducedImageCollection) * (len(zposList)) * len(rotations)

            for idxUID, UID in enumerate(list(UIDs)):
                s.loadImageFromPosZ(zposList[idxUID])

                if not thisDate:
                    thisDate = s.ds.StudyDate

                for rot in rotations:
                    self.progress.step(1)
                    self.progress.update_idletasks()

                    s.resetImage()
                    s.rotateImage(rot)
                    s.recalculateContourBounds()
                    s.reduceImageSize(self.imagePad)
                    s.convertImageToRSP()
                    
                    wepl = s.convertImageToWEPL()
                    contours = s.getStructuresInImageCoordinates()
                    
                    idx=0
                    for contourX, contourY in zip(*contours):
                        linearContour = LinearContour(s.dicomTranslation, s.pixelSpacing)
                        linearContour.addLines(list(zip(contourX, contourY)))
                        pixelContourMap = linearContour.getListOfPixelsInContour(s.image)
                        weplImageBinned = np.array(wepl[pixelContourMap], dtype='int64')

                        dfSum = dfSum.append(pd.DataFrame({'WEPL':weplImageBinned, '4D phase':s.amplitude,
                                                           'structureIdx':idx, 'rotation':rot}), ignore_index=True)
                        idx += 1

        self.progress['value'] = 0
        return dfSum, thisDate

    def makeViolinPlotCommand(self):
        dfSum, thisDate = self.makeDataFrame()
        rotations = self.getRotationList()
        
        for rot in rotations:
            fig = plt.figure(figsize=(12,7))
            dfThis = dfSum[dfSum['rotation'] == rot]
            ax = sns.violinplot(x="4D phase", y="WEPL", data=dfThis)
            plt.title(f"Rotation {rot} degrees; images from {thisDate}")
            
        plt.show()

    def plotAllImageSeriesCommand(self):
        self.makeReducedImageCollection()
        self.loadCheckedStructures()
        rotations = self.getRotationList()[0:1] # Only display first entry
        firstImageSeries = self.imageCollection[self.reducedImageCollection[0]] # Only display first entry

        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15,8))
        tracker = IndexTracker(ax1, ax2, ax3, firstImageSeries, self.extStructFile, self.options, rotations)
        fig.canvas.mpl_connect('scroll_event', tracker.onscroll)
        plt.show()

    def makeVariationPlotCommand(self):
        dfSum, thisDate = self.makeDataFrame()
        rotations = self.getRotationList()

        fig = plt.figure(figsize=(12,7))
        firstLabelPass = True
        for idx, rot in enumerate(rotations):
            thisLabel = firstLabelPass and f"{rot}° beam" or None
            if rot == 0:
                thisLabel = "AP beam"
            elif rot == 90:
                thisLabel = "Lateral  beam"
            elif rot == 180:
                thisLabel = "PA beam"
            else:
                thisLabel = f"{rot}° beam"
                
            quantiles = dfSum[dfSum['rotation'] == rot].groupby('4D phase')['WEPL'].quantile([0.25, 0.5, 0.75]).reset_index()
            phases = [k[:-4] for k in quantiles['4D phase'].unique()]        
            plt.plot(phases, quantiles[quantiles['level_1'] == 0.5]['WEPL'].values, color=lineColors[idx+1], label=thisLabel)
            plt.fill_between(phases, quantiles[quantiles['level_1'] == 0.25]['WEPL'].values, quantiles[quantiles['level_1'] == 0.75]['WEPL'].values,
                            color=fillColors[idx+1], alpha=0.5)
            plt.title("WEPL variation during free breath")
            plt.xlabel("4D phase")
            plt.ylabel("WEPL distribution: Median ± Quartiles")
#            firstLabelPass = False
        plt.legend()
        plt.show()

"""
structureToUse = "GTV øsofAcc"
numberOfImageSeries = 1 # None to get all
showIndividualImages = True
plotWEPLPerRotation = False

data_planning = {"Esophagus/Study date 20160929/Series Description CT THORAX" : reg_planning }
data_4D = {f"Esophagus/Study date 20160929/Series Description {k:.1f}% AMP" : reg_4D for k in np.arange(0,100,12.5) }

imageSeries = [Series(path=path, structure=structureToUse, translation=translation) \
               for path,translation in list(data_planning.items())[:numberOfImageSeries]]

imageSeries += [Series(path=path, structure=structureToUse, translation=translation) \
               for path,translation in list(data_4D.items())[:numberOfImageSeries]]

extStructFile = [Series(path=path, structure=structureToUse, translation=translation) for path,translation in list(data_planning.items())][0]
extStructFile.loadImages() # no z -> no images loaded

for img in imageSeries:
    img.loadImages()

cbarShrink = 0.8
colorlist = ["r", "b", "k", "y", "g"]

lineColors = ["orange", "red", "blue", 'darkgoldenrod', 'black', 'crimson']
fillColors = ["wheat",  "lightcoral", "lightblue", 'goldenrod', 'darkgray', 'pink']
lightFillColors = ["oldlace", "mistyrose", "lavender", 'gold', 'lightgray', 'lightpink']

pad = 5
firstPass = True
rotations = [120]
minBinLength = 500
structureStatistics = list()
dfSum = pd.DataFrame()
accumulatedStructureStatistics = list()

rotation = 0
nVoxels = 0
for seriesIdx in range(len(imageSeries)): # Loop over patients / image series / acquisition dates / etc.   
    if extStructFile:
        UIDs = extStructFile.getUIDsFromStructures()
        zposList = sorted(extStructFile.getZposFromStructures())
    else:
        UIDs = imageSeries[seriesIdx].getUIDsFromStructures()
    
    print(f"Found {len(UIDs)} images @ {imageSeries[seriesIdx].amplitude}", end="")

    if plotWEPLPerRotation:
        fig2 = plt.figure(figsize=(10,10))
        
    structureStatistics.append(list())
    for idxUID, UID in enumerate(list(UIDs)):
        if idxUID != 0: continue
        
        if not idxUID%5:
            print(".", end="")

        if extStructFile:
            imageSeries[seriesIdx].loadImageFromPosZ(zposList[idxUID])
            imageSeries[seriesIdx].loadStructuresFromExternalStructureFile(extStructFile)
        else:
            imageSeries[seriesIdx].loadImageFromUID(UID)
            imageSeries[seriesIdx].loadStructures()

        for rot in rotations:
            imageSeries[seriesIdx].resetImage()
            imageSeries[seriesIdx].rotateImage(rot)
            imageSeries[seriesIdx].recalculateContourBounds()
            imageSeries[seriesIdx].reduceImageSize(pad)
            imageSeries[seriesIdx].convertImageToRSP()
            
            wepl = imageSeries[seriesIdx].convertImageToWEPL()
            contours = imageSeries[seriesIdx].getStructuresInImageCoordinates()
            
            idx=0
            for contourX, contourY in zip(*contours):
                linearContour = LinearContour(imageSeries[seriesIdx].dicomTranslation,
                                              imageSeries[seriesIdx].pixelSpacing)
                linearContour.addLines(list(zip(contourX, contourY)))
                pixelContourMap = linearContour.getListOfPixelsInContour(imageSeries[seriesIdx].image)
                
                weplImageBinned = np.array(wepl[pixelContourMap], dtype='int64')
                
                if len(structureStatistics[seriesIdx]) == idx:
                    structureStatistics[seriesIdx].append({k:np.zeros(500) for k in rotations})
                
                structureStatistics[seriesIdx][idx][rot] += np.bincount(weplImageBinned,
                                                                        minlength=minBinLength)

                dfSum = dfSum.append(pd.DataFrame({'WEPL':weplImageBinned,
                                                   '4D phase':imageSeries[seriesIdx].amplitude,
                                                   'structureIdx':idx, 'rotation':rot}), ignore_index=True)
                
                nVoxels += len(pixelContourMap)
                idx += 1

    print()
    # Calculate accumulated statistics from the histograms summed over all images
    
    q = [25,50,75]
    accumulatedStructureStatistics.append([ dict() for idx in range(len(structureStatistics[seriesIdx]))])
    for strIdx, structure in enumerate(structureStatistics[seriesIdx]):
        for rot,hist in structure.items():
            if np.sum(hist) == 0:
                continue
            
            cumHist = np.cumsum(hist)
            thisQ = q[:]
            p = list()
            q0 = thisQ.pop(0)
            histSum = cumHist[-1]
            for idx,k in enumerate(cumHist):
                if cumHist[idx] > histSum * q0/100:
                    qUpper = cumHist[idx] / histSum
                    qLower = cumHist[idx-1] / histSum
                    percInterp = (q0/100 - qLower) / (qUpper - qLower) + idx - 1
                    p.append(percInterp)
                    try:
                        q0 = thisQ.pop(0)
                    except IndexError:
                        break # Found all percentiles!
                    
            accumulatedStructureStatistics[seriesIdx][strIdx][rot] = dict(zip(q,p))

    
    r = list()
    for _ in accumulatedStructureStatistics[seriesIdx]:
        r.append(np.zeros(len(rotations)))

    if plotWEPLPerRotation:
        firstLabelPass = True
        for rot in rotations:
            for kidx, k in enumerate(accumulatedStructureStatistics[seriesIdx]):
                thisLabelMedian = firstLabelPass and f"Median ({structureToUse})" or None
                thisLabelQuartiles = firstLabelPass and f"1st + 3rd Quartile ({structureToUse})" or None
                plt.plot(list(k.keys()), [perc[50] for perc in k.values()], color=lineColors[kidx], label=thisLabelMedian)
                plt.fill_between(list(k.keys()), [perc[25] for perc in k.values()], [perc[75] for perc in k.values()],
                                 label=thisLabelQuartiles, color=fillColors[kidx], alpha=0.5)
                r[kidx] = [perc[75] - perc[25] for perc in k.values()]
                r[kidx].append(r[kidx][0])
                plt.xlabel("Beam rotation [degrees]")
                plt.ylabel("WEPL values")
                plt.ylim(0,350)
                plt.title(f"(sub) structure statistics for {structureToUse} (Number of images: {idxUID+1})")
            firstLabelPass = False
        plt.legend()

    rotationsRadian = [k/180*3.1415926535 for k in rotations]
    rotationsRadian.append(rotationsRadian[0])

    if plotWEPLPerRotation:
        fig2 = plt.figure()
        ax = fig2.add_subplot(111, polar=True)
        ax.set_theta_zero_location("N")
        firstLabel2Pass = True
        for kidx in range(len(structureStatistics[seriesIdx])):
            thisLabelMedian = firstLabel2Pass and f"IQD for {structureToUse}" or None
            plt.title(f"WEPL variantion for {structureToUse} with {idxUID+1} images")
            plt.plot(rotationsRadian, r[kidx], color=lineColors[kidx], label=thisLabelMedian)
            plt.fill_between(rotationsRadian, np.zeros(len(r[kidx])), r[kidx], color=fillColors[kidx], alpha=0.5)
            plt.xlabel("Beam direction")
            plt.ylabel("WEPL IQD [mm]")
        firstLabel2Pass = False
        plt.legend()

    

pr.disable()
s = StringIO()
sortby = 'cumulative'
ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
ps.print_stats()
print(s.getvalue())

plt.show()
"""

root = Tk()
mainmenu = MainMenu(root)
root.mainloop()
