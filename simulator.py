import configparser
import pathlib
import os
import copy
import datetime
import functools
import pickle
import time
import logging
import sqlite3
import pandas as pd
from decimal import Decimal

from utils.utils import sec_to_timedelta_9h
from utils.utils import count_holiday
from utils.utils import time_converter
from utils.utils import adjast_column_width_excel

from utils.db_utils import display_new_material_list
from utils.db_utils import display_past_material_list
from utils.db_utils import display_history_material_data
from utils.db_utils import export_material_list
from utils.db_utils import display_material_quantity
from utils.db_utils import insert_new_material_data
from utils.db_utils import update_material_data
from utils.db_utils import revise_material_data
# from utils.db_utils import return_history_material_dataframe
from utils.db_utils import delete_history_material_data
from utils.db_utils import save_material_list
from utils.db_utils import query_production_table
from utils.db_utils import update_product_to_db
from utils.db_utils import insert_product_to_db
from utils.db_utils import update_process_to_db
from utils.db_utils import insert_process_to_db
from utils.db_utils import delete_process_from_db
from utils.db_utils import update_production_to_db
from utils.db_utils import delete_product_from_db
from utils.db_utils import plan_production
from utils.db_utils import append_production
from utils.db_utils import read_schedule
from utils.db_utils import read_charge_list
from utils.db_utils import check_machine_name
from utils.db_utils import encode_symbols_to_machine_ids
from utils.db_utils import encode_machine_ids_to_symbols

from utils.data_utils import simulate_and_save
from utils.data_utils import load_factory_list
from utils.data_utils import load_factory_object
from utils.data_utils import clear_factory_list
from utils.data_utils import shuffle_product_list

from utils.planning_utils import save_plan_to_excel
from utils.planning_utils import replace_plan
from utils.planning_utils import remove_plan
from utils.planning_utils import load_plan
from utils.planning_utils import replace_list
from utils.planning_utils import update_plan

from views.application import Application

from algorithm.algorithm_ver02 import continue_set_up

from models.factory import Factory


# --------------------------------------------------
# logging 設定
# --------------------------------------------------
# コンソールに表示するのはINFOレベル以上。
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)

# ファイルに出力するのは DEBUG レベル以上。
file_handler = logging.FileHandler('log.log', mode='w', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)

formatter1 = '%(filename)s : %(lineno)s : %(funcName)s : %(levelname)s : %(message)s'
formatter2 = '%(funcName)s : %(levelname)s : %(message)s'

logging.basicConfig(
    level=logging.ERROR,
    handlers=[stream_handler, file_handler],
    format=formatter2
)

# --------------------------------------------------
# configparserの宣言とiniファイルの読み込み
# --------------------------------------------------
config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')

# --------------------------------------------------
# config,iniから値取得
# --------------------------------------------------
# START_TIME = config['DEFAULT']['START_TIME']

# d = config['DATE']['BASE_DATE'].split('/')
# BASE_DATE = datetime.datetime(int(d[0]), int(d[1]), int(d[2]))

# --------------------------------------------------
# パス設定
# --------------------------------------------------

# データベースのファイルパス
db = config['DEFAULT']['database']
db_path = pathlib.Path('__file__')
db_path /= '../'  # 1つ上の階層を指す
db_path = db_path.resolve() / db

# 鋼材データの出力先(csv)
file = config['FILE']['material']
csv_path = pathlib.Path('__file__')
csv_path /= '../'  # 1つ上の階層を指す
csv_path = csv_path.resolve() / file

# 鋼材データの出力先(excel)
date = datetime.datetime.now()
str_date = date.strftime('%Y%m%d%H%M%S')
file = config['FILE']['material_folder']
file = file + '鋼材在庫' + str_date + '.xlsx'
material_path = pathlib.Path('__file__')
material_path /= '../'  # 1つ上の階層を指す
material_path = material_path.resolve() / file

# シミュレーション実行済みのFactoryオブジェクトのリストの保存先
result = config['DEFAULT']['result_list']
result_path = pathlib.Path('__file__')
result_path /= '../'  # 1つ上の階層を指す
result_path = result_path.resolve() / result

# 計画リストのDataFrameのファイルパス
df_file = config['DEFAULT']['plan_dataframe']
df_path = pathlib.Path('__file__')
df_path /= '../'  # 1つ上の階層を指す
df_path = df_path.resolve() / df_file

# 始業時間設定読み込み
START_TIME = config['DEFAULT']['start_time']
# --------------------------------------------------
# 画面設定
# --------------------------------------------------


def view_material(csv_path, material_path, db_path):
    """鋼材管理画面
    """
    while True:
        # os.system('cls')
        print('#'*20, '鋼材管理画面', '#'*20)
        print('\n')
        print('1 - 最新の鋼材データの一覧を表示する')
        print('2 - 各サイズごとの鋼材データを表示する')
        print('3 - 過去の鋼材データの一覧を表示する')
        print('4 - 鋼材の入出庫の履歴を表示する')
        print('5 - 鋼材データを新規登録する')
        print('6 - 鋼材の入出庫データを登録する')
        print('7 - 鋼材データを修正する')
        print('del - 鋼材の履歴データを削除する')
        print('s - 最新の鋼材データの一覧をcsvに保存する')
        print('e - 最新の鋼材データ一覧をexcel形式で保存する')

        print('\n')
        print('exit() - 終了する')

        print('\n')
        print('#'*(20 + 11 + 2 + 20))
        print('\n')

        command_list = [
            '1', '2', '3', '4', '5', '6', '7', 'del', 's','e', 'exit()'
        ]
        command = input('SELECT EXECUTE No. ---')
        os.system('cls')
        if command in command_list:
            print('\n')
            print(f'selstced - "{command}"')
            if command == 'exit()':
                os.system('cls')
                break
            elif command == '1':
                # 最新の鋼材データの一覧を表示する
                print('\n')
                print('最新の鋼材データの一覧を表示する')
                print('\n')
                display_new_material_list(db_path)
                print('\n')
                continue
            elif command == '2':
                # 各サイズごとの鋼材データを表示する
                print('\n')
                print('各サイズごとの鋼材データを表示する')
                print('\n')
                display_material_quantity(db_path)
                print('\n')
                continue
            elif command == '3':
                # 過去の鋼材データの一覧を表示する
                print('\n')
                print('過去の鋼材データの一覧を表示する')
                print('\n')
                display_past_material_list(db_path)
                print('\n')
                continue
            elif command == '4':
                # 鋼材の入出庫の履歴を表示する
                print('\n')
                print('鋼材の入出庫の履歴を表示する')
                print('\n')
                display_history_material_data(db_path)
                print('\n')
                continue
            elif command == '5':
                # 鋼材データを新規登録する
                print('\n')
                print('鋼材の基本データを新規登録する')
                print('\n')
                insert_new_material_data(db_path)
                print('\n')
                continue
            elif command == '6':
                # 鋼材の入出庫データを登録する
                print('\n')
                print('鋼材の入出庫データを登録する')
                print('\n')
                update_material_data(db_path)
                print('\n')
                continue
            elif command == '7':
                # 鋼材データを修正する
                print('\n')
                print('鋼材データを修正する')
                print('\n')
                revise_material_data(db_path)
                print('\n')
                continue
            elif command == 'del':
                # 鋼材の履歴データを削除する
                print('\n')
                print('鋼材の履歴データを削除する')
                print('\n')
                delete_history_material_data(db_path)
                print('\n')
                continue
            elif command == 's':
                # 最新の鋼材データの一覧をcsvに保存する
                print('\n')
                print('最新の鋼材データの一覧をcsvに保存する')
                print('\n')
                save_material_list(csv_path, db_path)
                print('保存完了')
                print(csv_path)
                print('\n')
                continue
            elif command == 'e':
                # 最新の鋼材データの一覧をcsvに保存する
                print('\n')
                print('最新の鋼材データの一覧をexcelに保存する')
                print('\n')
                export_material_list(material_path, db_path)
                adjast_column_width_excel(material_path)
                print('保存完了')
                print(material_path)
                print('\n')
                continue
        else:
            print('不正な入力です')


def view_sim_with_draw():
    """
    シミュレーター実行画面(描画あり)
    """
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    d = config['DATE']['BASE_DATE'].split('/')
    BASE_DATE = datetime.datetime(int(d[0]), int(d[1]), int(d[2]))

    while True:
        # os.system('cls')
        print('#'*12, 'シミュレーター実行(描画あり)', '#'*12)
        print('\n')
        print('1 - 設定済みのFactoryのリストを表示')
        print('2 - リストから一つ選んでシミュレート')

        print('\n')
        print('exit() - 終了する')

        print('\n')
        print('#'*(20 + 10 + 2 + 20))
        print('\n')

        command_list = [
            '1', '2', 'exit()'
        ]
        command = input('SELECT EXECUTE No. ---')
        os.system('cls')
        if command in command_list:
            print('\n')
            print(f'selstced - "{command}"')
            if command == 'exit()':
                os.system('cls')
                break
            elif command == '1':
                # 設定済みのFactoryのリストを表示
                print('\n')
                print('設定済みのFactoryのリストを表示')
                print('\n')
                factory_list = load_factory_list()
                i = 0
                for factory in factory_list:
                    print(f'({i}): {factory}')
                    i += 1
                while True:
                    n = input('select No. ---- [終了/exit()]')
                    if n == 'exit()':
                        break
                    elif n in map(str, [i for i in range(len(factory_list))]):
                        factory_list[int(n)].display_plan()
                        continue
                    else:
                        print('不正な入力です')
                        continue
                print('\n')
                continue
            elif command == '2':
                # リストから一つ選んでシミュレート
                print('\n')
                print('リストから一つ選んでシミュレート')
                print('\n')
                factory_list = load_factory_list()
                i = 0
                for factory in factory_list:
                    print(f'({i}): {factory}')
                    i += 1
                while True:
                    n = input('select No. ---- [終了/exit()]')
                    if n == 'exit()':
                        break
                    elif n in map(str, [i for i in range(len(factory_list))]):
                        factory_list[int(n)].display_plan()
                        # 開始日入力
                        print('\n')
                        # step_time入力
                        # step_time = input('input step time ----')
                        # step_time = int(step_time)
                        print('\n')
                        print('*'*20)
                        print(f'開始日: {BASE_DATE.strftime("%Y-%m-%d")}')
                        # print(f'step time: {step_time}')
                        print('algorithm: algorithm_ver02.continue_set_up')
                        print(f'出力先: {result_path}')
                        print('*'*20)
                        print('\n')
                        conf = input('実行しますか？ - [yes/y]')
                        if conf == 'y':
                            factory = factory_list[int(n)]
                            app = Application(factory, BASE_DATE)
                            app.mainloop()
                            # 保存
                            lst = [factory]
                            with open(result_path, 'wb') as p:
                                pickle.dump(lst, p)

                            print('\n')
                            print('保存完了')
                            print(result_path)
                            break
                        else:
                            fin = input('中止しますか？ - [yes/y]')
                            if fin == 'y':
                                break
                        continue
                    else:
                        print('不正な入力です')
                        continue
                print('\n')
                continue
        else:
            print('不正な入力です')
            continue


def view_sim():
    """
    シミュレーター実行画面(描画なし)
    """
    while True:
        # os.system('cls')
        print('#'*12, 'シミュレーター実行(描画なし)', '#'*12)
        print('\n')
        print('1 - 設定済みのFactoryのリストを表示')
        print('2 - リストから一つ選んでシミュレート')
        print('3 - リストのFactoryをすべてシミュレート')

        print('\n')
        print('exit() - 終了する')

        print('\n')
        print('#'*(20 + 10 + 2 + 20))
        print('\n')

        command_list = [
            '1', '2', '3', 'exit()'
        ]
        command = input('SELECT EXECUTE No. ---')
        os.system('cls')
        if command in command_list:
            print('\n')
            print(f'selstced - "{command}"')
            if command == 'exit()':
                os.system('cls')
                break
            elif command == '1':
                # 設定済みのFactoryのリストを表示
                print('\n')
                print('設定済みのFactoryのリストを表示')
                print('\n')
                factory_list = load_factory_list()
                i = 0
                for factory in factory_list:
                    print(f'({i}): {factory}')
                    i += 1
                while True:
                    n = input('select No. ---- [終了/exit()]')
                    if n == 'exit()':
                        break
                    elif n in map(str, [i for i in range(len(factory_list))]):
                        factory_list[int(n)].display_plan()
                        continue
                    else:
                        print('不正な入力です')
                        continue
                print('\n')
                continue
            elif command == '2':
                # リストから一つ選んでシミュレート
                print('\n')
                print('リストから一つ選んでシミュレート')
                print('\n')
                factory_list = load_factory_list()
                i = 0
                for factory in factory_list:
                    print(f'({i}): {factory}')
                    i += 1
                while True:
                    n = input('select No. ---- [終了/exit()]')
                    if n == 'exit()':
                        break
                    elif n in map(str, [i for i in range(len(factory_list))]):
                        factory_list[int(n)].display_plan()
                        step_time = input('input step time ----')
                        step_time = int(step_time)

                        print('\n')
                        print('*'*20)
                        print(f'step time: {step_time}')
                        print('algorithm: algorithm_ver02.continue_set_up')
                        print(f'出力先: {result_path}')
                        print('*'*20)
                        print('\n')
                        conf = input('実行しますか？ - [yes/y]')
                        if conf == 'y':
                            simulate_and_save(
                                [factory_list[int(n)]],
                                step_time, continue_set_up, result_path
                            )
                            print('\n')
                            print('保存完了')
                            print(result_path)
                            break
                        else:
                            fin = input('中止しますか？ - [yes/y]')
                            if fin == 'y':
                                break
                        continue
                    else:
                        print('不正な入力です')
                        continue
                print('\n')
                continue
            elif command == '3':
                # リストのFactoryをすべてシミュレート
                print('\n')
                print('リストのFactoryをすべてシミュレート')
                print('\n')
                factory_list = load_factory_list()
                i = 0
                for factory in factory_list:
                    print(f'({i}): {factory}')
                    i += 1
                while True:
                    step_time = input('input step time ----')
                    step_time = int(step_time)

                    print('\n')
                    print('*'*20)
                    print(f'step time: {step_time}')
                    print('algorithm: algorithm_ver02.continue_set_up')
                    print(f'出力先: {result_path}')
                    print('*'*20)
                    print('\n')
                    conf = input('実行しますか？ - [yes/y]')
                    if conf == 'y':
                        simulate_and_save(
                            factory_list, step_time, continue_set_up, result_path
                        )
                        print('\n')
                        print('保存完了')
                        print(result_path)
                        print('/n')
                        break
                    else:
                        fin = input('中止しますか？ - [yes/y]')
                        if fin == 'y':
                            break
                        else:
                            continue
        else:
            print('不正な入力です')
            continue


