import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
from collections import defaultdict

from models.factory import Factory

#from utils.utils import sec_to_timedelta_8h
from utils.utils import sec_to_timedelta_9h
from utils.utils import return_biz_day

from views import worker_graph
from views import machine_graph
from views import heatmap

class ProductSchedule(tk.Frame):

    def __init__(self, parent, controller, factory_obj, BASE_DATE):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        self.factory = factory_obj
        self.BASE_DATE = BASE_DATE
        self.info_str = ''
        label = ttk.Label(self, text="ProductSchedule", font=controller.title_font)
        label.grid(row=0, column=0)
        #label.pack(side="top", fill="x", pady=10)
        button1 = ttk.Button(self, text="Layout",
                           command=lambda: controller.show_frame("Layout"))
        button2 = ttk.Button(self, text="WorkersAnalysis",
                            command=lambda: worker_graph.draw(self.factory, self.start_day.get(),self.end_day.get()))
        button3 = ttk.Button(self, text="MachinesAnalysis",
                            command=lambda: machine_graph.draw(self.factory, self.start_day.get(),self.end_day.get()))
        button4 = ttk.Button(self, text="HeatMap",
                            command=lambda: heatmap.draw(self.factory, self.start_day.get(),self.end_day.get()))
        button5 = ttk.Button(self, text="reload",
                           command=lambda: self.main())
        #button.pack()
        button5.grid(row=0, column=1, sticky=tk.W)
        button2.grid(row=0, column=6, sticky=tk.W)
        button3.grid(row=0, column=7, sticky=tk.W)
        button4.grid(row=0, column=8, sticky=tk.W)
        button1.grid(row=0, column=9, sticky=tk.W)
        #button1.grid(row=1, column=0, sticky=tk.W)
        #button2.grid(row=1, column=1, sticky=tk.W)
        
        #コンボボックス用ラベル
        self.comblavel1 = ttk.Label(self, text="StartDay")
        self.comblavel1.grid(row=0, column=2)
        #コンボボックスの配置
        self.start_day = tk.IntVar()
        if sec_to_timedelta_9h(self.factory.time).days >= 1:
            self.start_time = sec_to_timedelta_9h(self.factory.time).days
        else:
            self.start_time = 1
        self.time_range_start = [i for i in range(1, self.start_time)]
        self.combo1 =  ttk.Combobox(self, values=self.time_range_start, 
                              textvariable=self.start_day, postcommand=self.changeStartDay, width=4)
        #self.combo1.current(0)
        self.combo1.grid(row=0, column=3)
        
        #コンボボックス用ラベル
        self.comblavel2 = ttk.Label(self, text="EndDay")
        self.comblavel2.grid(row=0, column=4)
        #コンボボックスの配置
        self.end_day = tk.IntVar()
        if sec_to_timedelta_9h(self.factory.time).days >= 1:
            self.limit_time = sec_to_timedelta_9h(self.factory.time).days
        else:
            self.limit_time = 1
        self.time_range_end = [i for i in range(self.start_time, self.limit_time)]
        self.combo2 =  ttk.Combobox(self, values=self.time_range_end, 
                              textvariable=self.end_day, postcommand=self.changeEndDay, width=4)
        #self.combo2.current(0)
        self.combo2.grid(row=0, column=5)
        
        #インフォボックス配置
        #self.info_box = tk.Text(self, width=20, height=45, font=("",10), fg='red')
        self.info_box = tk.Text(self, width=20, height=45, font=("",10))
        self.info_box.grid(row=1, column=11)
        
        #self.geometry("800x600")
        self.block_x = 40 #1マスのx軸の長さpx
        self.block_y = 20 #1マスのy軸の長さpx

        #キャンバスの部品を作る
        self.canvas = tk.Canvas(
            self, width=900, height=600, bg='floral white')
        #self.canvas.pack(side='left') #キャンバスを配置
        self.canvas.grid(row=1, columnspan=10)
        #self.canvas.grid(columnspan=2, row=3, column=0)

        self.n=0
        self.start_x = 50
        self.start_y = 50
        self.end_y = 400
        self.raw = 30
        self.days = 40

        self.canvas.create_line(self.start_x, 0, self.start_x, self.end_y, tag='schedule')
        self.canvas.create_line(
            0,self.start_y-5,self.start_x+self.block_x*self.days,self.start_y-5)
        for i in range(self.days):
            self.canvas.create_line(
                self.start_x+(i+1)*self.block_x, 0, self.start_x+(i+1)*self.block_x, 
                self.end_y, fill='gray', tag='schedule')
            self.canvas.create_text(
                self.start_x+i*self.block_x+20, self.start_y-15, 
                text = f'{return_biz_day(self.BASE_DATE, i).month}/{return_biz_day(self.BASE_DATE, i).day}' 
                #text=str(i+1)
                )

        self.scroll_x = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.scroll_x.grid(row=2, columnspan=10, sticky="ew")
        #self.scroll_x.pack(side='bottom', anchor=tk.N)

        self.scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_y.grid(row=1, column=10, sticky="ns")
        #self.scroll_y.pack(side='left')
        self.canvas.configure(yscrollcommand=self.scroll_y.set, xscrollcommand=self.scroll_x.set)

        self.scroll_y2 = ttk.Scrollbar(self, orient="vertical", command=self.info_box.yview)
        self.scroll_y2.grid(row=1, column=12, sticky="ns")
        #self.scroll_y.pack(side='left')
        self.canvas.configure(yscrollcommand=self.scroll_y.set, xscrollcommand=self.scroll_x.set)

        #self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def main(self):
        self.canvas.delete('schedule')
        self.n=0
        plan = defaultdict(list)
        for product in self.factory.product_list:
            for fin in product.finished_process:
                if fin[2] > 0:
                    plan[fin[0][0]].append([product.product,fin])

        for k, v in plan.items():
            self.canvas.create_text(
                10, (self.start_y+self.n*self.raw)+self.block_y-self.block_y+5, 
                text=k, tag='schedule')
            v = sorted(v, key=lambda x:x[1][1])
            for process in v:
                self.canvas.create_rectangle(
                    self.start_x+(sec_to_timedelta_9h(process[1][1]).days)*self.block_x, 
                    self.start_y+self.n*self.raw, 
                    self.start_x+(sec_to_timedelta_9h(process[1][2]).days+1)*self.block_x, 
                    (self.start_y+self.n*self.raw)+self.block_y,
                    fill='coral1', tag='schedule')
                self.canvas.create_text(
                    self.start_x+(sec_to_timedelta_9h(process[1][2]).days+1)*self.block_x + 20, 
                    (self.start_y+self.n*self.raw)+self.block_y-10,
                    text=process[0], fill='navy', tag='schedule')
                self.n += 1
            self.canvas.create_line(
                0,(self.start_y+self.n*self.raw)-5, self.start_x+self.block_x*self.days,
                (self.start_y+self.n*self.raw)-5, tag='schedule')
        self.end_y = (self.start_y+self.n*self.raw)+self.block_y
        self.canvas.create_line(self.start_x, 0, self.start_x, self.end_y, tag='schedule')
        for i in range(self.days):
            self.canvas.create_line(
                self.start_x+(i+1)*self.block_x, 0, self.start_x+(i+1)*self.block_x, 
                self.end_y, fill='gray', tag='schedule')
            
        #インフォボックス更新
        self.info_box.delete('1.0', tk.END)
        self.info_box.insert('1.0', self.refresh_info())

    def changeStartDay(self):
        if sec_to_timedelta_9h(self.factory.time).days >= 1:
            self.start_time = sec_to_timedelta_9h(self.factory.time).days + 1
            if self.start_time > self.limit_time:
                    self.start_time = self.limit_time
        else:
            self.start_time = 1
        self.limit_time = self.end_day.get()
        self.combo1["values"] = [i for i in range(1, self.limit_time + 1)]
        self.star_time = self.start_day.get()
        
            
    def changeEndDay(self):
        if sec_to_timedelta_9h(self.factory.time).days >= 1:
            self.limit_time = sec_to_timedelta_9h(self.factory.time).days + 1
            if self.limit_time < self.start_time:
                    self.limit_time = self.start_time
        else:
            self.limit_time = 1
        self.start_time = self.start_day.get()
        self.combo2["values"] = [i for i in range(self.start_time, self.limit_time + 1)]
        self.limit_time = self.end_day.get()

    def refresh_info(self):
        #global info_str
        self.info_str = ''
        self.product_info = [['工期', f'計画開始日:{self.BASE_DATE.date()}', '---------------']]
        for product in self.factory.product_list:
            start_time = []
            end_time = []
            for process in product.finished_process:
                info = []
                start_time.append(process[1])
                end_time.append(process[2])
            if start_time and end_time:
                self.product_info.append(
                    [f'製品:{product.product}', 
                     f'加工開始:{return_biz_day(self.BASE_DATE, sec_to_timedelta_9h(start_time[0]).days).date()}', 
                     f'({sec_to_timedelta_9h(start_time[0]).days+1}日目)',
                     f'加工終了:{return_biz_day(self.BASE_DATE, sec_to_timedelta_9h(end_time[-1]).days).date()}',
                     f'({sec_to_timedelta_9h(end_time[-1]).days+1}日目)',
                     '---------------'
                    ]
                )        
 
        for lst in self.product_info:
            for note in lst:
                self.info_str += note + '\n'
            self.info_str += '\n'

        return self.info_str
