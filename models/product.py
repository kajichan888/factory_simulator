from models.status import Pstatus
import copy


class Product(object):

    def __init__(self, number, product, lot, product_type, diameter, length, process):
        self.receipt_time = 0 # 鋼材、素材の入荷時間 days*9*60*60
        self.product_number = number
        self.product = product  # 製品名
        self.status = Pstatus.MATERIAL  # 製品の状態
        self.lot = lot  # 所要加工数
        self.product_type = product_type  # 製品タイプ 'HEX', 'SDS'等
        self.diameter = diameter  # 製品径
        self.length = length  # 製品長
        # self.count = 0  # 加工済み部品数
        self.process = process  # 工程リスト[[機械',サイクルタイム, 連続運転個数, 工数], [...]]
        self.raw_process = copy.copy(process)
        self.processing = []  # 加工中のリスト[機械',サイクルタイム, 連続運転個数,工数]
        self.start_time = 0  # processの開始時間を格納する
        self.finished_process = []  # 加工済みのプロセスのリスト[[[機械',サイクルタイム, 工数],開始時間,終了時間], [[...]]]

    def set_process(self, time):
        if not self.processing:
            self.processing = self.raw_process.pop(0)
            self.start_time = time

    def finisher(self, end_time):
        """加工中のプロセスを加工済みのプロセスのリストに登録する関数
        """
        self.finished_process.append(
            [self.processing, self.start_time, end_time]
        )
        self.processing = []
        self.start_time = 0

    def count_up(self):
        # self.count += 1
        # print('所要部品数:{} 加工済み:{}'.format(self.lot, self.count))
        pass

    def step(self):
        """1単位時間を進める
        """
        pass
