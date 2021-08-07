import copy
import logging

from models.status import Mstatus


class Machine(object):

    def __init__(
        self, machine, position, typ, setup, setting,
        same_type, same_diameter, same_length,
        error_rate, reset, trouble_rate, repair
    ):
        self.machine_name = machine
        if type(position) == int:
            self.position = str(position)
        else:
            self.position = position
        self.machine_type = typ  # 機械の種類
        self.setup = setup  # 段取り時間
        self.sub_setup = 0  # 段取り時間初期設定
        self.setting = setting  # 取付時間
        self.sub_setting = 0  # 取付時間初期設定

        # same_type + same_diameter + same_length=1 になるように
        self.same_type = same_type  # 同タイプの時の段取り短縮比率
        self.same_diameter = same_diameter  # 同径の時の段取り短縮比率
        self.same_length = same_length  # 同長の時の段取り短縮比率

        self.error_rate = error_rate  # 不具合発生確率
        self.reset = reset  # 不具合復旧にかかる時間
        self.trouble_rate = trouble_rate  # 故障発生確率
        self.repair = repair  # 修理にかかる時間
        self.status = Mstatus.EMPUTY

        self.sub_product_type = None  # 最後に加工した製品タイプ
        self.sub_diameter = None  # 最後に加工した製品径
        self.sub_length = None  # 最後に加工した製品長

        self.sub_status = None  # 故障、エラー前の状態を保存
        self.sub_worker_obj = None  # 故障、エラー前の作業者を保存

        # 故障している期間 [[start_time, end_time], [80, 20000], [],...]
        self.trouble_schedule = []

        self.product = None
        self.process = []  # 加工中の製品　例 [所要加工数,サイクルタイム, 連続自動運転, 工数]
        self.worker_obj = None

        self.sub_lot = 0  # 加工済み部品数
        self.sub_auto = 0  # 連続運転のカウント
        self.sub_kousu = 1  # 工数のカウントを格納
        self.sub_cycle_time = 0  # 加工サイクルのカウントを格納

    def planning(self, product_obj):
        """self.productに加工中の製品を格納する
        """
        if not self.product:
            self.product = product_obj
            self.process = [
                product_obj.lot,
                product_obj.processing[1],
                product_obj.processing[2],
                product_obj.processing[3]
            ]
            self.status = Mstatus.NOT_SET

    def set_work(self, worker):
        """ワークを機械にセットする、セットアップ作業を開始する
        """
        self.worker_obj = worker
        self.status = Mstatus.SETTING

    def set_up(self):
        """機械を設定する
        """
        if self.status == Mstatus.SETTING and self.product:
            self.status = Mstatus.STOP
            # 機械の設定を登録する
            self.sub_product_type = self.product.product_type
            self.sub_diameter = self.product.diameter
            self.sub_length = self.product.length

            self.worker_obj = None
            logging.info('{}:セッティングが完了しました'.format(self.machine_name))
        else:
            logging.warning('{}:セッティングできません'.format(self.machine_name))

    def set_trouble_schedule(self, start_time, end_time):
        """故障するスケジュールを設定
        """
        self.trouble_schedule.append([start_time, end_time])

    def break_down(self):
        """機械を故障させる
        """
        self.sub_status = copy.copy(self.status)
        # コピーしたworkerオブジェクトは元のworkerオブジェクトとは別物になるので取り扱い注意
        self.sub_worker_obj = copy.copy(self.worker_obj)
        self.status = Mstatus.TROUBLE

    def reset_status(self):
        """エラーを復旧する
        """
        self.status = copy.copy(self.sub_status)
        # コピーしたworkerオブジェクトは元のworkerオブジェクトとは別物になるので取り扱い注意
        self.worker_obj = copy.copy(self.sub_worker_obj)
        self.sub_status = None
        self.sub_worker_obj = None

    def check_status(self, factory_time):
        """ステータスをチェックする
           故障のスケジュールをチェックする
        """
        if self.trouble_schedule:
            count = 0
            for lst in self.trouble_schedule:
                if lst[0] <= factory_time <= lst[1]:
                    count += 1
                else:
                    pass
            if count > 0 and self.status != Mstatus.TROUBLE:
                self.break_down()
            elif count == 0 and self.status == Mstatus.TROUBLE:
                self.reset_status()
            else:
                pass
        else:
            pass

    def run(self):
        if self.process and self.status == Mstatus.SETTING:
            self.status = Mstatus.RUNNING
            self.worker_obj = None
            logging.info('{}:稼働します'.format(self.machine_name))
        elif self.status == Mstatus.NOT_SET:
            logging.info('{}:セッティングが完了していません'.format(self.machine_name))
        elif self.status == Mstatus.RUNNING:
            logging.info('{}:すでに稼働しています'.format(self.machine_name))
        else:
            logging.info('{}:計画がありません'.format(self.machine_name))

    def step(self, step_time, factory_time):
        """1単位時間を進める
        """
        self.check_status(factory_time)

        if self.product:
            if (
                self.sub_lot >= self.process[0]  # lot
                and self.sub_kousu >= self.process[3]  # 工数
            ):
                # 加工終了
                self.product.finisher(factory_time)
                self.process = []
                self.product = None
                self.sub_cycle_time = 0
                self.sub_lot = 0
                self.sub_auto = 0
                self.sub_kousu = 1
                self.status = Mstatus.EMPUTY
                logging.info('{}:加工完了'.format(self.machine_name))
            elif self.sub_lot >= self.process[0]:  # lot
                self.sub_kousu += 1
                self.sub_cycle_time = 0
                self.sub_lot = 0
                self.sub_auto = 0
                self.status = Mstatus.NOT_SET
                logging.info('{}:工数終了'.format(self.machine_name))
            elif self.sub_cycle_time >= self.process[1] * 60:  # サイクルタイム
                self.sub_lot += 1
                self.sub_cycle_time = 0
                self.sub_auto += 1
                if self.sub_auto >= self.process[2]:  # 連続運転
                    self.sub_auto = 0
                    self.status = Mstatus.STOP
                    logging.info('{}:連続運転終了'.format(self.machine_name))
                logging.info('{}:サイクル完了'.format(self.machine_name))
            elif self.status == Mstatus.RUNNING:
                self.sub_cycle_time += step_time
                logging.debug('{}:サイクルタイム1単位進行'.format(self.machine_name))
            else:
                logging.info('{}:停止中です'.format(self.machine_name))
        else:
            logging.info('{}:計画がありません'.format(self.machine_name))
