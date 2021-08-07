from models.machine import Machine
from models.worker import Worker
from models.product import Product
import logging
import networkx as nx
import functools

from models.status import Wstatus
from models.status import Mstatus

from utils.utils import route_to_move_list
from utils.utils import shortest_path
from utils.utils import shortest_path_length
from utils.utils import time_converter

from data.position import POSITIONS
from data.position import PATH

START_TIME = '8:00'

class Factory(object):
    
    def __init__(self):
        self.time = 0 #稼働時間
        #self.step_time = step_time #1stepの秒数
        self.machine_list = []
        self.planed_machine = []
        #self.stoped_machines = []
        
        self.worker_list = []
        #self.waiting_workers = []
        
        self.product_list = []
        #self.product_dict = defaultdict(list)
        #self.done_prodcts = []
        self.g = nx.Graph()
        self.g.add_edges_from(PATH)
        
    def step(self,step_time, algorithm):
        """1単位時間を進める
        """
        algorithm(self.g, self.planed_machine, self.worker_list, self.time, step_time)
        self.set_product_to_machine(self.time)

        for machine in self.planed_machine:
            machine.step(step_time, self.time)
        for worker in self.worker_list:
            worker.step(step_time, self.time)

        self.time += step_time
        
    def deploy(self, workers):
        """DataFrameから作業者オブジェクトのリストを作成する
        """
        for row in workers.itertuples():
            arrive = time_converter(START_TIME, row[6])
            leave = time_converter(START_TIME, row[7])
            worker = Worker(
                row[1], row[2], row[3], row[4], row[5], 
                arrive, leave, row[8], row[8])
            self.worker_list.append(worker)

    def set_machines(self, machines):
        """DataFrameから機械オブジェクトのリストを作成する
        """
        for row in machines.itertuples():
            machine = Machine(
                row[1], row[2], row[3], row[4], row[5], 
                row[6], row[7], row[8], 
                row[9], row[10], row[11], row[12])
            self.machine_list.append(machine)
            
    def planning(self, products):
        """DataFrameから計画オブジェクトのリストを作成する
        
        sample:
        products = [
            ('P1', 30, 'L1', 10, 5,1, 'M1', 5, 1, 1, 'M1', 10, 1, 1), 
            ('P2', 20, 'L2', 15, 5, 1, 'M3', 15, 1, 1), 
            ('P3', 10, 'L1', 100, 5, 1, 'M1', 5, 1, 1, 'M2', 20, 1, 2, 'M3', 15, 1, 1), 
            ('P1', 100, 'L1', 10, 5, 1, 'M1', 5, 1, 1, 'M1', 10, 1, 1)]
        pr = pd.DataFrame(products, columns=(
            'product', 'lot', 
            'process-1', 'time-1', 'auto-1', 'repeat-1', 
            'process-2', 'time-2', 'auto-2', 'repeat-2', 
            'process-3', 'time-3', 'auto-3', 'repeat-3', 
            'process-4', 'time-4', 'auto-4', 'repeat-4'))
        """
        lst = []
        for i in range(1, int((len(products.columns) - 2) / 4 + 1)):
            df = products[['product', 'process-{}'.format(i), 'time-{}'.format(i), 'auto-{}'.format(i), 'repeat-{}'.format(i)]].dropna()
            lst.append(df)
        dl = []
        for df in lst:
            for row in df.dropna().itertuples():
                d = {}
                d[row[0]] = [row[2], row[3], row[4], row[5]]
                dl.append(d)
        dd = {}
        for row in products.itertuples():
            dd[row[0]] = [row[1], row[2]]
        for dic in dl:
            for k, v in dic.items():
                dd[k].append(v)
        for i in range(len(dd)):
            product = Product(dd[i][0], dd[i][1], dd[i][2:])
            self.product_list.append(product)
        m = set()
        for product in self.product_list:
            for process in product.process:
                m.add(process[0])
        for machine in self.machine_list:
            if machine.machine_name in m:
                self.planed_machine.append(machine)

    def set_product_to_machine(self, time):
        """product_listから加工工程を機械ごとに割り振る
        """
        for product in self.product_list:
            for machine in self.planed_machine:
                if product.raw_process:
                    if product.raw_process[0][0] == machine.machine_name and not product.processing and not machine.product:
                            logging.info('ok')
                            product.set_process(self.time)
                            machine.planning(product)
                    else:
                        #logging.info('未計画の製品はありません')
                        pass

"""
    def make_path(self, path):
        """"""pathからグラフオブジェクトを作成する
        """"""
        self.g = nx.Graph()
        self.g.add_edges_from(path)
        """