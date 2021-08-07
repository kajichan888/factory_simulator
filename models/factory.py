from models.machine import Machine
from models.worker import Worker
from models.product import Product
# import logging
import networkx as nx
import pandas as pd
# import functools
import configparser
import pickle
import pathlib

# from models.status import Wstatus
from models.status import Mstatus

# from utils.utils import route_to_move_list
# from utils.utils import shortest_path
# from utils.utils import shortest_path_length
from utils.utils import time_converter
from utils.data_utils import load_factory_list
# from data.position import POSITIONS
from data.position import PATH

# --------------------------------------------------
# configparserの宣言とiniファイルの読み込み
# --------------------------------------------------
config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')

START_TIME = config['DEFAULT']['START_TIME']

factory_file = config['DEFAULT']['factory_object']
factory_object_path = pathlib.Path('__file__')
factory_object_path /= '../'  # 1つ上の階層を指す
factory_object_path = factory_object_path.resolve() / factory_file

factory_list = config['DEFAULT']['factory_list']
factory_list_path = pathlib.Path('__file__')
factory_list_path /= '../'  # 1つ上の階層を指す
factory_list_path = factory_list_path.resolve() / factory_list

class Factory(object):

    def __init__(self):
        self.time = 0  # 稼働時間
        # self.step_time = step_time #1stepの秒数
        self.machine_list = []
        self.planed_machine = []
        # self.stoped_machines = []

        self.worker_list = []
        # self.waiting_workers = []

        self.product_list = []
        # self.product_dict = defaultdict(list)
        # self.done_prodcts = []
        self.g = nx.Graph()
        self.g.add_edges_from(PATH)

    def step(self, step_time, algorithm):
        """1単位時間を進める
        """
        algorithm(
            self.g, self.planed_machine, self.worker_list, self.time, step_time
        )
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
                row[0], row[1], row[2], row[3], row[4], row[5],
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
            ('P1', 30, 'TYPE_A', 17, 505, 'L1', 10, 5,1, 'M1', 5, 1, 1, 'M1', 10, 1, 1),
            ('P2', 20, 'TYPE_A', 13, 280, 'L2', 15, 5, 1, 'M3', 15, 1, 1),
            ('P3', 10, 'TYPE_B', 16, 200, 'L1', 100, 5, 1, 'M1', 5, 1, 1, 'M2', 20, 1, 2, 'M3', 15, 1, 1),
            ('P1', 100, 'TYPE_C', 17, 540, 'L1', 10, 5, 1, 'M1', 5, 1, 1, 'M1', 10, 1, 1)]
        pr = pd.DataFrame(products, columns=(
            'product', 'lot', 'type', 'diameter', 'length',
            'process-1', 'time-1', 'auto-1', 'repeat-1',
            'process-2', 'time-2', 'auto-2', 'repeat-2',
            'process-3', 'time-3', 'auto-3', 'repeat-3',
            'process-4', 'time-4', 'auto-4', 'repeat-4'))
        """
        lst = []
        for i in range(1, int((len(products.columns) - 5) / 4 + 1)):
            df = products[
                [
                    'product',
                    'process-{}'.format(i),
                    'time-{}'.format(i),
                    'auto-{}'.format(i),
                    'repeat-{}'.format(i)
                ]
            ].dropna()
            lst.append(df)
        dl = []
        for df in lst:
            for row in df.dropna().itertuples():
                d = {}
                d[row[0]] = [row[2], row[3], row[4], row[5]]
                dl.append(d)
        dd = {}
        for row in products.itertuples():
            dd[row[0]] = [row[1], row[2], row[3], row[4], row[5]]
        for dic in dl:
            for k, v in dic.items():
                dd[k].append(v)
        for i in range(len(dd)):
            product = Product(
                i, dd[i][0], dd[i][1], dd[i][2], dd[i][3], dd[i][4], dd[i][5:]
            )
            self.product_list.append(product)
        m = set()
        for product in self.product_list:
            for process in product.process:
                m.add(process[0])
        # 加工予定のある機械のリストを作成
        self.planed_machine = []
        for machine in self.machine_list:
            if machine.machine_name in m:
                self.planed_machine.append(machine)

    def set_product_to_machine(self, time):
        """product_listから加工工程を機械ごとに割り振る
        """
        for product in self.product_list:
            for machine in self.planed_machine:
                if product.raw_process and self.time >= product.receipt_time:
                    if (
                        product.raw_process[0][0] == machine.machine_name
                        and not product.processing and not machine.product
                    ):
                        # logging.info('ok')
                        product.set_process(time)
                        machine.planning(product)
                    else:
                        # logging.info('未計画の製品はありません')
                        pass

    def finish_one_process(self, product_number):
        """product_listの中のProductのprocessを一つ終了させる

        product_number: processを一つ終了させる製品の番号
        """
        for product in self.product_list:
            if product.product_number == product_number:
                if not product.processing: # processingが空なら
                    # Product.processingに加工情報を格納, raw_processからpop(0)
                    product.set_process(0)
                    # 機械の設定を登録
                    for machine in self.machine_list:
                        if machine.machine_name == product.processing[0]:
                            machine.sub_product_type = product.product_type # 最後に加工した製品タイプ
                            machine.sub_diameter = product.diameter # 最後に加工した製品径
                            machine.sub_length = product.length # 最後に加工した製品長
                # 終了処理 Product.finished_processに加工情報を格納, Product.processingを空に
                product.finisher(0)

    def proceed_process(self, product_number, sub_lot):
        """
        加工を進める
        product_number: 加工を進める製品の加工番号
        sub_lot: 加工数
        """
        # まだ機械に割り当てれれていない場合
        for product in self.product_list:
            for machine in self.machine_list:
                if product.product_number == product_number and not product.processing and machine.machine_name == product.raw_process[0][0] and not machine.product:
                    # Product.processingに加工情報を格納, raw_processからpop(0)
                    product.set_process(0)
                    # 機械の設定を登録
                    for machine in self.machine_list:
                        if machine.machine_name == product.processing[0] and not machine.product:
                            machine.planning(product)
                            machine.sub_lot = sub_lot
                            machine.status = Mstatus.STOP
        # 機械に割り当て済みの場合
        for product in self.product_list:
            if product.product_number == product_number and product.processing:
                # 機械の設定を登録
                for machine in self.machine_list:
                    if machine.machine_name == product.processing[0] and machine.product == product:
                        if sub_lot > product.lot:
                            sub_lot = product.lot
                        machine.planning(product)
                        machine.sub_lot = sub_lot
                        machine.status = Mstatus.STOP

    def display_plan(self):
        """product_listをDataFrameにして出力する
        """
        lst = []
        for product in self.product_list:
            l = [
                product.product_number, product.product, product.lot,
                product.product_type, product.diameter, product.length
            ]
            for process in product.raw_process:
                for info in process:
                    l.append(info)
            lst.append(l)

        max_processes = ''
        for _products in lst:
            if len(_products) > len(max_processes):
                max_processes = _products
        columns = ['No.', 'product', 'lot', 'type', 'diameter', 'length']
        for i in range(1, int((len(max_processes) - 6) / 4 + 1)):
            columns.append(f'process-{i}')
            columns.append(f'time-{i}')
            columns.append(f'auto-{i}')
            columns.append(f'repeat-{i}')

        df = pd.DataFrame(lst, columns=tuple(columns))
        # df = df.set_index('No.')
        print(df)

    def display_machine_status(self):
        lst = []
        for machine in self.planed_machine:
            sub_product_type = machine.sub_product_type
            sub_diameter = machine.sub_diameter
            sub_length = machine.sub_length
            if not machine.product:
                product = None
                product_number = None
                lot = None
                auto = None
                repeat = None
            else:
                product = machine.product.product
                product_number = machine.product.product_number
                lot = machine.process[0]
                auto = machine.process[2]
                repeat = machine.process[3]
                
            l = [machine.machine_name, product_number, product, lot, machine.sub_lot, auto, repeat, machine.status, sub_product_type, sub_diameter, sub_length]
            lst.append(l)
        df = pd.DataFrame(lst, columns=('machine','product_No.', 'product', 'lot', 'sub_lot', 'auto', 'repeat', 'status', 'sub_product_type', 'sub_diameter', 'sub_length'))
        print(df)

    def save_object(self):
        """factory_objectをデフォルトのFactoryオブジェクトとして保存
        """
        # バイナリで保存
        with open(factory_object_path, 'wb') as p:
            pickle.dump(self, p)

    def append_factory_list(self):
        """Factoryオブジェクトをデフォルトのfactory_listに追加する
        """
        # 読み込み
        factory_list = load_factory_list()
        factory_list.append(self)
        #保存
        with open(factory_list_path, 'wb') as p:
            pickle.dump(factory_list, p)
