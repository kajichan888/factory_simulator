import copy
# import time
import numpy as np
import functools
import logging
import configparser

from data.position import POSITIONS

from models.task import Schedule
# from utils.utils import coord_move_list_from_points ->algorithmで処理するので不要
from models.status import Wstatus
from models.status import Mstatus

from utils.utils import seek_near_point
from utils.utils import time_converter
from utils.utils import sec_to_timedelta_9h

# --------------------------------------------------
# configparserの宣言とiniファイルの読み込み
# --------------------------------------------------
config_ini = configparser.ConfigParser()
config_ini.read('config.ini', encoding='utf-8')

START_TIME = config_ini['DEFAULT']['START_TIME']


class Worker(object):
    def __init__(
            self, number, name, age, sex, m_speed, w_speed,
            arrive, leave, position, default_position):
        self.number = number
        self.name = name
        self.age = age
        self.sex = sex
        self.m_speed = m_speed  # 移動速度倍率(標準1.0 例0.8標準より遅い、1.2標準より早い)
        self.w_speed = w_speed  # 作業速度倍率(標準1.0 例0.8標準より遅い、1.2標準より早い)
        self.arrive = arrive  # 出勤時間
        self.leave = leave  # 退勤時間
        self.charge_list = []  # 担当機械を格納

        self.attendance = False  # 勤務中:True 勤務時間外:False
        self.sum_attendance_time = 0  # 勤務時間累計
        self.attendance_record = []  # 出退勤記録 [[0, 28800], [30000, 58800], ...]
        self.sub_attendance_record = []  # 1日日の出退勤記録 [0, 28800]

        self.walk_time = 1  # 1マス移動するのにかかる時間(秒)
        self.sub_walk_time = 0  # 1マス移動するときのカウントを格納
        self.move_list = []  # 例[[1, 0], [1, 0], [0, 1]....]
        self.walking_command = []  # 例[1, 0]

        self.machine_obj = None  # 作業する対象のオブジェクトを格納
        self.work_time = 0  # 割り当て作業に要する時間
        self.sub_work_time = 0  # 割り当て作業のカウントを格納

        self.action_list = []  # [fancA, fancB,...]
        self.record = []  # 作業内容の記録[['作業内容','対象機械','開始時間','終了時間'],[...],[...]]
        self.sub_record = []  # recordに格納する一時リスト
        if type(position) == int:
            self.position = str(position)
        else:
            self.position = position
        if type(default_position) == int:
            self.default_position = str(default_position)
        else:
            self.default_position = default_position
        
        self.status = Wstatus.WAIT

        self.schedule = []  # [Schedule1, Schedule2, Schedule3, ...]
        self.task_obj = None  # 実行中のタスクオブジェを格納

    def append_action(self, action):
        self.action_list.append(action)  # move(), work()等のfancthonを格納

    def insert_action(self, action):
        self.action_list.insert(0, action)  # move, work等のactionを先頭に挿入

    def record_interrupt(self, factory_time):  # 強制レコード
        if len(self.sub_record) == 3:
            self.sub_record.append(factory_time)
            self.record.append(self.sub_record)
            self.sub_record = []

    def return_attendance_time(self, start_time, end_time, factory_time):
        """開始時間:start_time, 終了時間:end_time
        　 間の出勤時間を返す
        """
        new_rec = copy.copy(self.attendance_record)
        if self.sub_attendance_record:
            new_sub_rec = copy.copy(self.sub_attendance_record)
            if len(new_sub_rec) == 1 and new_sub_rec[0] <= end_time:
                new_sub_rec.append(factory_time)
                new_rec.append(new_sub_rec)

        if end_time >= factory_time:
            end_time = factory_time
        sum_time = 0

        for rec in new_rec:
            if rec[0] >= start_time and rec[1] <= end_time:
                sum_time += (rec[1] - rec[0])
            elif rec[0] <= start_time and (start_time <= rec[1] <= end_time):
                sum_time += (rec[1] - start_time)
            elif (start_time <= rec[0] <= end_time) and rec[1] >= end_time:
                sum_time += (end_time - rec[0])
            elif rec[0] <= start_time and rec[1] >= end_time:
                sum_time += (end_time - start_time)
        return sum_time

    def set_schedule(self, schedule_dataframe):
        """DataFrameからスケジュールをリストに変換し、self.scheduleに登録する
        8:00 -> 0
        9:00 -> 60*60という具合に秒に変換する必要
        timedelta(time).seconds で秒を取得できるので一日ごとの秒でいい
        """
        for row in schedule_dataframe.itertuples():
            task = row[1]
            place = row[3]
            position = row[4]
            worker = self
            week = row[2]
            start = time_converter(START_TIME, row[5])
            if start < self.arrive:
                start = self.arrive
            end = time_converter(START_TIME, row[6])
            if end > self.leave:
                end = self.leave
            time = end - start
            schedule_obj = Schedule(
                task, position, time, worker, place, week, start)
            self.schedule.append(schedule_obj)

    def set_charge_list(self, charge_list, machine_obj_list):
        """charge_list から self.charge_list に担当機械を登録
           factory.machine_listにないものは登録しない
        """
        for machine in charge_list:
            for machine_obj in machine_obj_list:
                if (
                    machine_obj.machine_name == machine
                    and machine not in self.charge_list
                ):
                    self.charge_list.append(machine)

    """
    def some_action(self, step_time):
        logging.info('{} some action done!'.format(self.name))
        time.sleep(1)
    """

    def reset_position(self):
        self.position = copy.copy(self.default_position)

    def move(self, destination, move_list, step_time, factory_time):
        self.move_list = move_list
        # self.sub_walk_time = 0
        # if type(self.position) is str and self.position not in POSITIONS:
        #     self.reset_position()
        if type(self.position) is str and self.position in POSITIONS:
            self.position = np.array(POSITIONS.get(self.position))
        self.status = Wstatus.MOVE
        if not self.sub_record:
            self.sub_record = ['move', destination, factory_time]
            logging.info('{}:現在地{}'.format(self.name, self.position))
            logging.info('{}:移動をセットしました'.format(self.name))
        if not self.walking_command and not self.move_list:
            logging.info('{}:移動完了しました'.format(self.name))
            self.status = Wstatus.WAIT
            logging.info('{}:{}'.format(self.name, self.status))
            self.position = seek_near_point(self.position, POSITIONS)
            self.sub_record.append(factory_time)
            self.record.append(self.sub_record)
            self.sub_record = []
            logging.info('{}:現在地{}'.format(self.name, self.position))
        elif not self.walking_command:
            self.walking_command = self.move_list.pop(0)
            logging.debug('POP')
            self.action_list.insert(0, functools.partial(
                self.move, destination, self.move_list))
        else:
            if self.sub_walk_time < self.walk_time:
                self.sub_walk_time += step_time*self.m_speed
                logging.debug('{}:移動1単位進行'.format(self.name))
                self.action_list.insert(0, functools.partial(
                    self.move, destination, self.move_list))
            else:
                self.sub_walk_time = step_time
                self.position += np.array(self.walking_command)
                if move_list:
                    self.walking_command = self.move_list.pop(0)
                else:
                    self.walking_command = []
                logging.info('{}:現在地{}'.format(self.name, self.position))
                self.action_list.insert(0, functools.partial(
                    self.move, destination, self.move_list))

    def warp(self, destination, destination_position, step_time, factory_time):
        self.status = Wstatus.MOVE
        self.position = destination_position
        self.record.append(
            ['move', destination, factory_time, factory_time])

    def machine_run(self, machine_obj, step_time, factory_time):
        """ワークを取り付け、機械を作動させる作業
        """
        self.machine_obj = machine_obj
        if (
            self.machine_obj.status == Mstatus.STOP
            and self.machine_obj.worker_obj == self
        ):
            self.status = Wstatus.WORK
            self.machine_obj.set_work(self)
            self.sub_record = [
                'set_work', self.machine_obj.machine_name, factory_time
            ]
            logging.info('{}:現在地{}'.format(self.name, self.position))
            logging.info(
                '{}:作業をセットしました {}'.format(self.name, self.machine_obj)
            )
            self.action_list.insert(
                0, functools.partial(self.machine_run, machine_obj)
            )
        elif (
            self.machine_obj.status == Mstatus.SETTING
            and self.machine_obj.worker_obj == self
        ):
            if not self.sub_record:
                self.sub_record = [
                    'set_work', self.machine_obj.machine_name, factory_time
                ]
            if self.machine_obj.sub_setting < self.machine_obj.setting * 60:
                self.machine_obj.sub_setting += step_time*self.w_speed
                logging.debug('{}:作業1単位進行'.format(self.name))
                self.action_list.insert(
                    0, functools.partial(self.machine_run, machine_obj)
                )
            else:
                self.machine_obj.sub_setting = 0
                self.machine_obj.run()
                self.status = Wstatus.WAIT
                self.machine_obj.worker_obj = None
                self.machine_obj = None
                if self.sub_record:
                    self.sub_record.append(factory_time)
                    self.record.append(self.sub_record)
                    self.sub_record = []
                logging.info('{}:作業完了しました'.format(self.name))
        else:
            self.machine_obj.worker_obj = None
            self.machine_obj = None
            self.status = Wstatus.WAIT
            logging.warning('{}:作業者が重複しています'.format(self.name))

    def machine_continue_set_up(self, machine_obj, step_time, factory_time):
        """機械の設定が終わるまで作業を続ける
        """
        self.machine_obj = machine_obj
        if (
            self.machine_obj.status == Mstatus.NOT_SET
            and self.machine_obj.worker_obj == self
        ):
            self.status = Wstatus.WORK
            self.machine_obj.set_work(self)
            self.sub_record = [
                'setup', self.machine_obj.machine_name, factory_time
            ]
            logging.info('{}:現在地{}'.format(self.name, self.position))
            logging.info(
                '{}:作業をセットしました {}'.format(self.name, self.machine_obj)
            )
            self.action_list.insert(
                0, functools.partial(self.machine_continue_set_up, machine_obj)
            )
            # 同タイプ、同径、同長の場合、段取り時間短縮
            if self.machine_obj.product:
                setup_score = 0
                if (
                    self.machine_obj.sub_product_type
                        == self.machine_obj.product.product_type
                ):
                    setup_score += self.machine_obj.same_type
                if (
                    self.machine_obj.sub_diameter
                        == self.machine_obj.product.diameter
                ):
                    setup_score += self.machine_obj.same_diameter
                if (
                    self.machine_obj.sub_length
                        == self.machine_obj.product.length
                ):
                    setup_score += self.machine_obj.same_length
                self.machine_obj.sub_setup += (
                    self.machine_obj.setup * 60 * setup_score
                )
        elif (
            self.machine_obj.status == Mstatus.SETTING
            and self.machine_obj.worker_obj == self
        ):
            if not self.sub_record:
                self.sub_record = [
                    'setup', self.machine_obj.machine_name, factory_time
                ]
            if self.machine_obj.sub_setup < self.machine_obj.setup * 60:
                self.machine_obj.sub_setup += step_time*self.w_speed
                logging.debug('{}:作業1単位進行'.format(self.name))
                self.action_list.insert(
                    0, functools.partial(
                        self.machine_continue_set_up, machine_obj
                    )
                )
            else:
                self.machine_obj.sub_setup = 0
                self.machine_obj.set_up()
                self.status = Wstatus.WAIT
                self.machine_obj.worker_obj = None
                self.machine_obj = None
                if self.sub_record:
                    self.sub_record.append(factory_time)
                    self.record.append(self.sub_record)
                    self.sub_record = []
                logging.info('{}:作業完了しました'.format(self.name))
        else:
            # self.machine_obj.worker_obj = None
            self.machine_obj = None
            self.status = Wstatus.WAIT
            logging.warning('{}:ステータス異常 or 作業者重複'.format(self.name))

    def execute_task(self, task_obj, step_time, factory_time):
        """タスクを実行する
        """
        self.task_obj = task_obj
        # if self.status != Wstatus.MOVE:
        if self.task_obj.now_task:
            if not self.sub_record:
                self.sub_record = ['task', self.task_obj.task, factory_time]
            self.status = Wstatus.WORK
            self.action_list.insert(
                0, functools.partial(self.execute_task, task_obj)
                )
            logging.info('{}:タスク{}実行中'.format(self.name, task_obj.task))
        else:
            self.task_obj = None
            self.status = Wstatus.WAIT
            if self.sub_record:
                self.sub_record.append(factory_time)
                self.record.append(self.sub_record)
                self.sub_record = []
            logging.info('{}:タスク{}が終了しました'.format(self.name, task_obj.task))

    def check_working_time(self, step_time, factory_time):
        # 勤務中なら
        if self.attendance:
            self.sum_attendance_time += step_time
        # 退勤
        if (
            self.leave < sec_to_timedelta_9h(factory_time).seconds + step_time
            and self.status != Wstatus.MOVE
        ):
            self.attendance = False
            self.status = Wstatus.ON_BREAK
            # 作業途中なら作業時間を記録して終了
            if len(self.sub_record) == 3:
                self.sub_record.append(factory_time)
                self.record.append(self.sub_record)
                self.sub_record = []
            # 出退勤記録
            if self.sub_attendance_record:
                self.sub_attendance_record.append(factory_time)
                self.attendance_record.append(self.sub_attendance_record)
                self.sub_attendance_record = []
        # 始業
        elif (
            self.arrive <= sec_to_timedelta_9h(factory_time).seconds
            and self.position == []
        ):
            self.reset_position()
            self.attendance = True
            self.status = Wstatus.WAIT
            self.sub_attendance_record.append(factory_time)
        # 始業時間前が出勤時間でない
        elif (
            self.arrive > sec_to_timedelta_9h(factory_time).seconds
        ):
            self.position = []
            self.status = Wstatus.ON_BREAK
        else:
            pass

    def step(self, step_time, factory_time):
        """実行すべきタスクはFactoryからalgorithmで判断
        self.now_task = True ならalgorithmから
        action_listにアクションを追加する
        というフローで考える
        """
        # 出勤管理
        self.check_working_time(step_time, factory_time)

        # スケジュール管理
        if self.schedule:
            for schedule_obj in self.schedule:
                schedule_obj.step(step_time, factory_time)

        # アクション管理
        if self.action_list and self.attendance:
            self.action_list.pop(0)(step_time, factory_time)
        else:
            logging.info('{} {}:待機中です'.format(self.name, self.status))
