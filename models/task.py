from utils.utils import nine_hour_return_week
from utils.utils import sec_to_timedelta_9h
import random


class Task(object):
    """掃除、注油など空き時間に実行するタスク
    """
    def __init__(self, task, position, time):
        self.task = task  # タスク名('掃除'、'注油'等)
        # タスクを実行する位置
        if type(position) == int:
            self.position = str(position)
        else:
            self.position = position
        self.time = time  # タスクに要する時間
        self.sub_time = 0  # タスク実行中のカウンター
        self.now_task = False  # 現在実行するタスクか否か

    def check_time(self, factory_time):
        """工場の時間から現在実行すべきタスクを決定する
        """
        pass

    def step(self, step_time, factory_time):
        """一単位時間を進める
        """
        if self.now_task:
            if self.sub_time >= self.time:
                self.sub_time = 0
                self.now_task = False
            else:
                self.sub_time += step_time
        else:
            self.sub_time = 0


class Schedule(Task):
    """休憩、ミーティング、デスクワークなど決まった時間に実行する
    'Taro'
    'Mon'
    11:00-12:00 デスクワーク
    12:00-12:45 休憩
    12:45-5:13:00 ミーティング
    16:00-17:00 デスクワーク
    'Tue'
    ・・・
    """

    def __init__(self, task, position, time, worker, place, week, start):
        super().__init__(task, position, time)
        self.worker = worker  # タスクを実行する人 'Hanako'
        self.place = place  # タスクを実行する場所 'Office'
        self.week = week  # タスクを実行する曜日 'Mon'
        self.start = start  # タスクを開始する時間 12:00 -> (12-8)*60*60 -> 14000
        self.now_task = False  # 現在実行するタスクか否か

    def check_time(self, factory_time):
        """工場の時間から現在実行すべきタスクを決定する
        """
        if (
            nine_hour_return_week(factory_time) == self.week
            and (
                sec_to_timedelta_9h(factory_time).seconds >= self.start
                and sec_to_timedelta_9h(factory_time).seconds <= self.start + self.time
            )
        ):
            self.now_task = True
        else:
            self.now_task = False

    def step(self, step_time, factory_time):
        """一単位時間を進める
        """
        self.check_time(factory_time)


class Event(Task):
    """電話応答、来客対応、加工相談など、ランダムに発生するタスク
    """
    def __init__(self, task, position, time, worker, prob):
        super().__init__(task, position, time)
        self.worker = worker  # タスクを実行する人
        self.prob = prob  # イベントが発生する確率0~1.0
        self.now_task = False  # 現在実行するタスクか否か

    def check_time(self, factory_time):
        """工場の時間から現在実行すべきタスクを決定する
        """
        if self.prob > random.random():  # 0.0 ～ 1.0
            self.now_task = True

    def step(self, step_time, factory_time):
        """一単位時間を進める
        """
        if self.now_task:
            if self.sub_time >= self.time:
                self.sub_time = 0
                self.now_task = False
            else:
                self.sub_time += step_time
        else:
            self.sub_time = 0
            self.check_time(factory_time)