def view_review():
    """シミュレーター実行結果の検証画面
    """
    os.system('cls')
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    d = config['DATE']['BASE_DATE'].split('/')
    BASE_DATE = datetime.datetime(int(d[0]), int(d[1]), int(d[2]))
    print('#'*12, 'シミュレーター実行結果の検証画面', '#'*12)
    with open(result_path, 'rb') as p:
        factory_list = pickle.load(p)

    i = 0
    for factory in factory_list:
        print(f'({i})工場稼働時間 : {sec_to_timedelta_9h(factory.time)}')
        i += 1
    print('#'*12, 'シミュレーター実行結果の検証画面', '#'*12)
    print('\n')
    while True:
        n = input('select No. ---- [終了/exit()]')
        if n == 'exit()':
            break
        elif n in map(str, [i for i in range(len(factory_list))]):
            factory_list[int(n)].display_plan()
            print('\n')
            factory = factory_list[int(n)]
            app = Application(factory, BASE_DATE)
            app.mainloop()
        else:
            print('不正な入力です')
            continue


def search_production(db_path):
    """
    production情報検索表示

    db_path: データベースのパス
    """
    while True:
        os.system('cls')
        print('\n')
        print('==== 製品・生産登録情報検索 ====')
        sql = """
            SELECT
                product.code,
                product.type,
                product.diameter,
                product.shank,
                product.length,
                product.effective_length,
                process.process
            FROM
                product
            INNER JOIN
                process
            ON
                product.product_id = process.product_id
        """
        with sqlite3.connect(db_path) as con:
            df = pd.read_sql(sql, con)

        # process列を機械名に変換
        encoder = functools.partial(encode_machine_ids_to_symbols, db_path=db_path)
        df['process'] = df['process'].apply(encoder)

        typ = input('製品タイプ[skip/enter] ---- ')
        diameter = input('製品径[skip/enter] ---- ')
        shank = input('シャンク径[skip/enter] ---- ')
        length = input('全長[skip/enter] ---- ')
        effective_length = input('有効長[skip/enter] ---- ')

        # 条件式作成
        query_list = []
        if typ:
            query_list.append(f'type == "{typ}"')
        if diameter:
            query_list.append(f'diameter == {diameter}')
        if shank:
            query_list.append(f'shank == {shank}')
        if length:
            query_list.append(f'length == {length}')
        if effective_length:
            query_list.append(f'effective_length == {effective_length}')
        query_str = ' and '.join(query_list)

        if query_str:
            if len(df.query(query_str)) == 0:
                print('該当する製品・製造情報は登録されていません')
            else:
                print(df.query(query_str))
        else:
            print(df)

        conf = input('他の条件で検索しますか？ - [yes/y]')
        if conf != 'y':
            break


def view_all_production(db_path):
    """
    production情報一覧

    db_path: データベースのパス
    """
    os.system('cls')
    print('\n')
    print('==== 製品情報登録一覧 ====')
    sql = """
        SELECT
            code,
            type,
            diameter,
            shank,
            length,
            effective_length
        FROM
            product
        ORDER BY
            type,
            shank,
            length
    """
    with sqlite3.connect(db_path) as con:
            df = pd.read_sql(sql, con)
        
    print(df)


def view_product(db_path):
    """Product設定画面
    """
    while True:
        # os.system('cls')
        print('#'*19, '製品情報(product)設定', '#'*19)
        print('\n')
        print('a - 製品情報登録一覧')
        print('s - 製品・生産登録情報検索')
        print('0 - 製品・生産情報表示')  # query_production_table('P100', db_path)
        print('1 - 製品情報(produt) 新規登録')  # insert_product_to_db(db_path)
        print('2 - 製品情報(produt) 更新')  # update_product_to_db(db_path)
        print('3 - 工程情報(pcesess) 新規登録')  # insert_process_to_db('P100', db_path)
        print('4 - 工程情報(pcesess) 更新')  # update_process_to_db('P100', db_path)
        print('5 - 工程情報(pcesess) 削除')  # delete_process_from_db('P100', db_path)
        print('6 - 生産情報(productition) 更新')  # update_production_to_db('P100', 'NL', db_path)
        print('7 - 製品情報一括削除(Product, process, production)')  # delete_product_from_db('P100', db_path)
        print('\n')
        print('exit() - 終了する')
        print('\n')
        print('#'*(20 + 9 + 2 + 20))
        print('\n')

        command_list = [
            'a', 's', '0', '1', '2', '3', '4', '5', '6', '7', 'exit()'
        ]
        command = input('SELECT EXECUTE No. ---')
        # os.system('cls')
        if command in command_list:
            print('\n')
            print(f'selstced - "{command}"')
            if command == 'exit()':
                os.system('cls')
                break
            elif command == 'a':
                print('製品情報登録一覧')
                view_all_production(db_path)
                continue
            elif command == 's':
                print('製品・生産登録情報検索')
                search_production(db_path)
                continue
            elif command == '0':
                print('製品・生産情報表示')
                code = input('製品コードを入力 ---')
                print(query_production_table(code, db_path))
                print('\n')
                continue
            elif command == '1':
                print('==== 製品情報新規登録 ====')
                code = insert_product_to_db(db_path)
                if code:
                    update_process_to_db(code, db_path)
                print('\n')
                continue
            elif command == '2':
                print('==== 製品情報更新 ====')
                update_product_to_db(db_path)
                print('\n')
                continue
            elif command == '3':
                print('==== 工程情報新規登録 ====')
                code = input('製品コードを入力 ---')
                insert_process_to_db(code, db_path)
                print('\n')
                continue
            elif command == '4':
                print('==== 工程情報更新 ====')
                code = input('製品コードを入力 ---')
                update_process_to_db(code, db_path)
                print('\n')
                continue
            elif command == '5':
                print('==== 工程情報削除 ====')
                code = input('製品コードを入力 ---')
                delete_process_from_db(code, db_path)
                print('\n')
                continue
            elif command == '6':
                print('==== 生産情報更新 ====')
                code = input('製品コードを入力 ---')
                print(query_production_table(code, db_path))
                machine = input('機械名を入力 ---')
                update_production_to_db(code, machine, db_path)
                print('\n')
                continue
            elif command == '7':
                print('==== 製品情報一括削除 ====')
                code = input('製品コードを入力 ---')
                print(query_production_table(code, db_path))
                conf = input('本当に削除しますか？ - [yes/y]')
                if conf == 'y':
                    delete_product_from_db(code, db_path)
                    print('\n')
                continue
        else:
            print('不正な入力です')
            print('\n')
            continue


def view_save_plan_to_excel():
    """
    シミュレーター実行済みのFactoryリストから
    一つ選んで工程表をエクセル形式で保存する
    """
    while True:
        os.system('cls')
        print('\n')
        print('#'*15, '工程表出力(Ecxcel形式)', '#'*15)
        with open(result_path, 'rb') as p:
            factory_list = pickle.load(p)

        i = 0
        for factory in factory_list:
            print(f'({i})工場稼働時間 : {sec_to_timedelta_9h(factory.time)}')
            i += 1
        print('\n')

        n = input('select No. ---- [終了/exit()]')
        if n == 'exit()':
            break
        elif n in map(str, [i for i in range(len(factory_list))]):
            factory_list[int(n)].display_plan()
            config = configparser.ConfigParser()
            config.read('config.ini', encoding='utf-8')
            d = config['DATE']['BASE_DATE'].split('/')
            BASE_DATE = datetime.datetime(int(d[0]), int(d[1]), int(d[2]))
            print(f'工程表の開始日: {BASE_DATE.strftime("%Y-%m-%d")}')
            print('\n')
            print('color設定')
            color_dic = {
                'Steelblue': '4682B4', 'Daidaiiro': 'E67928', 'Cream Yellow': 'E4D3A2'
            }
            i = 0
            dic = {}
            for k, v in color_dic.items():
                dic[i] = k
                print(f'{i}: {k}')
                i += 1
            lst = [str(x) for x in range(i + 1)]
            lst.append('other')
            while True:
                select_color_number = input('BarColorを選択 -[other/色を指定]')
                if select_color_number not in lst:
                    print('不正な値です')
                    continue
                elif select_color_number == 'other':
                    select_color = input('RGB番号を入力(16進数) ----')
                    break
                else:
                    select_color = color_dic[dic[int(select_color_number)]]
                    break
            factory = factory_list[int(n)]
            # plan_file = config['FILE']['plan']
            plan_file = config['FILE']['plan_folder'] + str(BASE_DATE.date()) + '-' + str(int(time.time())) + '.xlsx'
            save_plan_to_excel(factory, select_color, BASE_DATE, plan_file)
            print('==== 出力完了 ====')
            print(plan_file)
        else:
            print('不正な入力です')
            continue


def view_planning(db_path):
    """生産計画リスト設定
    """
    while True:
        # os.system('cls')
        print('#'*15, '生産計画リスト設定', '#'*15)
        print('\n')
        print('o - 計画リストを表示')
        print('n - 計画リストを初期化(新規作成)')
        print('a - 計画リストに計画を追加する')
        print('r - 計画リストの順番を並び替える')
        print('d - 計画リストから計画を削除する')

        print('\n')
        print('exit() - 終了する')

        command_list = [
            'o', 'n', 'a', 'r', 'd', 'exit()'
        ]
        command = input('SELECT EXECUTE No. ---')
        os.system('cls')
        if command in command_list:
            print('\n')
            print(f'selstced - "{command}"')
            if command == 'exit()':
                os.system('cls')
                break
            elif command == 'o':
                os.system('cls')
                origin_df = load_plan()
                print(origin_df)
                print('\n')
                continue
            elif command == 'n':
                origin_df = load_plan()
                os.system('cls')
                print(origin_df)
                print('==== 計画リストを初期化 ====')
                print('登録済みの計画リストは削除されます')
                conf = input('よろしいですか？ ---- [yes/y]')
                if conf != 'y':
                    print('計画リストの初期化を中止します')
                    print('\n')
                else:
                    while True:
                        product = input('製品コードを入力 ----')
                        df = query_production_table(product, db_path)
                        if len(df) == 0:
                            print('製品情報の登録がありません')
                            ask1 = input('他の製品を読み込みますか？ - [yes/y]')
                            if ask1 != 'y':
                                print('計画リストの初期化を中止します')
                                print('\n')
                                break
                        else:
                            print(df)
                            n = input('select No. ----')
                            while True:
                                lot = input('lot ----')
                                try:
                                    lot = int(lot)
                                    if lot > 0:
                                        break
                                    else:
                                        print('不正な入力です')
                                        print('\n')
                                except ValueError:
                                    print('不正な入力です')
                                    print('\n')

                            try:
                                plan_df = plan_production(df, int(n), lot)
                                print('\n')
                                print(plan_df)
                                print('\n')
                                ask2 = input('登録しますか？ -[yes/y]')
                                if ask2 == 'y':
                                    plan_df.to_pickle(df_path)
                                    print('=== 登録完了 ===')
                                    print('\n')
                                    break
                            except IndexError:
                                print('不正な入力です')
                                print('\n')
                print('\n')
                continue

            elif command == 'a':
                os.system('cls')
                plan_df = load_plan()
                print(plan_df)
                print('==== 計画リストに計画を追加 ====')

                while True:
                    product = input('製品コードを入力 ----')
                    df = query_production_table(product, db_path)
                    if len(df) == 0:
                        print('製品情報の登録がありません')
                        ask1 = input('他の製品を読み込みますか？ - [yes/y]')
                        if ask1 != 'y':
                            print('計画リストの初期化を中止します')
                            print('\n')
                            break
                    else:
                        print(df)
                        n = input('select No. ----')
                        while True:
                            lot = input('lot ----')
                            try:
                                lot = int(lot)
                                if lot > 0:
                                    break
                                else:
                                    print('不正な入力です')
                                    print('\n')
                            except ValueError:
                                print('不正な入力です')
                                print('\n')

                        try:
                            plan_df = append_production(
                                df, int(n), lot, plan_df
                            )
                            # plan_df = plan_production(df, int(n), int(lot))
                            print('\n')
                            print(plan_df)
                            print('\n')
                            ask2 = input('登録しますか？ -[yes/y]')
                            if ask2 == 'y':
                                plan_df.to_pickle(df_path)
                                print('=== 登録完了 ===')
                                print('\n')
                                ask = input('続けて追加しますか？ - [yes/y]')
                                if ask != 'y':
                                    break
                        except IndexError:
                            print('不正な入力です')
                            print('\n')
 
                print('\n')
                continue

            elif command == 'r':
                os.system('cls')
                df = load_plan()
                print(df)
                print('==== 計画リストを並び替える ====')
                print('\n')

                while True:
                    n = input('移動する計画番号 ----')
                    m = input('移動数 - (例) -1 -> 前に1つ移動 1 ->後ろに1つ移動')
                    try:
                        df = replace_plan(df, int(n), int(m))
                        print('\n')
                        print(df)
                        print('\n')
                    except (IndexError, ValueError):
                        print('不正な入力です')
                        print('\n')
                    ask3 = input('続けて並び替えしますか？ - [yes/y]')
                    if ask3 != 'y':
                        ask4 = input('登録しますか？ - [yes/y]')
                        if ask4 == 'y':
                            df.to_pickle(df_path)
                            print('=== 登録完了 ===')
                            print('\n')
                            break
                        else:
                            ask5 = input('中止しますか？ - [yes/y]')
                            if ask5 == 'y':
                                print('中止しました')
                                print('\n')
                                break

            elif command == 'd':
                os.system('cls')
                df = load_plan()
                print(df)
                print('==== 計画を削除する ====')
                print('\n')

                while True:
                    n = input('削除する計画番号 ----')
                    try:
                        df = remove_plan(df, int(n))
                        print('\n')
                        print(df)
                        print('\n')
                    except (IndexError, ValueError, KeyError):
                        print('不正な入力です')
                        print('\n')
                    ask6 = input('続けて削除しますか？ - [yes/y]')
                    if ask6 != 'y':
                        ask7 = input('保存しますか？ - [yes/y]')
                        if ask7 == 'y':
                            update_plan(df)
                            print('=== 保存完了 ===')
                            print('\n')
                            break
                        else:
                            ask8 = input('中止しますか？ - [yes/y]')
                            if ask8 == 'y':
                                print('中止しました')
                                print('\n')
                                break
                print('\n')
                continue
        else:
            print('不正な入力です')
            print('\n')
            continue


