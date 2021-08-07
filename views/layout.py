import numpy as np
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
from utils.utils import return_biz_day

from utils.utils import sec_to_timedelta_9h

from models.factory import Factory
from models.status import Mstatus
from models.status import Wstatus

from data.map import WALL
from data.position import POSITIONS
from data.map import MACHINE_POSITION

from algorithm.algorithm_ver02 import continue_set_up


class Layout(tk.Frame):

    def __init__(self, parent, controller, factory_obj, BASE_DATE):
        ttk.Frame.__init__(self, parent)
        self.controller = controller
        self.factory = factory_obj
        self.BASE_DATE = BASE_DATE
        self.speed = 0
        self.idx = 0
        self.info_str = ''
        self.info_str_bottom =''
        label = ttk.Label(self, text="Factory", font=controller.title_font)
        #label.pack(side="top", fill="x", pady=1)
        label.pack()

        button1 = ttk.Button(self, text="ProductSchedule",
                            command=lambda: controller.show_frame("ProductSchedule"))
        #button2 = ttk.Button(self, text="GraphicalAnalysis",
        #                    command=lambda: self.show_graph(factory, v.get()))
        button1.pack()
        #button2.pack()
        
        self.block_x = 20 #1マスのx軸の長さpx
        self.block_y = 20 #1マスのy軸の長さpx
        self.idx = 0
        self.speed = 2
        
        #インフォボックスの配置
        self.info_box = tk.Text(self, width=40, height=45)
        self.info_box.pack(side=tk.RIGHT, anchor=tk.N)

        #workerの凡例
        self.worker_color = [
            'SeaGreen1', 'orange', 'HotPink1', 'purple1',
            'PaleGreen3', 'coral', 'VioletRed1', 'MediumPurple1']
        
        pitch = 80
        i=0
        n=0
        self.top_legends = tk.Canvas(self, width=802, height=22, bg='white')
        self.top_legends.pack(side=tk.TOP)

        for worker in self.factory.worker_list:
            self.top_legends.create_oval(2+i+3, 2+3, 22+i-3, 22-3, 
                                    fill=self.worker_color[n], 
                                    tag=worker.name)
            self.top_legends.create_text(22+i+len(worker.name)*5, 12, 
                                    text=worker.name,
                                    font=('', 10))
            i += pitch
            n +=1        
        
        #キャンバスの部品を作る
        self.canvas = tk.Canvas(self, width=802, height=422, bg='floral white')
        self.canvas.pack(side=tk.TOP) #キャンバスを配置

        self.machine_color = {Mstatus.EMPUTY : 'white', 
                              Mstatus.NOT_SET : 'gray', 
                              Mstatus.SETTING : 'yellow',
                              Mstatus.STOP : 'yellow', 
                              Mstatus.RUNNING : 'blue', 
                              Mstatus.TROUBLE : 'red'
                             } 

        #建物配置wall[1][1]
        for wall in WALL:
            self.canvas.create_rectangle(
                wall[0][0]*self.block_x, wall[1][0]*self.block_y, 
                wall[0][1]*self.block_x+2, wall[1][1]*self.block_y+2, fill='gray')

        meeting_room = [[0, 16], [50, 10]] #[[座標x,y],[文字オフセットx,y]]
        office = [[3, 0], [25, 10]]
        stockyard = [[13, 14], [35, 10]]
        #ミーティングルーム
        self.canvas.create_text(meeting_room[0][0]*self.block_x + meeting_room[1][0], 
                                meeting_room[0][1]*self.block_y + meeting_room[1][1], 
                                text='MEETING ROOM')
        #事務室
        self.canvas.create_text(office[0][0]*self.block_x + office[1][0], 
                                office[0][1]*self.block_y + office[1][1], 
                                text='OFFICE')
        #資材置き場
        self.canvas.create_text(stockyard[0][0]*self.block_x + stockyard[1][0], 
                                stockyard[0][1]*self.block_y + stockyard[1][1], 
                                text='STOCKYARD')
        self.canvas.create_rectangle(stockyard[0][0]*self.block_x,
                                     stockyard[0][1]*self.block_y, 
                                     19*self.block_x,
                                     21*self.block_y)
        #資材棚
        self.canvas.create_rectangle(19*self.block_x,
                                     9.5*self.block_y, 
                                     22.5*self.block_x,
                                     12*self.block_y)
        self.canvas.create_text(19*self.block_x + 20, 
                                9.5*self.block_y + 10, 
                                text='RACK')
        #コンテナ
        self.canvas.create_rectangle(15*self.block_x,
                                     9.5*self.block_y, 
                                     17*self.block_x,
                                     10.5*self.block_y)
        
        #機械配置
        self.machine_status = {}
        for machine in self.factory.machine_list:
            #canvas.delete(machine.machine_name)
            dot = []
            for x, y in MACHINE_POSITION[machine.machine_name][0]:
                dot.append([x*self.block_x, y*self.block_y])
            self.canvas.create_polygon(*dot, fill=self.machine_color[machine.status],
                                  outline='black',
                                  tag=machine.machine_name
                                   )
            self.canvas.create_text(
                dot[0][0]+MACHINE_POSITION[machine.machine_name][1][0], 
                dot[0][1]+MACHINE_POSITION[machine.machine_name][1][1], 
                text=machine.machine_name)
            self.machine_status[machine.machine_name] = machine.status

        self.men = tk.Menu(self) #メニューバー作成
        self.controller.config(menu=self.men) #メニューバーを画面にセット

        #メニューに親メニュー(program)を作成
        menu_prg = tk.Menu(self)
        self.men.add_cascade(label='program', menu=menu_prg)

        #親メニューに子メニュー(start, close)を追加する
        menu_prg.add_command(label='start', command=self.start)
        menu_prg.add_command(label='stop', command=self.stop)
        menu_prg.add_command(label='close', command=self.controller.destroy)

        #下部テキストボックスを配置
        self.info_box_bottom = tk.Text(self, width=100, height=8)
        self.info_box_bottom.pack(side=tk.BOTTOM, anchor=tk.W)

        #スピード調整バー(scale)配置
        self.val_speed = tk.IntVar()
        self.val_speed.set(2)
        s = tk.Scale(self, label = 'speed', orient = 'h',
                   from_ = 1, to = 10, length = 400, variable = self.val_speed,
                   command = self.change_speed)
        self.speed = self.val_speed.get()
        s.pack(side=tk.LEFT)

        #steptime選択ラジオボタン作成
        self.radio_txt = ttk.Label(self, text='step time')
        self.radio_txt.pack(side=tk.LEFT)
        self.rval = tk.DoubleVar()
        self.rval.set(0.1)
        self.radio = [None]*5
        self.radio_txt = ['0.1sec', '1sec', '10sec', '1min', '5min']
        self.radio_val = [0.1, 1.0, 10, 60, 300]
        for i in range(5):
            self.radio[i] = ttk.Radiobutton(
                self, text=self.radio_txt[i], 
                variable=self.rval, value=self.radio_val[i])
            self.radio[i].pack(side=tk.LEFT)
 
    def main(self):
        #global idx
        #global speed
        #global info_str
        self.speed = self.val_speed.get()
        n = 0
        self.info_str = ''
        self.info_str_bottom = ''

        for worker in self.factory.worker_list:
            if worker.status == Wstatus.ON_BREAK:
                self.canvas.delete(worker.name)
            if worker.status == Wstatus.MOVE:
                self.canvas.delete(worker.name)
                if type(worker.position) is str and worker.position in POSITIONS:
                    worker.position = POSITIONS[worker.position]
                if worker.position != []:
                    self.canvas.create_oval(worker.position[0]*self.block_x, worker.position[1]*self.block_y, 
                                    (worker.position[0] + 1)*self.block_x, (worker.position[1] + 1)*self.block_x, 
                                    fill=self.worker_color[n], tag=worker.name)
                    for k, v in POSITIONS.items():
                        if np.all(worker.position == v):
                            worker.position = k
            n += 1

        #機械配置
        for machine in self.factory.planed_machine:
            if machine.status != self.machine_status[machine.machine_name]:
                self.canvas.delete(machine.machine_name)
                dot = []
                for x, y in MACHINE_POSITION[machine.machine_name][0]:
                    dot.append([x*self.block_x, y*self.block_y])
                self.canvas.create_polygon(*dot, fill=self.machine_color[machine.status],
                                      outline='black',
                                      tag=machine.machine_name
                                       )
                self.canvas.create_text(
                    dot[0][0]+MACHINE_POSITION[machine.machine_name][1][0], 
                    dot[0][1]+MACHINE_POSITION[machine.machine_name][1][1], 
                    text=machine.machine_name)
                self.machine_status[machine.machine_name] = machine.status

        #Factoryの時間を進める
        self.factory.step(self.rval.get(), continue_set_up)

        #インフォボックス更新
        self.info_box.delete('1.0', tk.END)
        self.info_box.insert('1.0', self.refresh_info())

        self.info_box_bottom.delete('1.0', tk.END)
        self.info_box_bottom.insert('1.0', self.refresh_info_bottom())


        p = []
        for product in self.factory.product_list:
            if product.raw_process:
                p.append(product)
        for machine in self.factory.machine_list:
            if machine.status != Mstatus.EMPUTY:
                p.append(machine)
        #for worker in self.factory.worker_list:
        #    if worker.status != Wstatus.WAIT:
        #        p.append(worker)
        #    if worker.action_list:
        #        p.append(worker)
        if not p:
            self.idx = 0
            #最後に機械を再描画
            for machine in self.factory.planed_machine:
                self.canvas.delete(machine.machine_name)
                dot = []
                for x, y in MACHINE_POSITION[machine.machine_name][0]:
                    dot.append([x*self.block_x, y*self.block_y])
                self.canvas.create_polygon(*dot, fill=self.machine_color[machine.status],
                                        outline='black',
                                        tag=machine.machine_name
                                        )
                self.canvas.create_text(
                    dot[0][0]+MACHINE_POSITION[machine.machine_name][1][0], 
                    dot[0][1]+MACHINE_POSITION[machine.machine_name][1][1], 
                    text=machine.machine_name)
                self.machine_status[machine.machine_name] = machine.status


        if self.idx == 1:
            self.after((100//self.speed), self.main)

    def start(self):
        #global idx
        self.idx = 1
        self.main()

    def stop(self):
        #global idx
        self.idx = 0

    def change_speed(self, n):
        pass

    def refresh_info(self):
        #global info_str
        self.info_str = ''

        d = return_biz_day(self.BASE_DATE, sec_to_timedelta_9h(self.factory.time).days).date()
        tm = sec_to_timedelta_9h(self.factory.time)

        self.info_str += f'開始日  :{self.BASE_DATE.date()}' + ' ' + self.BASE_DATE.date().strftime('%A')+ '\n'
        self.info_str += f'日付    :{d}' + ' ' + d.strftime('%A') + '\n'
        self.info_str += f'稼働時間:{self.factory.time}秒' + '\n'
        self.info_str += f'稼働時間(8+1h):{tm}' + '\n' +'\n'
        #self.info_str += '稼働時間(24h):' + time2.strftime('%d %H%M%S') + '\n' +'\n'

        self.machine_info = []
        for machine in self.factory.planed_machine:
            if machine.status != Mstatus.EMPUTY:
                info = []
                info.append('機械名:{}'.format(machine.machine_name))
                info.append('機械タイプ:{}'.format(machine.machine_type))
                info.append('ステータス:{}'.format(machine.status))
                if machine.product:
                    info.append('加工品目:{}'.format(machine.product.product))
                    info.append('sub_lot:{}'.format(machine.sub_lot))
                if machine.worker_obj:
                    info.append('作業者:{}'.format(machine.worker_obj.name))
                self.machine_info.append(info)

        for lst in self.machine_info:
            for note in lst:
                self.info_str += note + '\n'
            self.info_str += '\n'

        self.worker_info = []
        for worker in self.factory.worker_list:
            info = []
            info.append('作業者:{}'.format(worker.name))
            info.append('ステータス:{}'.format(worker.status))
            info.append('action_list:{}'.format(worker.action_list))
            if worker.machine_obj:
                info.append('作業機械:{}'.format(worker.machine_obj.machine_name))
            self.worker_info.append(info)

        for lst in self.worker_info:
            for note in lst:
                self.info_str += note + '\n'
            self.info_str += '\n'

        return self.info_str            
            
    def refresh_info_bottom(self):
        #global info_str_bottom
        self.info_str_bottom = ''

        for product in self.factory.product_list:
            self.info_str_bottom += f'製品名:{product.product}'
            self.info_str_bottom += f'所要数:{product.lot}'
            self.info_str_bottom += f'加工中:{product.processing}'
            self.info_str_bottom += f'加工終了:{product.finished_process}' + '/'

        return self.info_str_bottom
    