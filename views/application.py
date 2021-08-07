import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

from views.layout import Layout
from views.productSchedule import ProductSchedule

class Application(tk.Tk):

    def __init__(self, factory_obj, BASE_DATE,*args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.title('Simulator')
        self.title_font = tkfont.Font(family='Helvetica', size=18, weight="bold", slant="italic")
        # self.tk.call('tk', 'scaling', 1.0)
        self.factory = factory_obj
        self.base_date = BASE_DATE
        # the container is where we'll stack a bunch of frames
        # on top of each other, then the one we want visible
        # will be raised above the others
        container = ttk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (Layout, ProductSchedule):
            page_name = F.__name__
            frame = F(parent=container, controller=self, factory_obj=self.factory, BASE_DATE=self.base_date)
            self.frames[page_name] = frame

            # put all of the pages in the same location;
            # the one on the top of the stacking order
            # will be the one that is visible.
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("Layout")

    def show_frame(self, page_name):
        '''Show a frame for the given page name'''
        frame = self.frames[page_name]
        frame.tkraise()