def formatting_factory_obj(db_path):
    """
    Factoryオブジェクトをインスタンス化し、
    データベースに登録済みの、作業者リスト、機械リスト、計画リスト、charge_list、スケジュールを割り当てる

    db_path: データベースのパス
    """
    # インスタンス化
    factory = Factory()

    # 作業者登録
    with sqlite3.connect(db_path) as con:
        wk = pd.read_sql(
            """
            SELECT
                name,
                age,
                sex,
                m_speed,
                w_speed,
                arrive,
                leave,
                position
            FROM
                worker
            WHERE
                active = '1'
            """,
            con
        )
    factory.deploy(wk)

    # 機械登録
    with sqlite3.connect(db_path):
        ma = pd.read_sql(
            """
            SELECT
                symbol,
                position_id,
                type,
                setup,
                setting,
                same_type,
                same_diameter,
                same_length,
                error_rate,
                reset,
                trouble_rate,
                repair
            FROM
                machine
            WHERE
                active = '1'
            """,
            con
        )
    factory.set_machines(ma)

    # 生産計画登録
    factory.planning(load_plan())

    # 作業者のスケジュールを登録
    for worker in factory.worker_list:
        worker.set_schedule(read_schedule(worker.name, db_path))

    # 担当機械登録
    for worker in factory.worker_list:
        worker.set_charge_list(
            read_charge_list(worker.name, db_path), factory.planed_machine
        )

    return factory


def view_late_setting(db_path):
    """
    計画遅延の設定
    機械の故障、メンテナンス
    鋼材、素材の入荷日設定
    """
    while True:
        os.system('cls')
        print('#'*20, '計画遅延設定', '#'*20)
        print('\n')
        print('t - 機械のメンテナンス、故障による計画遅延の設定')
        print('m - 鋼材、素材の入庫待ち設定')

        print('\n')
        print('exit() - 終了する')
        print('\n')
        print('#'*(20 + 10 + 3 + 20))

        command_list = [
            't', 'm', 'exit()'
        ]
        command = input('SELECT EXECUTE No. ---')
        os.system('cls')
        if command in command_list:
            print('\n')
            print(f'selstced - "{command}"')
            if command == 'exit()':
                os.system('cls')
                break
            elif command == 't':
                os.system('cls')
                print('機械のメンテナンス、故障による計画遅延の設定')
                print('\n')
                print('登録済みマスターFactoryオブジェクト')
                print('==== 計画リスト ====')
                factory = load_factory_object()
                factory.display_plan()
                print('*'*20)
                print('\n')
                print('==== 機械の状態 ====')
                factory.display_machine_status()
                print('\n')

                # Factory_list読み込み
                factory_list = load_factory_list()
                print('シミュレート用Factoryオブジェクト一覧')
                print('*'*20)
                i = 0
                for factory in factory_list:
                    print(f'({i}) - {factory}')
                    i += 1
                print('*'*20)

                while True:
                    symbol = input('故障、メンテナンスのスケジュールを登録する機械名 ----')
                    print('\n')
                    if check_machine_name(symbol, db_path):
                        try:
                            # 起点日表示
                            config = configparser.ConfigParser()
                            config.read('config.ini', encoding='utf-8')
                            d = config['DATE']['BASE_DATE'].split('/')
                            BASE_DATE = datetime.datetime(
                                int(d[0]), int(d[1]), int(d[2])
                            )
                            print(
                                f'シミュレーション起点日: {BASE_DATE.strftime("%Y-%m-%d")}'
                            )
                            print('\n')

                            print('開始日')
                            y1 = input('西暦')
                            m1 = input('月')
                            d1 = input('日')
                            try:
                                date1 = datetime.datetime(
                                    int(y1), int(m1), int(d1)
                                )
                                holiday = count_holiday(BASE_DATE, date1)
                                start_day = ((date1 - BASE_DATE).days) - holiday
                                print('\n')

                                print('終了日')
                                y2 = input('西暦')
                                m2 = input('月')
                                d2 = input('日')
                                date2 = datetime.datetime(
                                    int(y2), int(m2), int(d2)
                                )
                                holiday = count_holiday(date1, date2)
                                end_day = ((date2 - BASE_DATE).days) + 1 - holiday

                                if start_day < 0 or start_day > end_day:
                                    print('不正な入力です')
                                else:
                                    print('シミュレート用Factoryオブジェクトは初期化されます')
                                    conf = input('実行しますか？ - [yes/y]')
                                    if conf == 'y':
                                        for machine in factory.machine_list:
                                            if machine.machine_name == symbol:
                                                machine.set_trouble_schedule(
                                                    start_day*9*60*60, end_day*9*60*60
                                                )
                                                # 保存
                                                factory.save_object()
                                                # リストのクリア
                                                clear_factory_list()
                                        conf2 = input('続けて登録しますか？ - [yes/y]')
                                        if conf2 != 'y':
                                            break
                                    else:
                                        break
                            except ValueError:
                                print('不正な入力です')
                        except ValueError:
                            print('不正な入力です')

                    else:
                        print('その機械は登録されていません')

            elif command == 'm':
                os.system('cls')
                print('鋼材、素材の入庫待ち設定')
                print('\n')
                print('登録済みマスターFactoryオブジェクト')
                print('==== 計画リスト ====')
                factory = load_factory_object()
                factory.display_plan()
                print('*'*20)
                print('\n')
                print('==== 機械の状態 ====')
                factory.display_machine_status()
                print('\n')

                # Factory_list読み込み
                factory_list = load_factory_list()
                print('シミュレート用Factoryオブジェクト一覧')
                print('*'*20)
                i = 0
                for factory in factory_list:
                    print(f'({i}) - {factory}')
                    i += 1
                print('*'*20)

                while True:
                    no = input('鋼材、素材の入庫待ちの設定をする計画No. ----')
                    print('\n')
                    try:
                        no = int(no)
                    except ValueError:
                        print('不正な入力です')
                        print('\n')
                    # 起点日表示
                    config = configparser.ConfigParser()
                    config.read('config.ini', encoding='utf-8')
                    d = config['DATE']['BASE_DATE'].split('/')
                    BASE_DATE = datetime.datetime(
                        int(d[0]), int(d[1]), int(d[2])
                    )
                    print(f'シミュレーション起点日: {BASE_DATE.strftime("%Y-%m-%d")}')
                    print('\n')

                    try:
                        print('入庫日を入力')
                        y1 = input('西暦')
                        m1 = input('月')
                        d1 = input('日')
                        date1 = datetime.datetime(int(y1), int(m1), int(d1))
                        holiday = count_holiday(BASE_DATE, date1)
                        start_day = ((date1 - BASE_DATE).days) - holiday
                        print('\n')
                        check = False
                        for product in factory.product_list:
                            if product.product_number == no:
                                check = True
                                print('\n')
                                print('*'*20)
                                print(f'計画番号: {no}')
                                print(f'計画名: {product.product}')
                                print(f'素材入庫日: {date1.strftime("%Y-%m-%d")}')
                                print('*'*20)
                                print('\n')
                                print('シミュレート用Factoryオブジェクトは初期化されます')
                                conf = input('登録しますか？ - [yes/y]')
                                if conf == 'y':
                                    product.receipt_time = (
                                        start_day * 9 * 60 * 60
                                    )
                                    # 保存
                                    factory.save_object()
                                    # リストのクリア
                                    clear_factory_list()
                                else:
                                    print('中止します')
                                    break
                        if not check:
                            print('計画がありません')

                    except ValueError:
                        print('不正な入力です')

                    conf2 = input('続けて入力しますか？ - [yes/y]')
                    if conf2 != 'y':
                        break


