import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import copy

#from utils.utils import sec_to_timedelta_8h
from utils.utils import sec_to_timedelta_9h

# Tkinter Class
def draw(factory, start_day, end_day):
    fig = None
    #factory = copy.deepcopy(factory)
    if start_day < 1:
        start_day = 1
    start_time = (start_day-1) *9*60*60
    if start_time > factory.time:
        start_time = factory.time
    
    limit_time = end_day *9*60*60
    if limit_time > factory.time:
        limit_time = factory.time
    
    lst = []
    product_list = copy.deepcopy(factory.product_list)
    for product in product_list:
    #for product in factory.product_list:
        for fin in product.finished_process:
            if fin[1] <= limit_time and fin[2] >= start_time:
                if fin[1] < start_time:
                    fin[1] = start_time 
                if fin[2] > limit_time:
                    fin[2] = limit_time
                lst.append([product.product, fin[0][0], fin[2]-fin[1]])

    machine_run_dic = defaultdict(list)
    for l in lst:
        machine_run_dic[l[1]].append(l[2])
    machine_run_sum = {}
    machine_run_sum['TOTAL TIME'] = limit_time-start_time
    for machine in factory.machine_list:
        machine_run_sum[machine.machine_name] = 0
    for k, v in machine_run_dic.items():
        machine_run_sum[k] = sum(v)
    df = pd.DataFrame(
        machine_run_sum.values(), 
        index=machine_run_sum.keys(), columns=['runtime'])
    sdf = df.sort_values(by='runtime',ascending=True)

    if lst:
        plt.rcParams['figure.figsize'] = (15.0, 15.0)
        sns.set_context('talk')
        plt.style.use('ggplot')

        fig, ax = plt.subplots(1, 1)

        ax.barh(sdf.index, sdf['runtime'], height=0.8);    

    root2 = tk.Tk()
    root2.title('MachiesRunnigTime')
    # root2.geometry("300x200")
    # root2.tk.call('tk', 'scaling', 0.5)
    root2.withdraw()
    # Canvas
    if fig:
        canvas = FigureCanvasTkAgg(fig, master=root2)  # Generate canvas instance, Embedding fig in root
        canvas.draw()
        canvas.get_tk_widget().pack()
        #canvas._tkcanvas.pack()

    # root
    #root2.protocol('WM_DELETE_WINDOW', _destroyWindow)  # When you close the tkinter window.
    root2.update()
    root2.deiconify()
    root2.mainloop()
    

#def _destroyWindow():
#    root2.quit()
#    root2.destroy()