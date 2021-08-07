import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import copy

#from utils.utils import sec_to_timedelta_8h
from utils.utils import sec_to_timedelta_9h

def get_day(time):
    return sec_to_timedelta_9h(time).days + 1

# Tkinter Class
def draw(factory, start_day, end_day):

    check = []
    for worker in factory.worker_list:
        if worker.record:
            check.append(worker.record)
    fig = None
    
    if check:
        #factory = copy.deepcopy(factory)
        if start_day < 1:
            start_day = 1
        start_time = (start_day-1) *9*60*60
        if start_time > factory.time:
            start_time = factory.time

        if end_day < 1:
            end_day = 1
        limit_time = end_day *9*60*60
        if limit_time > factory.time:
            limit_time = factory.time

    fig = None
    
    lst = []
    machines = []
    for machine in factory.machine_list:
        machines.append(machine.machine_name)
    for worker in factory.worker_list:
        for rec in worker.record:  # worker.record =[[作業内容, 対象機械, 開始時間, 終了時間], []...]
            if rec[1] in machines:
                if rec[3] < limit_time and rec[2] > start_time:
                    lst.append(rec)
    if lst:
        df = pd.DataFrame(lst)
        df2 = df[[1,2]].copy()
        df2['day'] = df2[2].apply(get_day)
        df2 = df2.rename(columns={1:'machine'})
        p_df = df2.pivot_table(
            values=2, index='machine', columns='day', aggfunc='count')
        plt.rcParams['figure.figsize'] = (10.0, 10.0)
        plt.style.use('dark_background')

        fig, ax = plt.subplots(1,1)
        sns.heatmap(p_df)

    root = tk.Tk()
    root.title('HeatMap')
    # root.geometry("300x200")
    # root.tk.call('tk', 'scaling', 0.5)
    root.withdraw()
    # Canvas
    if fig:
        canvas = FigureCanvasTkAgg(fig, master=root)  # Generate canvas instance, Embedding fig in root
        canvas.draw()
        canvas.get_tk_widget().pack()
        #canvas._tkcanvas.pack()

    # root
    #root.protocol('WM_DELETE_WINDOW', _destroyWindow)  # When you close the tkinter window.
    root.update()
    root.deiconify()
    root.mainloop()

#def _destroyWindow():
#    root.quit()
#    root.destroy()