def view_factory(db_path):
    """
    Factory設定
    """
    while True:
        # os.system('cls')
        print('#'*20, 'Factory設定', '#'*20)
        print('\n')
        print('b - シミュレート起点日の設定')
        print('o - 登録済みFactoryを表示')
        print('n - Factory初期化(新規作成)')
        print('l - 計画遅延設定')
        print('fn - 計画リストの工程を1つ終わらせる')
        print('fw - 計画リストの工程を進める')
        print('d - シミュレート用Factoryオブジェクトのリストを初期化する')
        print('r - 計画を並び替えてシミュレート用Factoryオブジェクトのリストに追加する')
        print('s - 計画リストをシャッフルしてシミュレート用Factoryオブジェクトのリストに追加する')

        print('\n')
        print('exit() - 終了する')
        print('\n')
        print('#'*(20 + 10 + 2 + 20))

        command_list = [
            'b', 'o', 'n', 'l', 'fn', 'fw', 'd', 'r', 's', 'exit()'
        ]
        command = input('SELECT EXECUTE No. ---')
        os.system('cls')
        if command in command_list:
            print('\n')
            print(f'selstced - "{command}"')
            if command == 'exit()':
                os.system('cls')
                break
            elif command == 'b':
                os.system('cls')
                config = configparser.ConfigParser()
                config.read('config.ini', encoding='utf-8')
                d = config['DATE']['BASE_DATE'].split('/')
                BASE_DATE = datetime.datetime(int(d[0]), int(d[1]), int(d[2]))
                print('シミュレート起点日の設定')
                print('\n')
                print(f'起点日: {BASE_DATE.strftime("%Y-%m-%d")}')
                print('\n')
                conf = input('起点日を変更しますか？ - [yes/y]')
                if conf == 'y':
                    print('起点日を登録')
                    year = input('西暦')
                    month = input('月')
                    day = input('日')
                    try:
                        # 日付チェック
                        date = datetime.datetime(
                            int(year), int(month), int(day)
                        )
                        date = year + '/' + month + '/' + day
                        print(f'変更後起点日:{date}')
                        print('\n')
                        config['DATE']['BASE_DATE'] = date
                        # 書き込みモードでオープン
                        with open('config.ini', 'w') as configfile:
                            # 指定したconfigファイルを書き込み
                            config.write(configfile)
                    except ValueError:
                        print('不正な入力です')

            elif command == 'o':
                os.system('cls')
                print('登録済みマスターFactoryオブジェクト')
                print('==== 計画リスト ====')
                factory = load_factory_object()
                factory.display_plan()
                print('*'*20)
                print('\n')
                print('==== 機械の状態 ====')
                factory.display_machine_status()
                print('\n')

                # Factory_list読み込み
                factory_list = load_factory_list()
                # 番号選択用リスト作成
                lst = [i for i in range(len(factory_list))]
                lst = map(str, lst)
                lst = list(lst)
                while True:
                    print('シミュレート用Factoryオブジェクト一覧')
                    print('*'*20)
                    i = 0
                    for factory in factory_list:
                        print(f'({i}) - {factory}')
                        i += 1
                    print('*'*20)
                    ask1 = input('select No. - [終了/exit()]')
                    if ask1 == 'exit()':
                        print('終了します')
                        break
                    elif ask1 in lst:
                        print('\n')
                        os.system('cls')
                        print(f'==== Factory No.{ask1} 計画リスト ====')
                        factory_list[int(ask1)].display_plan()
                        print('\n')
                    else:
                        print('不正な入力です')
                        print('\n')
                        continue

            elif command == 'n':
                os.system('cls')
                print('Factoryオブジェクト初期化(新規作成)')
                print('\n')
                print('登録済みマスターFactoryオブジェクト')
                print('==== 計画リスト ====')
                factory = load_factory_object()
                factory.display_plan()
                print('*'*20)
                print('\n')
                print('==== 機械の状態 ====')
                factory.display_machine_status()
                print('\n')

                # Factory_list読み込み
                factory_list = load_factory_list()
                print('シミュレート用Factoryオブジェクト一覧')
                print('*'*20)
                i = 0
                for factory in factory_list:
                    print(f'({i}) - {factory}')
                    i += 1
                print('*'*20)

                print('登録済みの計画リストで初期化されます')
                print('シミュレート用Factoryオブジェクトも初期化されます')
                conf = input('初期化しますか？() - [yes/y]')
                if conf == 'y':
                    # factory初期化
                    factory = formatting_factory_obj(db_path)
                    # charge_list漏れがないかチェック
                    factory_machines = []
                    all_charges = []
                    check = 0
                    for machine in factory.planed_machine:
                        factory_machines.append(machine.machine_name)
                    for worker in factory.worker_list:
                        for charge in worker.charge_list:
                            all_charges.append(charge)
                    for machine_name in factory_machines:
                        if machine_name not in all_charges:
                            check += 1
                    if check == 0:
                        factory.save_object()
                        clear_factory_list()
                        print('\n')
                        print('*'*20, '初期化成功', '*'*20)
                        print('Factoryオブジェクトは登録済みの計画リストで初期化されました')
                        print('シミュレート用Factoryオブジェクトは初期化されました')
                    else:
                        print('\n')
                        print('*'*20, '初期化失敗', '*'*20)
                        print('担当者が割り当てられていない機械があります')
                    print('\n')
                else:
                    print('\n')
                    print('初期化を中止します')
                    print('\n')

            elif command == 'l':
                view_late_setting(db_path)

            elif command == 'fn':
                os.system('cls')
                print('計画リストの工程を1つ終わらせる')
                print('\n')
                print('登録済みマスターFactoryオブジェクト')
                print('==== 計画リスト ====')
                factory = load_factory_object()
                factory.display_plan()
                print('*'*20)
                print('\n')
                print('==== 機械の状態 ====')
                factory.display_machine_status()
                print('\n')

                # Factory_list読み込み
                factory_list = load_factory_list()
                print('シミュレート用Factoryオブジェクト一覧')
                print('*'*20)
                i = 0
                for factory in factory_list:
                    print(f'({i}) - {factory}')
                    i += 1
                print('*'*20)

                while True:
                    plan_no = input('工程を1つ終了させる計画番号を入力 ----')
                    print('シミュレート用Factoryオブジェクトは初期化されます')
                    conf = input('実行しますか？ - [yes/y]')
                    if conf == 'y':
                        factory.finish_one_process(int(plan_no))
                        # 保存
                        factory.save_object()
                        # リストのクリア
                        clear_factory_list()
                        print('\n')
                        print('==== 計画リスト ====')
                        factory.display_plan()
                        print('*'*20)
                        print('\n')
                        print('==== 機械の状態 ====')
                        factory.display_machine_status()
                        print('\n')
                        conf2 = input('続けて他の工程を終了させますか？ - [No/n]')
                        if conf2 == 'n':
                            break
                    else:
                        print('\n')
                        print('中止します')
                        print('\n')
                        conf3 = input('他の工程を終了させますか？ - [No/n]')
                        if conf3 == 'n':
                            break

            elif command == 'fw':
                os.system('cls')
                print('計画リストの工程を進める')
                print('\n')
                print('登録済みマスターFactoryオブジェクト')
                print('==== 計画リスト ====')
                factory = load_factory_object()
                factory.display_plan()
                print('*'*20)
                print('\n')
                print('==== 機械の状態 ====')
                factory.display_machine_status()
                print('\n')

                # Factory_list読み込み
                factory_list = load_factory_list()
                print('シミュレート用Factoryオブジェクト一覧')
                print('*'*20)
                i = 0
                for factory in factory_list:
                    print(f'({i}) - {factory}')
                    i += 1
                print('*'*20)

                while True:
                    plan_no = input('工程を進める計画番号を入力 ----')
                    mount = input('数量を入力 ----')
                    print('シミュレート用Factoryオブジェクトは初期化されます')
                    conf = input('実行しますか？ - [yes/y]')
                    if conf == 'y':
                        factory.proceed_process(int(plan_no), int(mount))
                        factory.save_object()
                        clear_factory_list()
                        print('\n')
                        print('==== 計画リスト ====')
                        factory.display_plan()
                        print('*'*20)
                        print('\n')
                        print('==== 機械の状態 ====')
                        factory.display_machine_status()
                        print('\n')
                        conf2 = input('続けて他の工程を進めますか？ - [No/n]')
                        if conf2 == 'n':
                            break
                    else:
                        print('\n')
                        print('中止します')
                        print('\n')
                        conf3 = input('他の工程を終了させますか？ - [No/n]')
                        if conf3 == 'n':
                            break

            elif command == 'd':
                os.system('cls')
                print('登録済みマスターFactoryオブジェクト')
                print('==== 計画リスト ====')
                factory = load_factory_object()
                factory.display_plan()
                print('*'*20)
                print('\n')
                print('==== 機械の状態 ====')
                factory.display_machine_status()
                print('\n')

                # Factory_list読み込み
                factory_list = load_factory_list()
                print('シミュレート用Factoryオブジェクト一覧')
                print('*'*20)
                i = 0
                for factory in factory_list:
                    print(f'({i}) - {factory}')
                    i += 1
                print('*'*20)
                print('シミュレート用Factoryオブジェクトのリストを初期化します')
                conf = input('初期化しますか？() - [yes/y]')
                if conf == 'y':
                    # factory_list初期化
                    clear_factory_list()
                    print('\n')
                else:
                    print('\n')
                    print('初期化を中止します')
                    print('\n')

            elif command == 'r':
                os.system('cls')
                print('計画リストを並び替える')
                print('\n')
                print('登録済みマスターFactoryオブジェクト')
                print('==== 計画リスト ====')
                factory = load_factory_object()
                factory.display_plan()
                print('*'*20)
                print('\n')
                print('==== 機械の状態 ====')
                factory.display_machine_status()
                print('\n')

                # Factory_list読み込み
                factory_list = load_factory_list()
                print('シミュレート用Factoryオブジェクト一覧')
                print('*'*20)
                i = 0
                for factory in factory_list:
                    print(f'({i}) - {factory}')
                    i += 1
                print('*'*20)

                # deepcopyにしないと同じリストになってしまう
                replaced_factory = copy.deepcopy(factory)
                while True:
                    print('シミュレート用Factoryオブジェクトに追加されます')
                    plan_no = input('移動する計画番号を入力 ---- ')
                    n = input('移動量を入力 ---- ')
                    conf = input('実行しますか？ - [yes/y]')
                    if conf == 'y':
                        # 一つ順番を変えたものを保存
                        replace_list(
                            replaced_factory.product_list, int(plan_no), int(n)
                        )
                        print('\n')
                        print('==== 計画リスト ====')
                        replaced_factory.display_plan()
                        print('*'*20)
                        print('\n')

                        conf2 = input('続けて他の計画を移動しますか？ - [No/n]')
                        if conf2 == 'n':
                            replaced_factory.append_factory_list()
                            factory_list = load_factory_list()
                            print('シミュレート用Factoryオブジェクト一覧')
                            print('*'*20)
                            i = 0
                            for factory in factory_list:
                                print(f'({i}) - {factory}')
                                i += 1
                            print('*'*20)
                            break
                    else:
                        print('\n')
                        print('中止します')
                        print('\n')

            elif command == 's':
                os.system('cls')
                print('計画リストをシャッフルする')
                print('\n')
                print('登録済みマスターFactoryオブジェクト')
                print('==== 計画リスト ====')
                factory = load_factory_object()
                factory.display_plan()
                print('*'*20)
                print('\n')
                print('==== 機械の状態 ====')
                factory.display_machine_status()
                print('\n')

                # Factory_list読み込み
                factory_list = load_factory_list()
                print('シミュレート用Factoryオブジェクト一覧')
                print('*'*20)
                i = 0
                for factory in factory_list:
                    print(f'({i}) - {factory}')
                    i += 1
                print('*'*20)

                print('シミュレート用Factoryオブジェクトに追加されます')
                frm = input('計画リストをシャッフルする範囲(開始位置) ---- ')
                to = input('計画リストをシャッフルする範囲(終了位置) ---- ')
                n = input('作成するFactoryオブジェクトの個数 ---- ')
                conf = input('実行しますか？ - [yes/y]')
                if conf == 'y':
                    shuffle_product_list(int(frm), int(to), int(n))
                    print('\n')

                    for factory in factory_list:
                        print(f'({i}) - {factory}')
                        i += 1
                        print('*'*20)
                        print('\n')

                else:
                    print('\n')
                    print('中止します')
                    print('\n')

        else:
            print('不正な入力です')
            print('\n')
            continue


def display_machine_info(db_path):
    """
    データベースに登録してある機械情報を表示する

    db_path: データベースのパス
    """
    while True:
        machine = input('機械名入力')
        print('\n')
        if not check_machine_name(machine, db_path):
            print('機械の登録がありません')
        else:
            break
    # データベース問い合わせ
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    cursor.execute(
        f"""
        SELECT
            symbol,
            type,
            setup,
            setting,
            same_type,
            same_diameter,
            same_length,
            error_rate,
            reset,
            trouble_rate,
            repair,
            active
        FROM
            machine
        WHERE
            symbol = '{machine}'
        """
    )
    res = cursor.fetchone()

    # 機械情報表示
    print('登録機械情報')
    print('*'*20)
    print(f'機械名: {res[0]}')
    print(f'タイプ: {res[1]}')
    print(f'段取り時間(分): {res[2]}')
    print(f'ワーク取付時間(分): {res[3]}')
    print('*'*20)
    print('\n')
    print('=== 段取り短縮設定 ===')
    print(f'同タイプの場合の段取り短縮比率: {res[4]}')
    print(f'同径の場合の段取り短縮比率: {res[5]}')
    print(f'同長の場合の段取り短縮比率: {res[6]}')
    print('\n')
    print('=== 故障、不具合の設定 ===')
    print(f'不具合発生確率(未実装): {res[7]}')
    print(f'不具合修正時間(未実装): {res[8]}')
    print(f'故障発生確率(未実装): {res[9]}')
    print(f'故障修理時間(未実装): {res[10]}')
    print('\n')
    print('=== 休工設定 ===')
    print(f'休工中:0 稼働可能:1 --- {res[11]}')
    print('*'*20)
    print('\n')


def update_machine_info(db_path):
    """
    データベースに登録済みの機械情報を更新する

    db_path: データベースのパス
    """
    while True:
        machine = input('機械名入力')
        print('\n')
        if not check_machine_name(machine, db_path):
            print('機械の登録がありません')
        else:
            break

    # データベース問い合わせ
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    cursor.execute(
        f"""
            SELECT
                symbol,
                type,
                setup,
                setting,
                same_type,
                same_diameter,
                same_length,
                error_rate,
                reset,
                trouble_rate,
                repair,
                active
            FROM
                machine
            WHERE
                symbol = '{machine}'
        """
    )
    res = cursor.fetchone()

    # 機械情報表示
    print('更新前登録情報')
    print('*'*20)
    print(f'機械名: {res[0]}')
    print(f'タイプ: {res[1]}')
    print(f'段取り時間(分): {res[2]}')
    print(f'ワーク取付時間(分): {res[3]}')
    print('*'*20)
    print('\n')
    print('=== 段取り短縮設定 ===')
    print(f'同タイプの場合の段取り短縮比率: {res[4]}')
    print(f'同径の場合の段取り短縮比率: {res[5]}')
    print(f'同長の場合の段取り短縮比率: {res[6]}')
    print('\n')
    print('=== 故障、不具合の設定 ===')
    print(f'不具合発生確率(未実装): {res[7]}')
    print(f'不具合修正時間(未実装): {res[8]}')
    print(f'故障発生確率(未実装): {res[9]}')
    print(f'故障修理時間(未実装): {res[10]}')
    print('\n')
    print('=== 休工設定 ===')
    print(f'休工中:0 稼働可能:1 --- {res[11]}')
    print('\n')
    # 更新情報入力
    print('==== 更新情報入力 ====')
    print(f'機械名: {res[0]}')
    print(f'タイプ: {res[1]}')

    while True:
        setup = input(f'段取り時間(分): ({res[2]}) ---- ')
        if len(setup) == 0:
            setup = res[2]
            break
        else:
            try:
                setup = float(setup)
                if setup < 0:
                    print('不正な入力です')
                else:
                    break
            except ValueError:
                print('不正な入力です')

    while True:
        setting = input(f'ワーク取付時間(分): ({res[3]}) ---- ')
        if len(setting) == 0:
            setting = res[3]
            break
        else:
            try:
                setting = float(setting)
                if setting < 0:
                    print('不正な入力です')
                else:
                    break
            except ValueError:
                print('不正な入力です')

    while True:
        print('=== 段取り短縮設定 ===')
        print('※同タイプ + 同径 + 同長 = 1になるように設定すること')
        print('※段取り時間は0.5で1/2、1.0で0になる')

        while True:
            same_type = input(f'同タイプの場合の段取り短縮比率: ({res[4]}) ---- ')
            if len(same_type) == 0:
                same_type = res[4]
                break
            else:
                try:
                    same_type = float(same_type)
                    if same_type < 0 or same_type > 1:
                        print('不正な入力です')
                    else:
                        break
                except ValueError:
                    print('不正な入力です')

        while True:
            same_diameter = input(f'同径の場合の段取り短縮比率: ({res[5]}) ---- ')
            if len(same_diameter) == 0:
                same_diameter = res[5]
                break
            else:
                try:
                    same_diameter = float(same_diameter)
                    if same_diameter < 0 or same_diameter > 1:
                        print('不正な入力です')
                    else:
                        break
                except ValueError:
                    print('不正な入力です')

        same_length = Decimal('1') - Decimal(str(same_type)) - Decimal(str(same_diameter))
        print(f'同径の場合の段取り短縮比率: {same_length}')
        if same_length < 0:
            print('\n')
            print('同タイプ + 同径 + 同長 = 1 となるように設定してください')
            print('\n')
        else:
            break

    print('=== 故障、不具合の設定 ===')
    while True:
        error_rate = input(f'不具合発生確率(未実装): ({res[7]}) ----')
        if len(error_rate) == 0:
            error_rate = res[7]
            break
        else:
            try:
                error_rate = float(error_rate)
                if error_rate < 0:
                    print('不正な入力です')
                else:
                    break
            except ValueError:
                print('不正な入力です')

    while True:
        reset = input(f'不具合修正時間(未実装): ({res[8]}) ----')
        if len(reset) == 0:
            reset = res[8]
            break
        else:
            try:
                reset = float(reset)
                if reset < 0:
                    print('不正な入力です')
                else:
                    break
            except ValueError:
                print('不正な入力です')

    while True:
        trouble_rate = input(f'故障発生確率(未実装): ({res[9]}) ----')
        if len(trouble_rate) == 0:
            trouble_rate = res[9]
            break
        else:
            try:
                trouble_rate = float(trouble_rate)
                if trouble_rate < 0:
                    print('不正な入力です')
                else:
                    break
            except ValueError:
                print('不正な入力です')

    while True:
        repair = input(f'故障修理時間(未実装): ({res[10]}) ----')
        if len(repair) == 0:
            repair = res[10]
            break
        else:
            try:
                repair = float(repair)
                if repair < 0:
                    print('不正な入力です')
                else:
                    break
            except ValueError:
                print('不正な入力です')

    print('=== 休工設定 ===')
    while True:
        active = input(f'休工中:0 稼働可能:1  - ({res[11]}) ----')
        if len(active) == 0:
            active = res[11]
            break
        elif active == '0' or active == '1':
            active = int(active)
            break
        else:
            print('0 または 1 を入力してください')

    print('\n')
    print('更新後登録情報')
    print('*'*20)
    print(f'機械名: {res[0]}')
    print(f'タイプ: {res[1]}')
    print(f'段取り時間(分): {setup}')
    print(f'ワーク取付時間(分): {setting}')
    print('*'*20)
    print('\n')
    print('=== 段取り短縮設定 ===')
    print(f'同タイプの場合の段取り短縮比率: {same_type}')
    print(f'同径の場合の段取り短縮比率: {same_diameter}')
    print(f'同長の場合の段取り短縮比率: {same_length}')
    print('\n')
    print('=== 故障、不具合の設定 ===')
    print(f'不具合発生確率(未実装): {error_rate}')
    print(f'不具合修正時間(未実装): {reset}')
    print(f'故障発生確率(未実装): {trouble_rate}')
    print(f'故障修理時間(未実装): {repair}')
    print('\n')
    print('=== 休工設定 ===')
    print(f'休工中:0 稼働可能:1 --- {active}')
    print('*'*20)
    print('\n')

    conf = input('更新しますか？ - [yes/y]')
    if conf == 'y':
        sql = f"""
            UPDATE
                machine
            SET
                setup = '{setup}',
                setting = '{setting}',
                same_type = '{same_type}',
                same_diameter = '{same_diameter}',
                same_length = '{same_length}',
                error_rate = '{error_rate}',
                reset = '{reset}',
                trouble_rate = '{trouble_rate}',
                repair = '{repair}',
                active = '{active}'
            WHERE
                symbol = '{res[0]}'
        """
        # print(sql)
        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)
        con.commit()
        con.close()


