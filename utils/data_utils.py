import sys
import pickle
import configparser
import pathlib
import random
import copy
import time
from utils.utils import sec_to_timedelta_9h

path = pathlib.Path('__file__')
path /= '../'  # 1つ上の階層を指す
sys.path.append(str(path.resolve()))

from models.status import Mstatus


# --------------------------------------------------
# configparserの宣言とiniファイルの読み込み
# --------------------------------------------------
config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')

factory_object = config['DEFAULT']['factory_object']
factory_object_path = pathlib.Path('__file__')
factory_object_path /= '../'  # 1つ上の階層を指す
factory_object_path = factory_object_path.resolve() / factory_object

factory_list = config['DEFAULT']['factory_list']
factory_list_path = pathlib.Path('__file__')
factory_list_path /= '../'  # 1つ上の階層を指す
factory_list_path = factory_list_path.resolve() / factory_list

def load_factory_object():
    """デフォルトのFactoryオブジェクトを呼び出す
    """   
    with open(factory_object_path, 'rb') as p:
        factory = pickle.load(p)
    return factory

def clear_factory_list():
    """デフォルトのfactory_listを初期化する
    デフォルトのfactoryオブジェクトだけが格納される
    """
    factory = load_factory_object()
    # バイナリで保存
    with open(factory_list_path, 'wb') as p:
        pickle.dump([factory], p)

def load_factory_list():
    """デフォルトのfactory_listを読み込む"""    
    # 読み込み
    with open(factory_list_path, 'rb') as p:
        factory_list = pickle.load(p)
    return factory_list

def shuffle_product_list(frm, to, times):
    """Factoryオブジェクトのproduct_listをシャッフルして
    factory_listに追加して保存する
    
    frm: シャッフルする範囲の開始位置インデックス番号
    to: シャッフルする範囲の終了位置インデックス番号
    times: シャッフルする回数
    """
    # 現在のfactory_listを読み込み
    l = load_factory_list()
    # デフォルトのfactoryオブジェクトを読み込み
    factory = load_factory_object()
    # シャッフルしてtimes個factoryオブジェクトを作成
    for _ in range(times):
        factory = copy.deepcopy(factory)
        shuffle_list = factory.product_list[frm: to + 1]
        random.shuffle(shuffle_list)
        factory.product_list[frm: to + 1] = shuffle_list
        l.append(factory)

    # バイナリで保存
    with open(factory_list_path, 'wb') as p:
        pickle.dump(l, p)

def simulate_and_save(factory_list, step_time, algorithm, file_path):
    """
    factory_listに格納したFactoryオブジェクトのシミュレーションをすべて実行して
    保存する
    
    factory_list: Factory_listを格納したリスト
    step_time: Factoryオブジェクトを実行する刻み時間
    algolithm: Factoryオブジェクトを実行するアルゴリズム
    file_path: シミュレーションの実行結果のリストを保存するファイルパス
    """
    result_list = []
    start_time = time.time()
    end_time = time.time()

    s_factory = None
    s_factory_time = 1000*9*60*60

    i = 0
    for factory in factory_list:
        while True:
            factory.step(step_time, algorithm)
            p = []
            for product in factory.product_list:
                if product.raw_process:
                    p.append(product)
            for machine in factory.machine_list:
                if machine.status != Mstatus.EMPUTY:
                    p.append(machine)
            if not p:
                end_time = time.time()
                break
        i += 1
        print(f'({i})工場稼働時間 : {sec_to_timedelta_9h(factory.time)}')
        result_list.append(factory)

        if factory.time < s_factory_time:
            s_factory_time = factory.time
            s_factory = factory
            n = i
    print('\n')
    print(f'計算時間 : {end_time - start_time}')
    print(f'({n})最短工場稼働時間 : {sec_to_timedelta_9h(s_factory.time)}')
    with open(file_path, 'wb') as p:
            pickle.dump(result_list, p)
