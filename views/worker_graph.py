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
    #描画するデータがあるか確認
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
        
        dic = defaultdict(list)

        worker_list = copy.deepcopy(factory.worker_list)
        for worker in worker_list:
        #for worker in factory.worker_list:
            for rec in worker.record: #worker.record =[[作業内容, 対象機械, 開始時間, 終了時間], []...]
                if rec[3] < limit_time and rec[2] > start_time:
                    dic[worker.name].append(rec)
                    
        lst=[]
        dd={}
        for k, v in dic.items():
            d = defaultdict(list)
            for rec in v:
                d[rec[0]].append([rec[1], rec[3]-rec[2]])
            dd[k] = d
        for name, rec in dd.items():
            for action, m_t in rec.items():
                ddd = defaultdict(list)
                for raw in m_t:
                    ddd[raw[0]].append(raw[1])
                dddd = {}
                for machine, time in ddd.items():
                    dddd[machine] = sum(time)
                lst.append([name, action, dddd])

        record_dic = defaultdict(list)
        for raw in lst:
            if raw[1] != 'move':
                record_dic[raw[0]].append([raw[1], raw[2]])
            
        record_list = []
        for name, l in record_dic.items():
            lst = []
            for raw in l:
                df = pd.DataFrame(raw[1].values(),index=raw[1].keys(),columns=[raw[0]]).T
                lst.append(df)
            record_list.append([name, lst])
            
        record = []
        for name, df_list in record_list:
            df_concat = pd.concat(df_list)
            record.append([name, df_concat])
            
        record_sum = []
        w = []
        for rec in record:
            w.append(rec[0])
        for worker in factory.worker_list:
            if worker.name not in w:
                record_sum.append(
                    [worker.name, pd.Series((0,), index=('None',))]
                    )
        for rec in record:
            record_sum.append([rec[0], rec[1].sum()])
            
        """    
        record_total = []
        for rec_sum in record_sum:
            df_other = pd.Series([(limit_time-start_time) - rec_sum[1].sum()], index=['OTHER'])
            d = rec_sum[1].append([df_other])
            record_total.append([rec_sum[0], d])
        """

        record_total = []
        for rec_sum in record_sum:
            for worker in factory.worker_list:
                if worker.name == rec_sum[0]:
                    df_other = pd.Series(
                        [
                            worker.return_attendance_time(start_time, limit_time, factory.time) - rec_sum[1].sum()
                            ], index=['OTHER'])
                    d = rec_sum[1].append([df_other])
                    record_total.append([rec_sum[0], d])

        if record_total:
            plt.rcParams['figure.figsize'] = (15.0, 10.0)
            sns.set_context('talk')
            plt.style.use('dark_background')

            fig, ax = plt.subplots(1, len(record_total))

            i=0
            for rec in record_total:
                try:
                    if rec:
                        ax[i].set_title(rec[0])
                        ax[i].pie(
                            rec[1], labels=rec[1].index, startangle=90, 
                            counterclock=False, normalize=True)
                        #ax[i].legend();
                        i += 1
                except:
                    pass
    else:
        pass

    root = tk.Tk()
    root.title('WorkingRatio')
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