def view_machine(db_path):
    """機械情報設定
    """
    while True:
        print('#'*19, '機械情報設定', '#'*19)
        print('0 - 登録機械一覧')
        print('1 - 個別機械情報表示')
        print('2 - 機械情報更新')
        print('3 - 機械レイアウト表示')
        print('\n')
        print('exit() - 終了する')
        print('#'*(20 + 10 + 2 + 20))

        command_list = ['0', '1', '2', '3','exit()']
        command = input('SELECT EXECUTE No. ---')
        if command in command_list:
            print('\n')
            print(f'selstced - "{command}"')
            if command == 'exit()':
                os.system('cls')
                break
            elif command == '0':
                with sqlite3.connect(db_path) as con:
                    df = pd.read_sql(
                        """
                        SELECT
                            machine_id,
                            symbol,
                            type,
                            active
                        FROM
                            machine
                        """, con
                    )
                print(df.to_string(index=False))
                print('\n')
                continue
            elif command == '1':
                display_machine_info(db_path)
                print('\n')
                continue
            elif command == '2':
                update_machine_info(db_path)
                print('\n')
                continue
            elif command == '3':
                # Factory読み込み
                factory = load_factory_object()
                config = configparser.ConfigParser()
                config.read('config.ini', encoding='utf-8')
                d = config['DATE']['BASE_DATE'].split('/')
                BASE_DATE = datetime.datetime(
                    int(d[0]), int(d[1]), int(d[2])
                    )
                # シミュレーター起動
                print('='*20)
                print('シミュレーターを起動します')
                print('処理を続けるにはシミュレーターを終了してください')
                print('\n')
                app = Application(factory, BASE_DATE)
                app.mainloop()
                continue


def display_worker_info(db_path):
    # room_id: room_name の辞書を作成
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(
            """
            SELECT
                *
            FROM
                room
            """, con
        )
    room_dic = dict(zip(df['position_id'], df['room_name']))
    sex_dic = {'M': '男性', 'F': '女性'}

    while True:
        # 作業者情報表示
        with sqlite3.connect(db_path) as con:
            worker_df = pd.read_sql(
                """
                    SELECT
                        worker_id,
                        name,
                        age,
                        sex
                    FROM
                        worker
                """, con
            )
        print(
            worker_df[['worker_id', 'name', 'age', 'sex']].to_string(index=False)
        )

        worker_id = input('作業者ID(worker_id)入力 ---- ')

        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        cursor.execute(
            f"""
            SELECT
                worker_id,
                name,
                age,
                sex,
                m_speed,
                w_speed,
                arrive,
                leave,
                position,
                active
            FROM
                worker
            WHERE
                worker_id = '{worker_id}'
            """
        )
        res = cursor.fetchone()
        if not res:
            print('登録がありません')
        else:
            worker_id = int(worker_id)
            break

    # 登録情報表示
    print('登録作業者情報')
    print('*'*20)
    print('==== 基本情報 ====')
    print(f'作業者ID: {res[0]}')
    print(f'作業者名: {res[1]}')
    print(f'年齢: {res[2]}')
    print(f'性別: {sex_dic[res[3]]}')
    print('\n')
    print('==== 速度倍率 ====')
    print('標準: 1.0, ※2.0は標準の2倍の速さ')
    print(f'移動速度倍率: {res[4]}')
    print(f'作業速度倍率: {res[5]}')
    print('\n')
    print('==== 出退勤時間、場所 ====')
    print(f'出勤時間: {res[6]}')
    print(f'退勤時間: {res[7]}')
    print(f'出勤場所: {room_dic[int(res[8])]}')
    print('\n')
    print('==== 勤務の有無 ====')
    print('0: 勤務無し 1:勤務有り')
    print(f'勤務: {res[9]}')
    print('*'*20)


def update_worker_info(db_path):
    # room_id: room_name の辞書を作成
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(
            """
            SELECT
                *
            FROM
                room
            """, con
        )
    room_dic = dict(zip(df['position_id'], df['room_name']))
    sex_dic = {'M': '男性', 'F': '女性'}

    while True:
        # 作業者情報表示
        with sqlite3.connect(db_path) as con:
            worker_df = pd.read_sql(
                """
                    SELECT
                        worker_id,
                        name,
                        age,
                        sex
                    FROM
                        worker
                """, con
            )
        print(
            worker_df[['worker_id', 'name', 'age', 'sex']].to_string(index=False)
        )

        worker_id = input('作業者ID(worker_id)入力 ---- ')

        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        cursor.execute(
            f"""
            SELECT
                worker_id,
                name,
                age,
                sex,
                m_speed,
                w_speed,
                arrive,
                leave,
                position,
                active
            FROM
                worker
            WHERE
                worker_id = '{worker_id}'
            """
        )
        res = cursor.fetchone()
        if not res:
            print('登録がありません')
        else:
            worker_id = int(worker_id)
            break

    # 登録情報表示
    print('更新前作業者情報')
    print('*'*20)
    print('==== 基本情報 ====')
    print(f'作業者ID: {res[0]}')
    print(f'作業者名: {res[1]}')
    print(f'年齢: {res[2]}')
    print(f'性別: {sex_dic[res[3]]}')
    print('\n')
    print('==== 速度倍率 ====')
    print('標準: 1.0, ※2.0は標準の2倍の速さ')
    print(f'移動速度倍率: {res[4]}')
    print(f'作業速度倍率: {res[5]}')
    print('\n')
    print('==== 出退勤時間、場所 ====')
    print(f'出勤時間: {res[6]}')
    print(f'退勤時間: {res[7]}')
    print(f'出勤場所: {room_dic[int(res[8])]}')
    print('\n')
    print('==== 勤務の有無 ====')
    print('0: 勤務無し 1:勤務有り')
    print(f'勤務: {res[9]}')
    print('*'*20)
    print('\n')

    print('==== 基本情報設定 ====')
    while True:
        name = input(f'作業者名: ({res[1]}) ----')
        if len(name) == 0:
            name = res[1]
            break

    while True:
        age = input(f'年齢: ({res[2]}) ----')
        if len(age) == 0:
            age = res[2]
            break
        else:
            try:
                age = int(age)
                if age < 0:
                    print('不正な入力です')
                else:
                    break
            except ValueError:
                print('不正な入力です')

    while True:
        sex = input(f'性別 [M:男性, F: 女性]: ({res[3]}) ----')
        if len(sex) == 0:
            sex = res[3]
            break
        else:
            if sex == 'M' or sex == 'F':
                print(f'性別: {sex_dic[sex]}')
                break
            else:
                print('M または F を入力してください')

    print('==== 速度倍率設定 ====')
    while True:
        m_speed = input(f'移動速度倍率: ({res[4]}) ----')
        if len(m_speed) == 0:
            m_speed = res[4]
            break
        else:
            try:
                m_speed = float(m_speed)
                if m_speed < 0:
                    print('不正な入力です')
                else:
                    break
            except ValueError:
                print('不正な入力です')

    while True:
        w_speed = input(f'作業速度倍率: ({res[5]}) ----')
        if len(w_speed) == 0:
            w_speed = res[5]
            break
        else:
            try:
                w_speed = float(w_speed)
                if w_speed < 0:
                    print('不正な入力です')
                else:
                    break
            except ValueError:
                print('不正な入力です')

    hour_list = [str(i) for i in range(24)]
    minute_list = [str(i).zfill(2) for i in range(60)]
    print('==== 出退勤時間、場所設定 ====')
    while True:
        arrive_hour = input(
            f'出勤時刻(hour)を入力 - ({res[6].split(":")[0]}) 例)8, 12, 15 ----'
            )
        if len(arrive_hour) == 0:
            arrive_hour = res[6].split(":")[0]
            break
        else:
            if arrive_hour not in hour_list:
                print('不正な入力です')
            else:
                break
    while True:
        arrive_minute = input(
            f'出勤時刻(minute)を入力 - ({res[6].split(":")[1]}) 例)00, 05, 10 ----'
            )
        if len(arrive_minute) == 0:
            arrive_minute = res[6].split(":")[1]
            break
        else:
            if arrive_minute not in minute_list:
                print('不正な入力です')
            else:
                break
    arrive = arrive_hour + ':' + arrive_minute

    while True:
        leave_hour = input(
            f'退勤時刻(hour)を入力 - ({res[7].split(":")[0]}) 例)8, 12, 15 ----'
            )
        if len(leave_hour) == 0:
            leave_hour = res[7].split(":")[0]
            break
        else:
            if leave_hour not in hour_list:
                print('不正な入力です')
            else:
                break
    while True:
        leave_minute = input(
            f'退勤時刻(minute)を入力 - ({res[7].split(":")[1]}) 例)00, 05, 10 ----'
        )
        if len(leave_minute) == 0:
            leave_minute = res[7].split(":")[1]
            break
        else:
            if leave_minute not in minute_list:
                print('不正な入力です')
            else:
                break
    leave = leave_hour + ':' + leave_minute

    while True:
        position = input(
            f'出勤場所を選択[1:{room_dic[1]} 8:{room_dic[8]}] - ({res[8]})'
        )
        if len(position) == 0:
            position = int(res[8])
            break
        else:
            if position not in ['1', '8']:
                print('不正な入力です')
            else:
                position = int(position)
                break

    print('==== 勤務の有無 ====')
    while True:
        active = input(f'0: 勤務無し 1:勤務有り  - ({res[9]}) ----')
        if len(active) == 0:
            active = res[9]
            break
        elif active == '0' or active == '1':
            active = int(active)
            break
        else:
            print('0 または 1 を入力してください')
    print('\n')
    print('更新後登録情報')
    print('*'*20)
    print('==== 基本情報 ====')
    print(f'作業名: {name}')
    print(f'年齢: {age}')
    print(f'性別: {sex_dic[sex]}')
    print('\n')
    print('==== 速度倍率 ====')
    print(f'移動速度倍率: {m_speed}')
    print(f'作業速度倍率: {w_speed}')
    print('\n')
    print('==== 出退勤時間、場所 ====')
    print(f'出勤時間: {arrive}')
    print(f'退勤時間: {leave}')
    print(f'出勤場所: {room_dic[position]}')
    print('\n')
    print('==== 勤務の有無 ====')
    print('0: 勤務無し 1:勤務有り')
    print(f'勤務: {active}')
    print('*'*20)
    print('\n')

    conf = input('更新しますか？ - [yes/y]')
    if conf == 'y':
        sql = f"""
            UPDATE
                worker
            SET
                name = '{name}',
                age = '{age}',
                sex = '{sex}',
                m_speed = '{m_speed}',
                w_speed = '{w_speed}',
                arrive = '{arrive}',
                leave = '{leave}',
                position = '{position}',
                active = '{active}'
            WHERE
                worker_id = '{worker_id}'
        """
        # print(sql)
        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)
        con.commit()
        con.close()


def insert_worker_info(db_path):
    # room_id: room_name の辞書を作成
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(
            """
            SELECT
                *
            FROM
                room
            """, con
        )
    room_dic = dict(zip(df['position_id'], df['room_name']))
    sex_dic = {'M': '男性', 'F': '女性'}

    print('作業者新規登録')
    print('==== 基本情報設定 ====')
    while True:
        name = input('作業者名 - ')
        if len(name) == 0:
            print('作業者名を入力してください')
        else:
            break

    while True:
        age = input('年齢 - ')
        if len(age) == 0:
            print('整数を入力してください')
        else:
            try:
                age = int(age)
                break
            except ValueError:
                print('不正な入力です')

    while True:
        sex = input('性別[M:男性 F:女性] - ')
        if sex not in ['M', 'F']:
            print('MまたはFを入力してください')
        else:
            break

    print('==== 速度倍率設定 ====')
    while True:
        m_speed = input('移動速度倍率[標準:1.0]')
        if len(m_speed) == 0:
            m_speed = 1.0
            break
        else:
            try:
                m_speed = float(m_speed)
                break
            except ValueError:
                print('不正な入力です')

    while True:
        w_speed = input('作業速度倍率[標準:1.0]')
        if len(w_speed) == 0:
            w_speed = 1.0
            break
        else:
            try:
                w_speed = float(w_speed)
                break
            except ValueError:
                print('不正な入力です')

    hour_list = [str(i) for i in range(24)]
    minute_list = [str(i).zfill(2) for i in range(60)]
    print('==== 出退勤時間、場所設定 ====')
    while True:
        arrive_hour = input(f'出勤時刻(hour)を入力 例)8, 12, 15 ----')
        if arrive_hour not in hour_list:
            print('不正な入力です')
        else:
            break

    while True:
        arrive_minute = input(f'出勤時刻(minute)を入力 例)00, 05, 10 ----')
        if arrive_minute not in minute_list:
            print('不正な入力です')
        else:
            break
    arrive = arrive_hour + ':' + arrive_minute

    while True:
        leave_hour = input(f'退勤時刻(hour)を入力 例)8, 12, 15 ----')
        if leave_hour not in hour_list:
            print('不正な入力です')
        else:
            break

    while True:
        leave_minute = input(f'退勤時刻(minute)を入力 例)00, 05, 10 ----')
        if leave_minute not in minute_list:
            print('不正な入力です')
        else:
            break

    leave = leave_hour + ':' + leave_minute

    while True:
        position = input(f'出勤場所を選択[1:{room_dic[1]} 8:{room_dic[8]}] ----')
        if position not in ['1', '8']:
            print('不正な入力です')
        else:
            position = int(position)
            break

    print('==== 勤務の有無 ====')
    while True:
        active = input(f'0: 勤務無し 1:勤務有り ----')
        if active == '0' or active == '1':
            active = int(active)
            break
        else:
            print('0 または 1 を入力してください')

    print('\n')
    print('作業者情報')
    print('*'*20)
    print('==== 基本情報 ====')
    print(f'作業名: {name}')
    print(f'年齢: {age}')
    print(f'性別: {sex_dic[sex]}')
    print('\n')
    print('==== 速度倍率 ====')
    print(f'移動速度倍率: {m_speed}')
    print(f'作業速度倍率: {w_speed}')
    print('\n')
    print('==== 出退勤時間、場所 ====')
    print(f'出勤時間: {arrive}')
    print(f'退勤時間: {leave}')
    print(f'出勤場所: {room_dic[position]}')
    print('\n')
    print('==== 勤務の有無 ====')
    print('0: 勤務無し 1:勤務有り')
    print(f'勤務: {active}')
    print('*'*20)
    print('\n')

    conf = input('登録しますか？ - [yes/y]')
    if conf == 'y':
        sql = f"""
            INSERT
            INTO
                worker(
                    name, age, sex, m_speed, w_speed,
                    arrive, leave, position, active
                )
            VALUES(
                '{name}', '{age}', '{sex}', '{m_speed}', '{w_speed}',
                '{arrive}', '{leave}', '{position}', '{active}'
            )
        """
        # print(sql)
        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)
        con.commit()
        # worker_id取得
        cursor = con.cursor()
        cursor.execute(f'select worker_id from worker where name = "{name}"')
        worker_id = cursor.fetchone()[0]
        charge_sql = f"""
            INSERT
            INTO
                charge(worker_id, charge)
            VALUES({worker_id}, '')
        """
        cursor = con.cursor()
        try:
            cursor.execute(charge_sql)
        except sqlite3.Error as e:
            print(e)
        con.commit()
        con.close()


def view_worker(db_path):
    """作業者情報設定
    """
    while True:
        print('#'*19, '作業者情報設定', '#'*19)
        print('0 - 作業者情報一覧')
        print('1 - 個別作業者情報表示')
        print('2 - 作業者情報更新')
        print('3 - 作業者追加')
        print('4 - 作業者登録削除')
        print('\n')
        print('exit() - 終了する')
        print('#'*(20 + 10 + 2 + 20))

        command_list = ['0', '1', '2', '3', '4', 'exit()']
        command = input('SELECT EXECUTE No. ---')
        if command in command_list:
            print('\n')
            print(f'selstced - "{command}"')
            if command == 'exit()':
                os.system('cls')
                break
            elif command == '0':
                with sqlite3.connect(db_path) as con:
                    df = pd.read_sql(
                        """
                        SELECT
                            *
                        FROM
                            worker
                        """, con
                    )
                print(df)
                print('\n')
                continue
            elif command == '1':
                display_worker_info(db_path)
                print('\n')
                continue
            elif command == '2':
                update_worker_info(db_path)
                print('\n')
                continue
            elif command == '3':
                insert_worker_info(db_path)
                print('\n')
                continue
            elif command == '4':
                with sqlite3.connect(db_path) as con:
                    df = pd.read_sql(
                        """
                        SELECT
                            worker_id as id,
                            name,
                            age,
                            sex
                        FROM
                            worker
                        """, con
                    )
                print(df.to_string(index=False))
                sex_dic = {'M': '男性', 'F': '女性'}
                while True:
                    worker_id = input('削除する作業者のidを入力して下さい ----')
                    try:
                        worker_id = int(worker_id)
                    except ValueError:
                        print('不正な入力です')
                    con = sqlite3.connect(db_path)
                    cursor = con.cursor()
                    cursor.execute(
                        f"""
                            SELECT
                                worker_id as id,
                                name,
                                age,
                                sex
                            FROM
                                worker
                            WHERE
                                id = '{worker_id}'
                        """
                    )
                    res = cursor.fetchone()
                    print('==== 作業者情報 ====')
                    print(f'id: {res[0]}')
                    print(f'作業者名: {res[1]}')
                    print(f'年齢: {res[2]}')
                    print(f'性別: {sex_dic[res[3]]}')
                    print('\n')
                    conf = input('削除してよろしいですか - [yes/y]')
                    if conf == 'y':
                        cursor = con.cursor()
                        cursor.execute(
                            f"""
                            DELETE
                            FROM
                                worker
                            WHERE
                                worker_id = '{res[0]}'
                            """
                        )
                        cursor = con.cursor()
                        cursor.execute(
                            f"""
                            DELETE
                            FROM
                                charge
                            WHERE
                                worker_id = '{res[0]}'
                            """
                        )
                        con.commit()
                        con.close()
                        break
                    else:
                        cancel = input('中止しますか？- [yes/y]')
                        if cancel == 'y':
                            print('中止しました')
                            break
                    print('\n')
                continue


def display_all_worker_schedule(db_path):
    """
    データベースに登録されているすべてのスケジュールを表示する

    db_path: データベースのパス
    """
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(
            f"""
                SELECT
                    schedule.worker_id,
                    worker.name,
                    task,
                    schedule.week_id,
                    week.eng as week,
                    schedule.position_id,
                    room.room_name as room,
                    start,
                    end
                FROM
                    schedule
                INNER JOIN
                    worker
                ON
                    worker.worker_id = schedule.worker_id
                INNER JOIN
                    week
                ON
                    week.week_id = schedule.week_id
                INNER JOIN
                    room
                ON
                    room.position_id = schedule.position_id
                ORDER BY
                    schedule.worker_id,
                    schedule.week_id,
                    schedule.start
            """, con
        )
    os.system('cls')
    print('\n')
    print(df[['name', 'task', 'week', 'room', 'start', 'end']])
    print('\n')


def display_worker_schedule(db_path):
    """
    作業者のスケジュールを表示する

    db_path: データベースのパス
    """
    while True:
        while True:
            # 作業者情報表示
            with sqlite3.connect(db_path) as con:
                worker_df = pd.read_sql(
                    """
                    SELECT
                        worker_id,
                        name,
                        age,
                        sex
                    FROM
                        worker
                    """, con
                )
            print(
                worker_df[['worker_id', 'name', 'age', 'sex']].to_string(index=False)
            )

            # 作業者選択
            worker_id = input('SELECT WORKER ID ---- ')
            try:
                worker_id = int(worker_id)
                con = sqlite3.connect(db_path)
                cursor = con.cursor()
                cursor.execute(
                    f"""
                    SELECT
                        worker_id
                    FROM
                        worker
                    WHERE
                        worker_id ='{worker_id}'
                    """
                )
                res = cursor.fetchone()
                if res:
                    break
                else:
                    print('作業者の登録がありません')
            except ValueError:
                print('不正な入力です')

        with sqlite3.connect(db_path) as con:
            df = pd.read_sql(
                f"""
                    SELECT
                        schedule.worker_id,
                        worker.name,
                        task,
                        schedule.week_id,
                        week.eng as week,
                        schedule.position_id,
                        room.room_name as room,
                        start,
                        end
                    FROM
                        schedule
                    INNER JOIN
                        worker
                    ON
                        worker.worker_id = schedule.worker_id
                    INNER JOIN
                        week
                    ON
                        week.week_id = schedule.week_id
                    INNER JOIN
                        room
                    ON
                        room.position_id = schedule.position_id
                    WHERE
                        schedule.worker_id = '{worker_id}'
                    ORDER BY
                        schedule.worker_id,
                        schedule.week_id,
                        schedule.start
                """, con
            )
        os.system('cls')
        print('\n')
        print(df[['name', 'task', 'week', 'room', 'start', 'end']])
        print('\n')
        conf = input('他の作業者を表示しますか？ - [yes/y]')
        if conf != 'y':
            break


def return_worker_schedule_info(db_path):
    """
    作業者IDを選択して作業者のスケジュールを表示し
    作業者のスケジュールの
    DataFrame, worker_idを返す

    使い方: df, worker_id = return_worker_schedule_info(db_path)

    db_path: データベースのパス
    """
    # 作業者情報表示
    with sqlite3.connect(db_path) as con:
        worker_df = pd.read_sql(
            """
            SELECT
                worker_id,
                name,
                age,
                sex
            FROM
                worker
            """, con
        )
    print(
        worker_df[['worker_id', 'name', 'age', 'sex']].to_string(index=False)
    )

    # 作業者選択
    while True:
        worker_id = input('SELECT WORKER ID ---- ')
        try:
            worker_id = int(worker_id)
            con = sqlite3.connect(db_path)
            cursor = con.cursor()
            cursor.execute(
                f"""
                SELECT
                    worker_id
                FROM
                    worker
                WHERE
                    worker_id ='{worker_id}'
                """
            )
            res = cursor.fetchone()
            if res:
                break
            else:
                print('作業者の登録がありません')
        except ValueError:
            print('不正な入力です')

    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(
            f"""
                SELECT
                    schedule.worker_id,
                    worker.name,
                    task,
                    schedule.week_id,
                    week.eng as week,
                    schedule.position_id,
                    room.room_name as room,
                    start,
                    end
                FROM
                    schedule
                INNER JOIN
                    worker
                ON
                    worker.worker_id = schedule.worker_id
                INNER JOIN
                    week
                ON
                    week.week_id = schedule.week_id
                INNER JOIN
                    room
                ON
                    room.position_id = schedule.position_id
                WHERE
                    schedule.worker_id = '{worker_id}'
                ORDER BY
                    schedule.worker_id,
                    schedule.week_id,
                    schedule.start
            """, con
        )
    # print(df[['name', 'task', 'week', 'room', 'start', 'end']])

    return df, worker_id


def return_worker_schedule_daily_info(db_path):
    """
    作業者ID, 曜日を選択して作業者のスケジュールを表示し
    作業者、曜日で選択されたスケジュールの
    DataFrame, worker_id, week_idを返す

    使い方: df, worker_id, week_id = return_worker_schedule_daily_info(db_path)

    db_path: データベースのパス
    """
    # 作業者情報表示
    with sqlite3.connect(db_path) as con:
        worker_df = pd.read_sql(
            """
            SELECT
                worker_id,
                name,
                age,
                sex
            FROM
                worker
            """, con
        )
    print(
        worker_df[['worker_id', 'name', 'age', 'sex']].to_string(index=False)
    )

    # 作業者選択
    while True:
        worker_id = input('SELECT WORKER ID ---- ')
        try:
            worker_id = int(worker_id)
            con = sqlite3.connect(db_path)
            cursor = con.cursor()
            cursor.execute(
                f"""
                SELECT
                    worker_id
                FROM
                    worker
                WHERE
                    worker_id ='{worker_id}'
                """
            )
            res = cursor.fetchone()
            if res:
                break
            else:
                print('作業者の登録がありません')
        except ValueError:
            print('不正な入力です')

    # 曜日を選択
    while True:
        print('1: Sun 2:Mon 3:Tue 4:Wed 5:Thu 6:Fri 7:Sat')
        week_id = input('SELECT WEEK No.')
        try:
            week_id = int(week_id)
            if week_id in [i for i in range(1, 8)]:
                break
            else:
                print('不正な入力です')
        except ValueError:
            print('不正な入力です')
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(
            f"""
                SELECT
                    schedule.worker_id,
                    worker.name,
                    task,
                    schedule.week_id,
                    week.eng as week,
                    schedule.position_id,
                    room.room_name as room,
                    start,
                    end
                FROM
                    schedule
                INNER JOIN
                    worker
                ON
                    worker.worker_id = schedule.worker_id
                INNER JOIN
                    week
                ON
                    week.week_id = schedule.week_id
                INNER JOIN
                    room
                ON
                    room.position_id = schedule.position_id
                WHERE
                    schedule.worker_id = '{worker_id}'
                    and
                    week.week_id = '{week_id}'
                ORDER BY
                    schedule.start
            """, con
        )
    # print(df[['name', 'task', 'week', 'room', 'start', 'end']])

    return df, worker_id, week_id


def chek_schedule_times(check_times_list, registered_times_list):
    """
    check_time_listの時間帯がregistered_time_list内の時間帯に干渉しないかチェックする
    干渉がなければTrueを、干渉があればFalseを返す
    check_times_listのstartがendより大きい、または等しい場合はFalseを返す

    check_times_list: [start, end] 例)[2000, 3000]
    registered_times_list: [[start1, end1], [start2, end2]] 例)[[0, 1000], [2000, 3000],....]
    """
    check = 0
    for r_times in registered_times_list:
        if r_times[0] <= check_times_list[0] < r_times[1]:
            check += 1
            # print('case(1-1)')
        if r_times[0] < check_times_list[1] <= r_times[1]:
            check += 1
            # print('case(1-2)')
    for r_times in registered_times_list:
        if check_times_list[0] <= r_times[0] < check_times_list[1]:
            check += 1
            # print('case(2-1)')
        if check_times_list[0] < r_times[1] <= check_times_list[1]:
            check += 1
            # print('case(2-2)')
    if check_times_list[0] >= check_times_list[1]:
        check += 1
        # print('case(3)')
    if check == 0:
        return True
    else:
        return False


def edit_schedule(db_path):
    """
    データベースに登録された作業者のスケジュールを更新する

    db_path: データベースのパス
    """
    while True:
        # 更新前情報表示
        df, worker_id, week_id = return_worker_schedule_daily_info(db_path)
        print('\n')
        print('==== 登録データ ====')
        print(df[['name', 'task', 'week', 'room', 'start', 'end']])
        print('\n')
        if len(df) == 0:
            print(('データがありません'))
        else:
            break

    # 更新データ選択
    while True:
        select = input('SELECT EDIT No.')
        try:
            select = int(select)
            if 0 <= select < len(df):
                break
            else:
                print('不正な入力です')
        except ValueError:
            print('不正な入力です')
        # print(df.iloc[select])

    # worker_id = df.iloc[select]['worker_id']
    worker = df.iloc[select]['name']
    pre_task = df.iloc[select]['task']
    # week_id = df.iloc[select]['week_id']
    week = df.iloc[select]['week']
    pre_position_id = df.iloc[select]['position_id']
    pre_room = df.iloc[select]['room']
    pre_start = df.iloc[select]['start']
    pre_end = df.iloc[select]['end']

    # task名
    new_task = input(f'input task name(更新前: {pre_task}) ---- ')
    if len(new_task) == 0:
        new_task = pre_task

    # 部屋
    with sqlite3.connect(db_path) as con:
        room_df = pd.read_sql(
            """
            SELECT
                *
            FROM
                room
            """, con
        )
    room_list = room_df.values.tolist()
    rooms_str = ''
    room_no_list = []
    room_dic = {}
    room_list = room_df.values.tolist()
    for room in room_list:
        room_no_list.append(room[0])
        room_dic[room[0]] = room[1]
        rooms_str += str(room[0]) + ': ' + room[1] + ' '
    while True:
        room_id = input(
            f'SLECT TASK ROOM No({pre_position_id}) - [{rooms_str}]'
        )
        if len(room_id) == 0:
            room_id = pre_position_id
            break
        else:
            try:
                room_id = int(room_id)
                if room_id in room_no_list:
                    break
                else:
                    print('不正な入力です')
            except ValueError:
                print('不正な入力です')

    # 時刻入力確認用リスト
    hour_list = [str(i) for i in range(24)]
    minute_list = [str(i).zfill(2) for i in range(60)]

    while True:
        # 作業開始時間
        while True:
            s_hour = input(
                f"""
                input start hour(更新前: {pre_start.split(':')[0]}) 例)8, 12, 15 ---- 
                """
                )
            if len(s_hour) == 0:
                s_hour = pre_start.split(":")[0]
                break
            else:
                if s_hour not in hour_list:
                    print('不正な入力です')
                else:
                    break
        while True:
            s_minute = input(
                f"""
                input start minute(更新前: {pre_start.split(':')[1]}) 例)00, 05, 10 ---- 
                """
                )
            if len(s_minute) == 0:
                s_minute = pre_start.split(":")[1]
                break
            else:
                if s_minute not in minute_list:
                    print('不正な入力です')
                else:
                    break
        start = s_hour + ':' + s_minute

        # 作業終了時間
        while True:
            e_hour = input(
                f"""
                input end hour(更新前: {pre_end.split(':')[0]}) 例)8, 12, 15 ---- 
                """
                )
            if len(e_hour) == 0:
                e_hour = pre_end.split(":")[0]
                break
            else:
                if e_hour not in hour_list:
                    print('不正な入力です')
                else:
                    break
        while True:
            e_minute = input(
                f"""
                input end minute(更新前: {pre_end.split(':')[1]}) 例)00, 05, 10 ---- 
                """
            )
            if len(e_minute) == 0:
                e_minute = pre_end.split(":")[1]
                break
            else:
                if e_minute not in minute_list:
                    print('不正な入力です')
                else:
                    break
        end = e_hour + ':' + e_minute

        # スケジュール時間重複チェック
        check_times_list = [
            time_converter(START_TIME, start), time_converter(START_TIME, end)
        ]
        registered_times_list = []
        lst = df.values.tolist()
        lst.pop(select)
        """
        ==== DataFrame構成 ====
        df.columns = [
            'worker_id', 'name', 'task', 'week_id', 'week',
            'position_id', 'room', 'start', 'end'
       ]
        """
        for l in lst:
            times = [
                time_converter(START_TIME, l[7]), time_converter(START_TIME, l[8])
            ]
            registered_times_list.append(times)
        if chek_schedule_times(check_times_list, registered_times_list):
            break
        else:
            print('スケジュールが重複しているか、入力が不正です')

    # 更新前情報表示
    print('\n')
    print('==== 更新前 ====')
    print(f'作業者名: {worker}')
    print(f'week: {week}')
    print(f'task: {pre_task}')
    print(f'room: {pre_room}')
    print(f'start: {pre_start}')
    print(f'end: {pre_end}')

    # 更新後情報表示
    print('\n')
    print('==== 更新後 ====')
    print(f'作業者名: {worker}')
    print(f'week: {week}')
    print(f'task: {new_task}')
    print(f'room: {room_dic[room_id]}')
    print(f'start: {start}')
    print(f'end: {end}')
    print('\n')

    # 確認
    conf = input('更新しますか？ - [yes/y]')
    if conf == 'y':
        sql = (
            f"""
            UPDATE
                schedule
            SET
                task = '{new_task}',
                position_id = '{room_id}',
                start = '{start}',
                end = '{end}'
            WHERE
                worker_id = '{worker_id}'
                AND
                task = '{pre_task}'
                AND
                week_id = '{week_id}'
                AND
                position_id = '{pre_position_id}'
                AND
                start = '{pre_start}'
                AND
                end = '{pre_end}'
        """
        )
        # print(sql)
        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)
        con.commit()
        con.close()


def append_schedule(db_path):
    """
    スケジュールを追加する

    db_path: データベースのパス
    """
    while True:
        # 登録前情報表示
        df, worker_id, week_id = return_worker_schedule_daily_info(db_path)
        print('\n')
        print('==== 登録データ ====')
        if len(df) == 0:
            print('登録情報なし')
        else:
            print(df[['name', 'task', 'week', 'room', 'start', 'end']])
        print('\n')
        break

    # worker_id = df.iloc[0]['worker_id']
    # worker = df.iloc[0]['name']
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    cursor.execute(f'select name from worker where worker_id = "{worker_id}"')
    res = cursor.fetchone()
    worker = res[0]
    # week_id = df.iloc[0]['week_id']
    # week = df.iloc[0]['week']
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    cursor.execute(f'select eng from week where week_id = "{week_id}"')
    res = cursor.fetchone()
    week = res[0]

    # 追加データ入力
    # task名
    while True:
        new_task = input('input task name ---- ')
        if len(new_task) == 0:
            print('不正な入力です')
        else:
            break

    # 部屋
    with sqlite3.connect(db_path) as con:
        room_df = pd.read_sql(
            """
            SELECT
                *
            FROM
                room
            """, con
        )
    room_list = room_df.values.tolist()
    rooms_str = ''
    room_no_list = []
    room_dic = {}
    room_list = room_df.values.tolist()
    for room in room_list:
        room_no_list.append(room[0])
        room_dic[room[0]] = room[1]
        rooms_str += str(room[0]) + ': ' + room[1] + ' '
    while True:
        room_id = input(f'SLECT TASK ROOM No. - [{rooms_str}]')
        try:
            room_id = int(room_id)
            if room_id in room_no_list:
                break
            else:
                print('不正な入力です')
        except ValueError:
            print('不正な入力です')

    # 時刻入力確認用リスト
    hour_list = [str(i) for i in range(24)]
    minute_list = [str(i).zfill(2) for i in range(60)]

    while True:
        # 作業開始時間
        while True:
            s_hour = input('input start hour 例)8, 12, 15 ---- ')
            if s_hour not in hour_list:
                print('不正な入力です')
            else:
                break
        while True:
            s_minute = input('input start minute 例)00, 05, 10 ---- ')
            if s_minute not in minute_list:
                print('不正な入力です')
            else:
                break
        start = s_hour + ':' + s_minute

        # 作業終了時間
        while True:
            e_hour = input('input end hour 例)8, 12, 15 ---- ')
            if e_hour not in hour_list:
                print('不正な入力です')
            else:
                break
        while True:
            e_minute = input('input end minute 例)00, 05, 10 ---- ')
            if e_minute not in minute_list:
                print('不正な入力です')
            else:
                break
        end = e_hour + ':' + e_minute

        # スケジュール時間重複チェック
        check_times_list = [
            time_converter(START_TIME, start), time_converter(START_TIME, end)
        ]
        registered_times_list = []
        lst = df.values.tolist()
        """
        ==== DataFrame構成 ====
        df.columns = [
            'worker_id', 'name', 'task', 'week_id', 'week',
            'position_id', 'room', 'start', 'end'
       ]
        """
        for l in lst:
            times = [
                time_converter(START_TIME, l[7]), time_converter(START_TIME, l[8])
            ]
            registered_times_list.append(times)
        if chek_schedule_times(check_times_list, registered_times_list):
            break
        else:
            print('スケジュールが重複しているか、入力が不正です')

    # 登録情報表示
    print('\n')
    print('==== 登録情報 ====')
    print(f'作業者名: {worker}')
    print(f'week: {week}')
    print(f'task: {new_task}')
    print(f'room: {room_dic[room_id]}')
    print(f'start: {start}')
    print(f'end: {end}')
    print('\n')

    # 確認
    conf = input('更新しますか？ - [yes/y]')
    if conf == 'y':
        sql = (
            f"""
            INSERT
            INTO
                schedule(
                    worker_id, task, week_id, position_id, start, end
                )
            VALUES(
                '{worker_id}', '{new_task}', '{week_id}',
                '{room_id}', '{start}', '{end}'
        )
        """
        )
        # print(sql)
        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)
        con.commit()
        con.close()


def delete_schedule(db_path):
    """
    データベースに登録された作業者のスケジュールを削除する

    db_path: データベースのパス
    """
    while True:
        # 削除前情報表示
        df, worker_id, week_id = return_worker_schedule_daily_info(db_path)
        print('\n')
        print('==== 登録データ ====')
        print(df[['name', 'task', 'week', 'room', 'start', 'end']])
        print('\n')
        if len(df) == 0:
            print(('データがありません'))
        else:
            break

    # 削除データ選択
    while True:
        select = input('SELECT EDIT No.')
        try:
            select = int(select)
            if 0 <= select < len(df):
                break
            else:
                print('不正な入力です')
        except ValueError:
            print('不正な入力です')
        # print(df.iloc[select])

    # worker_id = df.iloc[select]['worker_id']
    worker = df.iloc[select]['name']
    pre_task = df.iloc[select]['task']
    # week_id = df.iloc[select]['week_id']
    week = df.iloc[select]['week']
    pre_position_id = df.iloc[select]['position_id']
    pre_room = df.iloc[select]['room']
    pre_start = df.iloc[select]['start']
    pre_end = df.iloc[select]['end']

    # 削除前情報表示
    print('\n')
    print('==== 削除データ ====')
    print(f'作業者名: {worker}')
    print(f'week: {week}')
    print(f'task: {pre_task}')
    print(f'room: {pre_room}')
    print(f'start: {pre_start}')
    print(f'end: {pre_end}')
    print('\n')

    # 確認
    conf = input('削除しますか？ - [yes/y]')
    if conf == 'y':
        sql = (
            f"""
            DELETE
            FROM
                schedule
            WHERE
                worker_id = '{worker_id}'
                AND
                task = '{pre_task}'
                AND
                week_id = '{week_id}'
                AND
                position_id = '{pre_position_id}'
                AND
                start = '{pre_start}'
                AND
                end = '{pre_end}'
            """
        )
        # print(sql)
        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        try:
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(e)
        con.commit()
        con.close()


def copy_schedule(db_path):
    """
    登録済みのスケジュールデータをすべて削除し
    他の作業者のスケジュールを全てコピーして登録する

    db_path: データベースのパス
    """

    while True:
        # 削除情報表示
        print('コピー先情報を表示')
        df, worker_id = return_worker_schedule_info(db_path)
        print('\n')
        print('==== 登録データ ====')
        print(df[['name', 'task', 'week', 'room', 'start', 'end']])
        print('\n')
        # if len(df) == 0:
        #    print(('データがありません'))
        #else:
        conf = input('他の作業者を選択しますか - [yes/y]')
        if conf != 'y':
            break

    while True:
        # 参照情報表示
        print('コピー元情報を表示')
        ori_df, ori_worker_id = return_worker_schedule_info(db_path)
        print('\n')
        print('==== 登録データ ====')
        print(ori_df[['name', 'task', 'week', 'room', 'start', 'end']])
        print('\n')
        if len(ori_df) == 0:
            print(('データがありません'))
        else:
            conf = input('他の作業者を選択しますか - [yes/y]')
            if conf != 'y':
                break

    print('\n')
    print('*'*40)
    print('==== コピー元スケジュール情報 ====')
    print(ori_df[['task', 'week', 'room', 'start', 'end']])
    print('\n')
    print('↓↓↓↓↓↓↓↓↓↓↓')
    print('\n')
    print('==== コピー先スケジュール情報 ====')
    print('※コピーを実行するとこれらはすべて削除されます')
    print(df[['name', 'task', 'week', 'room', 'start', 'end']])
    print('\n')

    print('※※※※※※※※ 注意 ※※※※※※※※')
    print('コピーを実行するとコピー先にすでに登録されているデータは最初に初期化されます')
    conf = input('コピーを実行しますか？ - [yes/y]')
    if conf == 'y':
        del_sql = (
            f"""
            DELETE FROM schedule WHERE worker_id = '{worker_id}'
            """
        )

        # コピー元のDataFrameのworker_idをコピー先のworker_idに変更
        ori_df.loc[ori_df.worker_id == ori_worker_id, 'worker_id'] = worker_id
        insert_df = ori_df[
            ['worker_id', 'task', 'week_id', 'position_id', 'start', 'end']
        ]
        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        try:
            cursor.execute(del_sql)
            insert_df.to_sql('schedule', con, if_exists='append', index=False)
        except sqlite3.Error as e:
            print(e)
        con.commit()
        con.close()


def view_schedule(db_path):
    """スケジュール設定
    """
    while True:
        print('#'*17, 'スケジュール設定', '#'*17)
        print('0 - スケジュール情報一覧')
        print('1 - 作業者個人スケジュール表示')
        print('2 - スケジュール更新')
        print('3 - スケジュール追加')
        print('4 - スケジュール削除')
        print('5 - スケジュール一括コピー')
        print('\n')
        print('exit() - 終了する')
        print('#'*(17 + 16 + 2 + 17))

        command_list = ['0', '1', '2', '3', '4', '5', 'exit()']
        command = input('SELECT EXECUTE No. ---')
        if command in command_list:
            print('\n')
            print(f'selstced - "{command}"')
            if command == 'exit()':
                os.system('cls')
                break
            elif command == '0':
                display_all_worker_schedule(db_path)
                print('\n')
                continue
            elif command == '1':
                display_worker_schedule(db_path)
                print('\n')
                continue
            elif command == '2':
                edit_schedule(db_path)
                print('\n')
                continue
            elif command == '3':
                append_schedule(db_path)
                print('\n')
                continue
            elif command == '4':
                delete_schedule(db_path)
                print('\n')
                continue
            elif command == '5':
                copy_schedule(db_path)
                print('\n')
                continue


def appended_charge_list(worker_id, charge_list, db_path):
    """
    charge_listに機械名を追加して新しい担当機械リストをデータベースに登録する

    worker_id: データベースに登録済みのworker_id
    charge_list: 追加前の担当機械リスト 例) ['M1', 'M2', 'M3', ....]
    db_path: データベースのパス
    """
    while True:
        new_charge = input('追加する担当機械を入力 - ')
        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        cursor.execute(f'select * from machine where symbol = "{new_charge}"')
        res = cursor.fetchone()
        if not res:
            print('機械が登録がされていません')
            conf5 = input('中止しますか？ - [yes/y]')
            if conf5 == 'y':
                break
        elif new_charge in charge_list:
            print('すでに担当に割り当てられています')
            conf4 = input('中止しますか？ - [yes/y]')
            if conf4 == 'y':
                break
        else:
            print('\n')
            print('*'*20)
            print(f'担当機械リスト: {charge_list}')
            print(f'追加する担当機械: {new_charge}')
            conf = input('機械を担当リストに追加しますか - [yes/y]')
            if conf == 'y':
                charge_list.append(new_charge)
                # リストを文字列に変換
                symbols = ','.join(charge_list)
                # 機械名のリストの文字列をmachine_idのリストの文字列に変換
                charge_id_list = encode_symbols_to_machine_ids(
                    symbols, db_path
                    )
                sql = (
                    f"""
                        UPDATE
                            charge
                        SET
                            charge = '{charge_id_list}'
                        WHERE
                            worker_id = '{worker_id}'
                    """
                )
                # print(sql)
                con = sqlite3.connect(db_path)
                cursor = con.cursor()
                try:
                    cursor.execute(sql)
                except sqlite3.Error as e:
                    print(e)
                con.commit()
                con.close()
                conf2 = input('続けて追加しますか？ - [yes/y]')
                if conf2 != 'y':
                    break
            else:
                conf3 = input('中止しますか？ - [yes/y]')
                if conf3 == 'y':
                    break


def delete_charge_list(worker_id, charge_list, db_path):
    """
    charge_listに機械名を追加して新しい担当機械リストをデータベースに登録する

    worker_id: データベースに登録済みのworker_id
    charge_list: 追加前の担当機械リスト 例) ['M1', 'M2', 'M3', ....]
    db_path: データベースのパス
    """
    if not charge_list:
        print('担当機械の登録がありません')
    else:
        while True:
            del_charge = input('削除する担当機械を入力 - ')
            if del_charge not in charge_list:
                print('機械が割り当てられていません')
                conf4 = input('中止しますか？ - [yes/y]')
                if conf4 == 'y':
                    break
            else:
                print('\n')
                print('*'*20)
                print(f'担当機械リスト: {charge_list}')
                print(f'削除する担当機械: {del_charge}')
                conf = input('機械を担当リストから削除しますか - [yes/y]')
                if conf == 'y':
                    charge_list.remove(del_charge)
                    # リストを文字列に変換
                    symbols = ','.join(charge_list)
                    # 機械名のリストの文字列をmachine_idのリストの文字列に変換
                    charge_id_list = encode_symbols_to_machine_ids(
                        symbols, db_path
                        )
                    sql = (
                        f"""
                            UPDATE
                                charge
                            SET
                                charge = '{charge_id_list}'
                            WHERE
                                worker_id = '{worker_id}'
                        """
                    )
                    # print(sql)
                    con = sqlite3.connect(db_path)
                    cursor = con.cursor()
                    try:
                        cursor.execute(sql)
                    except sqlite3.Error as e:
                        print(e)
                    con.commit()
                    con.close()
                    conf2 = input('続けて削除しますか？ - [yes/y]')
                    if conf2 != 'y':
                        break
                else:
                    conf3 = input('中止しますか？ - [yes/y]')
                    if conf3 == 'y':
                        break


def view_charge_list(db_path):
    """
    作業者の担当機械のリストを表示する

    db_path: データベースのパス
    """
    # 作業者情報表示
    with sqlite3.connect(db_path) as con:
        worker_df = pd.read_sql(
            """
            SELECT
                worker_id,
                name,
                age,
                sex
            FROM
                worker
            """, con
        )

    # 作業者選択
    while True:
        print(
            worker_df[
                ['worker_id', 'name', 'age', 'sex']
                ].to_string(index=False)
            )
        worker_id = input('SELECT WORKER ID ---- ')
        try:
            worker_id = int(worker_id)
            con = sqlite3.connect(db_path)
            cursor = con.cursor()
            cursor.execute(
                f"""
                SELECT
                    worker_id,
                    name
                FROM
                    worker
                WHERE
                    worker_id ='{worker_id}'
                """
            )
            res = cursor.fetchone()

            if res:
                charge_list = read_charge_list(res[1], db_path)
                print('\n')
                print('==== 登録済み担当機械 ====')
                print(f'担当者: {res[1]}')
                print(f'担当機械: {charge_list}')
                print('\n')
                print('0 - 機械リスト参照')
                print('1 - 機械レイアウト参照(シミュレーター画面起動)')
                print('\n')
                print('a - 担当機械追加')
                print('d - 担当機械削除')
                print('\n')
                print('exit() - 終了')
                print('\n')

                command_list = ['0', '1', 'a', 'd', 'exit()']
                command = input('SELECT No.')
                if command not in command_list:
                    print('不正な入力です')
                    continue
                elif command == 'exit()':
                    break
                elif command == '0':
                    with sqlite3.connect(db_path) as con:
                        df = pd.read_sql(
                            """
                            SELECT
                                machine_id,
                                symbol,
                                type,
                                active
                            FROM
                                machine
                            """, con
                        )
                    print(df.to_string(index=False))
                elif command == '1':
                    # Factory読み込み
                    factory = load_factory_object()
                    config = configparser.ConfigParser()
                    config.read('config.ini', encoding='utf-8')
                    d = config['DATE']['BASE_DATE'].split('/')
                    BASE_DATE = datetime.datetime(
                        int(d[0]), int(d[1]), int(d[2])
                        )
                    # シミュレーター起動
                    print('='*20)
                    print('シミュレーターを起動します')
                    print('処理を続けるにはシミュレーターを終了してください')
                    print('\n')
                    app = Application(factory, BASE_DATE)
                    app.mainloop()
                    continue
                elif command == 'a':
                    # os.system('cls')
                    appended_charge_list(worker_id, charge_list, db_path)
                    continue
                elif command == 'd':
                    # os.system('cls')
                    delete_charge_list(worker_id, charge_list, db_path)
                    continue

            else:
                print('作業者の登録がありません')
        except ValueError:
            print('不正な入力です')


def main():
    """main画面設定
    """
    while True:
        os.system('cls')
        print('#'*20, 'MAIN MENU', '#'*20)
        print('\n')
        print('0 - Factoy 設定')
        print('1 - 生産計画リスト 設定')
        print('2 - 製品情報(Product) 設定')
        print('3 - 作業者情報(Worker) 設定')
        print('4 - 機械情報(Machine)設定')
        print('5 - Schedule 設定')
        print('6 - Task 設定 (未実装)')
        print('7 - 担当機械(charge list)設定')
        print('8 - random Event 設定(未実装)')

        print('\n')
        print('d - シミュレーター実行(描画あり)')
        print('s - シミュレーター実行(描画なし)')
        print('c- シミュレーター実行結果の検証')

        print('\n')
        print('o - 計画表出力')

        print('\n')
        print('m - 鋼材在庫管理')

        print('\n')
        print('exit() - 終了する')

        print('\n')
        print('#'*(20 + 10 + 2 + 20))
        print('\n')

        command_list = [
            '0', '1', '2', '3', '4', '5', '6', '7', '8',
            'd', 's', 'c', 'o', 'm', 'exit()'
        ]
        n_y_i = ['6', '8']
        command = input('SELECT EXECUTE No. ---')
        os.system('cls')
        if command in command_list:
            print('\n')
            print(f'selstced - "{command}"')
            if command == 'exit()':
                os.system('cls')
                print('program closed')
                break
            elif command in n_y_i:
                print('\n')
                print('not yet implemented')
                print('\n')
                continue
            elif command == '0':
                view_factory(db_path)
                print('\n')
                continue
            elif command == '1':
                view_planning(db_path)
                print('\n')
                continue
            elif command == '2':
                view_product(db_path)
                print('\n')
                continue
            elif command == '3':
                view_worker(db_path)
                print('\n')
                continue
            elif command == '4':
                view_machine(db_path)
                print('\n')
                continue
            elif command == '5':
                view_schedule(db_path)
                print('\n')
                continue
            elif command == '7':
                view_charge_list(db_path)
                print('\n')
                continue
            elif command == 'd':
                view_sim_with_draw()
                print('\n')
                continue
            elif command == 's':
                view_sim()
                print('\n')
                continue
            elif command == 'c':
                view_review()
                print('\n')
                continue
            elif command == 'o':
                view_save_plan_to_excel()
                print('\n')
                continue
            elif command == 'm':
                view_material(csv_path, material_path, db_path)
                print('\n')
                continue
        else:
            print('不正な入力です')
            print('\n')
            continue


if __name__ == '__main__':

    main()
