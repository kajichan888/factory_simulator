import sqlite3
import pandas as pd
import datetime
import openpyxl as xl


def query_production_table(product, db_path):
    """
    データベースから製品の加工情報を読み込み
    DataFrameに変換して返す
    product: 計画名 P1, P2等
    db_path: sqliteデータベースのファイルパス
    """
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT
            product.product_id,
            code,
            type,
            shank,
            length,
            process.process
        FROM
            product
        INNER JOIN
            process
        ON
        process.product_id=product.product_id
        WHERE
            product.code = ?
        """,
        (product,)
    )

    res = cursor.fetchall()

    with sqlite3.connect(db_path) as con:
        production_df = pd.read_sql(
            f"""
            SELECT
                product.product_id,
                machine.machine_id,
                machine.symbol,
                cycle_time,
                auto,
                repeat
            FROM
                production
            INNER JOIN
                product
            ON
                production.product_id = product.product_id
            INNER JOIN
                machine
            ON
                production.machine_id=machine.machine_id
            WHERE
            product.code = '{product}'
            """,
            con
        )

    merge_list = []
    for row in res:
        m = []
        for i in range(1, 5):
            m.append(row[i])
        if row[5]:
            machines = row[5].split(',')
            for machine_id in machines:
                _df = production_df[
                    production_df['machine_id'] == int(machine_id)
                ]
                df_list = _df.values.tolist()[0]
                for process in df_list[2:]:
                    m.append(process)
        merge_list.append(m)

    max_processes = ''
    for _products in merge_list:
        if len(_products) > len(max_processes):
            max_processes = _products
    columns = ['product', 'type', 'diameter', 'length']
    for i in range(1, int((len(max_processes) - 4) / 4 + 1)):
        columns.append(f'process-{i}')
        columns.append(f'time-{i}')
        columns.append(f'auto-{i}')
        columns.append(f'repeat-{i}')

    df = pd.DataFrame(merge_list, columns=tuple(columns))

    return df


def plan_production(product_dataframe, df_row_label, lot):
    """新規に計画を作成する
    product_dataframe: product情報のDataFrame
    df_row_label: 登録するproductのproduct_dataframeのインデックス番号
    """
    pr = pd.DataFrame(product_dataframe.iloc[df_row_label].dropna()).T
    pr.insert(1, 'lot', lot)
    return pr


def append_production(product_dataframe, df_row_label, lot, planed_products):
    """既存の計画に追加する
    product_dataframe: product情報のDataFrame
    df_row_label: 登録するproductのproduct_dataframeのインデックス番号
    lot: 加工数量
    planed_prpducts: 既存の計画のDataFrame
    """
    pr = plan_production(product_dataframe, df_row_label, lot)
    pr = pd.concat([planed_products, pr]).reset_index(drop=True)
    return pr


def read_schedule(worker_name, db_path):
    """
    データベース(db_path)から作業者のスケジュールを読み込み
    DataFrameにして返す
    worker_name: 作業者名
    db_path: データベースのファイルパス
    """
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(
            f"""
            SELECT
                task,
                week.eng,
                room.room_name,
                schedule.position_id,
                start,
                end
            FROM
                schedule
            INNER JOIN
                week
            ON schedule.week_id = week.week_id
            INNER JOIN
                room
            ON schedule.position_id = room.position_id
            INNER JOIN
                worker
            ON schedule.worker_id = worker.worker_id
            WHERE
                worker.name = '{worker_name}'
            """,
            con
        )
    return df


def read_charge_list(worker_name, db_path):
    """
    データベース(db_path)から作業者の担当機械のリストを読み込み返す
    """
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    cursor.execute(
        f"""
        SELECT
            worker.name,
            charge
        FROM
            charge
        INNER JOIN
            worker
        ON worker.worker_id = charge.worker_id
        WHERE
            worker.name = '{worker_name}'
        """)
    res = cursor.fetchone()

    with sqlite3.connect(db_path) as con:
        machine_df = pd.read_sql(
            """
            SELECT
                *
            FROM
                machine
            """,
            con
        )

    con.close()

    charge_list = []
    c = res[1].split(',')
    try:
        int_c = list(map(int, c))
        cs = pd.Series(int_c, name='machine_id')
        cs_ = pd.merge(cs, machine_df, on='machine_id')
        cs_sr = cs_['symbol']
        charge_list = cs_sr.values.tolist()
    except ValueError:
        pass
    return charge_list


def encode_symbols_to_machine_ids(symbols, db_path):
    """
    ','区切りで繋がっっている機械の文字列を
    データベースのmachine_idの文字列に変換する
    例 'M1,M2,M3' -> '1,2,3'

    """
    # データベース接続
    con = sqlite3.connect(db_path)
    if not symbols:
        return ''
    else:
        for machine in symbols:
            process = symbols.split(',')
            id_list = []
            for machine in process:
                res = con.cursor()
                res.execute(
                    """
                    SELECT
                        machine_id
                    FROM
                        machine
                    WHERE
                        symbol = ?
                    """,
                    (machine,)
                )
                machine_id = res.fetchone()
                if machine_id:
                    id_list.append(machine_id[0])
            if id_list:
                machine_ids = ','.join(map(str, id_list))
            else:
                machine_ids = ''
        con.close()
        return machine_ids


def encode_machine_ids_to_symbols(machine_ids, db_path):
    """
    ','区切りで繋がっっているデータベースのmachine_idの文字列を
    機械名の文字列に変換する
    例  '1,2,3' -> 'M1,M2,M3'

    """
    # データベース接続
    con = sqlite3.connect(db_path)
    if not machine_ids:
        return ''
    else:
        for machine in machine_ids:
            process = machine_ids.split(',')
            symbol_list = []
            for machine_id in process:
                res = con.cursor()
                res.execute(
                    """
                    SELECT
                        symbol
                    FROM
                        machine
                    WHERE
                        machine_id = ?
                    """,
                    (machine_id,)
                )
                symbol = res.fetchone()
                if symbol:
                    symbol_list.append(symbol[0])
            if symbol_list:
                symbols = ','.join(symbol_list)
            else:
                symbols = ''
        con.close()
        return symbols


def referene_product(db_path):
    """
    inputで問い合わせた製品の製品コードを返す

    db_path: データベースのパス
    """
    # 参照するproductionデータの呼び出し
    while True:
        reference_product = input('参照する製品コード')
        with sqlite3.connect(db_path) as con:
            df = pd.read_sql(
                f"""
                SELECT
                    product.code,
                    machine.symbol,
                    production.cycle_time,
                    production.auto,
                    production.repeat
                FROM
                    production
                INNER JOIN
                    product
                ON
                    production.product_id = product.product_id
                INNER JOIN
                    machine
                ON
                    production.machine_id = machine.machine_id
                WHERE
                    code = '{reference_product}'
                """,
                con
            )
        print(df)
        ask1 = input('他を読みますか? - [終了/n]')
        if ask1 == 'n':
            break

    return reference_product


def referene_production(db_path):
    """
    inputで問い合わせた製品の
    リスト[製品コード, 機械名, サイクルタイム, 連続運転回数, 工数]を返す

    db_path: データベースのパス
    """
    # 参照するproductionデータの呼び出し
    while True:
        reference_product = input('参照する製品コード')
        with sqlite3.connect(db_path) as con:
            df = pd.read_sql(
                f"""
                SELECT
                    product.code,
                    machine.symbol,
                    production.cycle_time,
                    production.auto,
                    production.repeat
                FROM
                    production
                INNER JOIN
                    product
                ON
                    production.product_id = product.product_id
                INNER JOIN
                    machine
                ON
                    production.machine_id = machine.machine_id
                WHERE
                    code = '{reference_product}'
                """,
                con
            )
        print(df)
        ask1 = input('他を読みますか? - [終了/n]')
        if ask1 == 'n':
            break
    if len(df):
        while True:
            ask2 = input('参照するproduction番号 - [終了/exit()]')
            if ask2 == 'exit()':
                break
            else:
                try:
                    if int(ask2) + 1 > len(df):
                        print('out of range')
                    else:
                        break
                except:
                    print('不正な入力です')
                    continue
        if ask2 != 'exit()':
            return df.values.tolist()[int(ask2)]


def update_product_to_db(db_path):
    """
    製品情報(製品名、径、全長等)を登録する
    processテーブルにはproduct_idだけ登録される

    reference_product: 参照する製品コード(引数とするとデフォルト値として入力を省略可)
    """
    # DataBase接続
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    # デフォルト値(refererence_product)の情報読み込み
    update_product = input('情報を更新する製品コードを入力 ---- ')
    cursor.execute(
        """
        SELECT
            product_id,
            code,
            type,
            diameter,
            shank,
            length,
            effective_length
        FROM
            product
        WHERE
            code = ?
        """,
        (update_product,)
    )
    res = cursor.fetchone()
    con.close()
    if res:
        print(f'製品名: {res[1]}')
        print(f'製品タイプ{res[2]}')
        print(f'製品径: {res[3]}')
        print(f'シャンク径: {res[4]}')
        print(f'全長: {res[5]}')
        print(f'有効長: {res[6]}')

        print('\n')
        print('='*10, '更新情報入力', '='*10)

        # 製品コード
        code = input(f'製品名 - [referece: {res[1]}]')
        if len(code) == 0:
            code = res[1]
        # 製品タイプ
        typ = input(f'Type - [referece: {res[2]}]')
        if len(typ) == 0:
            typ = res[2]

        # 製品径
        diameter = input(f'製品径 - [referece: {res[3]}]')
        if len(diameter) == 0:
            diameter = res[3]

        # シャンク径
        shank = input(f'シャンク径 - [referece: {res[4]}]')
        if len(shank) == 0:
            shank = res[4]

        # 全長
        length = input(f'全長 - [referece: {res[5]}]')
        if len(length) == 0:
            length = res[5]

        # 有効長
        effective_length = input(f'有効長 - [referece: {res[6]}]')
        if len(effective_length) == 0:
            effective_length = res[6]

        print('\n')
        print('==== 更新前情報 ====')
        print(f'製品名: {res[1]}')
        print(f'製品タイプ{res[2]}')
        print(f'製品径: {res[3]}')
        print(f'シャンク径: {res[4]}')
        print(f'全長: {res[5]}')
        print(f'有効長: {res[6]}')
        print('\n')

        print('==== 更新後情報 ====')
        print
        print('\n')
        print('*'*20)
        print(f'製品名: {code}')
        print(f'Type: {typ}')
        print(f'製品径: {diameter}')
        print(f'シャンク径: {shank}')
        print(f'全長: {length}')
        print(f'有効長: {effective_length}')
        print('*'*20)
        print('\n')

        conf = ''
        while True:
            conf = input('更新しますか？ Yes: y No: n - ')
            if conf == 'y' or conf == 'n':
                break
            else:
                print('\n')
                print('input y or n')
                print('\n')
                continue
        if conf == 'y':
            sql = f"""
                UPDATE
                    product
                SET
                    code = '{code}', 
                    type = '{typ}', 
                    diameter = '{diameter}',
                    shank = '{shank}',
                    length = '{length}',
                    effective_length = '{effective_length}'
                WHERE
                    product_id = '{res[0]}'
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
    else:
        print('不正な入力です')

def insert_product_to_db(db_path):
    """
    製品情報(製品名、径、全長等)を登録する
    processテーブルにはproduct_idだけ登録される

    reference_product: 参照する製品コード(引数とするとデフォルト値として入力を省略可)
    """
    # DataBase接続
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    # デフォルト値(refererence_product)の情報読み込み
    reference_product = referene_product(db_path)
    cursor.execute(
        """
        SELECT
            product_id,
            code,
            type,
            diameter,
            shank,
            length,
            effective_length
        FROM
            product
        WHERE
            code = ?
        """,
        (reference_product,)
    )
    res = cursor.fetchone()
    if res:
        print(f'製品名: {res[1]}')
        print(f'製品タイプ{res[2]}')
        print(f'製品径: {res[3]}')
        print(f'シャンク径: {res[4]}')
        print(f'全長: {res[5]}')
        print(f'有効長: {res[6]}')

    # 製品コード
    print('\n')
    print('='*10, '新規登録情報入力', '='*10)
    code = input('製品名')

    # 製品タイプ
    while True:
        if res:
            typ = input(f'Type - [referece: {res[2]}]')
            if len(typ) == 0:
                typ = res[2]
            break
        else:
            typ = input('Type - ')
            break

    # 製品径
    if res:
        while True:
            diameter = input(f'製品径 - [referece: {res[3]}]')
            if len(diameter) == 0:
                diameter = res[3]
                break
            else:
                try:
                    diameter = float(diameter)
                    break
                except ValueError:
                    print('不正な入力です')
    else:
        while True:
            diameter = input('製品径 - ')
            if len(diameter) == 0:
                diameter = ''
                break
            else:
                try:
                    diameter = float(diameter)
                    break
                except ValueError:
                    print('不正な入力です')

    # シャンク径
    if res:
        while True:
            shank = input(f'シャンク径 - [referece: {res[4]}]')
            if len(shank) == 0:
                shank = res[4]
                break
            else:
                try:
                    shank = float(shank)
                    break
                except ValueError:
                    print('不正な入力です')
    else:
        while True:
            shank = input('シャンク径 - ')
            if len(shank) == 0:
                shank = ''
                break
            else:
                try:
                    shank = float(shank)
                    break
                except ValueError:
                    print('不正な入力です')

    # 全長
    if res:
        while True:
            length = input(f'全長 - [referece: {res[5]}]')
            if len(length) == 0:
                length = res[5]
                break
            else:
                try:
                    length = float(length)
                    break
                except ValueError:
                    print('不正な入力です')
    else:
        while True:
            length = input('全長 - ')
            if len(length) == 0:
                length = ''
                break
            else:
                try:
                    length = float(length)
                    break
                except ValueError:
                    print('不正な入力です')

    # 有効長
    if res:
        while True:
            effective_length = input(f'有効長 - [referece: {res[6]}]')
            if len(effective_length) == 0:
                effective_length = res[6]
                break
            else:
                try:
                    effective_length = float(effective_length)
                    break
                except ValueError:
                    print('不正な入力です')
    else:
        while True:
            effective_length = input('有効長 - ')
            if len(effective_length) == 0:
                effective_length = ''
                break
            else:
                try:
                    effective_length = float(effective_length)
                    break
                except ValueError:
                    print('不正な入力です')

    print('\n')
    print('*'*20)
    print(f'製品名: {code}')
    print(f'Type: {typ}')
    print(f'製品径: {diameter}')
    print(f'シャンク径: {shank}')
    print(f'全長: {length}')
    print(f'有効長: {effective_length}')
    print('*'*20)
    print('\n')

    conf = ''
    while True:
        conf = input('登録しますか？ Yes: y No: n - ')
        if conf == 'y' or conf == 'n':
            break
        else:
            print('\n')
            print('input y or n')
            print('\n')
            continue
    if conf == 'y':
        cursor.execute(
            f"""
            INSERT INTO
                product(code, type, diameter, shank, length, effective_length)
            VALUES
                ('{code}', '{typ}', '{diameter}', '{shank}', '{length}', '{effective_length}')
            """
        )
        con.commit()
        cursor.execute(
            f"""
            SELECT
                product_id
            FROM
                product
            WHERE
                code = '{code}'
            """
        )
        product_id = cursor.fetchone()
        cursor.execute(
            f"""
            INSERT INTO
                process(product_id, process)
            VALUES
                ('{product_id[0]}', '')
            """
        )
        con.commit()

    con.close()
    if conf == 'y':
        return code
    else:
        return None


def update_process_to_db(product, db_path):
    """processテーブルを更新する

    product: 更新する製品コード
    db_path: データベースのパス
    """
    # DataBase接続
    con = sqlite3.connect(db_path)
    # 更新するprocessの選択
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT
            process.product_id,
            product.code,
            process
        FROM
            process
        INNER JOIN
            product
        ON process.product_id = product.product_id
        WHERE
            product.code = ?
        """,
        (product,)
    )
    res = cursor.fetchall()

    process_list = []
    if res:
        for tpl in res:
            l = []
            l.append(tpl[0])
            l.append(tpl[1])
            symbols = encode_machine_ids_to_symbols(tpl[2], db_path)
            l.append(symbols)
            process_list.append(l)
    df = pd.DataFrame(process_list, columns=('id', 'code', 'process'))
    print(df)
    print('\n')
    while True:
        n = input('更新するprocess No.')
        try:
            if int(n) not in [i for i in range(len(df))]:
                print('process Noがありません')
            else:
                break
        except ValueError:
            print('不正な入力です')
            continue
    update_product = product
    update_product_id = df.loc[int(n), 'id']
    pre_update_symbols = df.loc[int(n), 'process']
    pre_update_process = encode_symbols_to_machine_ids(pre_update_symbols, db_path)

    # デフォルト値(refererence_product)の情報読み込み
    reference_product = referene_product(db_path)
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT
            process.product_id,
            product.code,
            process
        FROM
            process
        INNER JOIN
            product
        ON process.product_id = product.product_id
        WHERE
            product.code = ?
        """,
        (reference_product,)
    )
    r_res = cursor.fetchall()

    ref_process_list = []
    if r_res:
        for tpl in r_res:
            l = []
            l.append(tpl[1])
            symbols = encode_machine_ids_to_symbols(tpl[2], db_path)
            l.append(symbols)
            ref_process_list.append(l)
    # print(f'r_res: {r_res}, \nref_machine_list: {ref_process_list}')
    ref_df = pd.DataFrame(ref_process_list, columns=('code', 'process'))
    print('参照データ')
    print(ref_df)
    print('\n')

    # 登録機械のprocess作成
    cursor = con.cursor()
    while True:
        n = input('参照するprocess No.')
        # if int(n) + 1 > len(ref_df):
        try:
            if int(n) not in [i for i in range(len(ref_df))]:
                print('process Noがありません')
            else:
                break
        except ValueError:
            print('不正な入力です')
            continue
    ref_machine_list = ref_df.loc[int(n), 'process'].split(',')

    machine_list = []
    symbol_list = []
    while True:
        if ref_machine_list:
            ref_machine_name = ref_machine_list.pop(0)
        else:
            ref_machine_name = None
        while True:
            if ref_machine_name:
                machine = input(f'機械名 - [referece: {ref_machine_name}]')
                if len(machine) == 0:
                    machine = ref_machine_name
            else:
                machine = input(f'機械名 - ')
            cursor = con.cursor()
            cursor.execute(
                f"""
                SELECT
                    machine_id
                FROM
                    machine
                WHERE
                    symbol = '{machine}'
                """
            )
            machine_id = cursor.fetchone()
            if machine_id:
                break
            else:
                print('その機械は登録されていません')
        machine_list.append(machine_id[0])
        symbol_list.append(machine)
        q = input('続けて登録しますか？ [終了/n]')
        if q == 'n':
            break

    machine_ids = ','.join(map(str, machine_list))
    symbols = ','.join(symbol_list)
    # print(machine_ids)
    # print(symbols)

    # 登録する
    print('\n')
    print('更新前')
    print('*'*20)
    print(f'product_id: {update_product_id}')
    print(f'製品名: {update_product}')
    print(f'process: {pre_update_symbols}')
    print('*'*20)
    print('\n')

    print('更新後')
    print('*'*20)
    print(f'product_id: {update_product_id}')
    print(f'製品名: {update_product}')
    print(f'process: {symbols}')
    print('*'*20)

    conf = ''
    while True:
        conf = input('登録しますか？ Yes: y No: n')
        if conf == 'y' or conf == 'n':
            break
        else:
            print('\n')
            print('input y or n')
            print('\n')
            continue
    if conf == 'y':
        process = machine_ids
        print('\n')
        print(update_product_id, pre_update_process)
        print(update_product_id, process)
        print('\n')

        # UPDATEのSQL
        update_process_sql = f"""
            UPDATE
                process
            SET
                product_id = '{update_product_id}',
                process = '{process}'
            WHERE
                product_id = '{update_product_id}'
                AND
                process = '{pre_update_process}'
            """
        cursor = con.cursor()
        cursor.execute(update_process_sql)
        # print(update_process_sql)

        # 未登録のproductionデータの抽出
        check_list = []
        while True:
            process_list = process.split(',')
            if set(process_list) == set(check_list):
                break
            else:
                for machine_id in process_list:
                    cursor = con.cursor()
                    cursor.execute(
                        f"""
                        SELECT
                            product_id,
                            machine_id
                        FROM
                            production
                        WHERE
                            product_id = '{update_product_id}'
                            AND
                            machine_id = '{machine_id}'
                        """
                    )
                    res = cursor.fetchone()
                    # productionデータの登録(未登録の場合)
                    if not res:
                        product_sql = f"SELECT code FROM product WHERE product_id = '{update_product_id}'"
                        machine_sql = f"SELECT symbol FROM machine WHERE machine_id = '{machine_id}'"
                        print(f'新規登録 - product_id: {update_product_id}, machine_id: {machine_id}')
                        cursor = con.cursor()
                        cursor.execute(product_sql)
                        product_code = cursor.fetchone()[0]
                        cursor = con.cursor()
                        cursor.execute(machine_sql)
                        machine_symbol = cursor.fetchone()[0]
                        print('\n')
                        print(product_code)
                        print(machine_symbol)
                        print('\n')

                        print('参照するproduct code')
                        print('\n')

                        # utils.db_utils.reference_production呼び出し
                        # [製品コード, 機械名, サイクルタイム, 連続運転回数, 工数]
                        lst = referene_production(db_path)
                        while True:
                            if lst:
                                cycle_time = input(f'サイクルタイム(分) - [reference: {lst[2]}]')
                                if len(cycle_time) == 0:
                                    cycle_time = lst[2]
                                auto = input(f'連続運転(回) - [reference: {lst[3]}]')
                                if len(auto) == 0:
                                    auto = lst[3]
                                repeat = input(f'工数(回) - [reference: {lst[4]}]')
                                if len(repeat) == 0:
                                    repeat = lst[4]
                            else:
                                cycle_time = input('サイクルタイム(分)')
                                auto = input('連続運転(回)')
                                repeat = input('工数(回)')
                            try:
                                cycle_time = int(cycle_time)
                                auto = int(auto)
                                repeat = int(repeat)
                                break
                            except ValueError:
                                print('不正な入力です')
                                continue

                        print('\n')
                        print('*'*20)
                        print(f'製品名: {product_code}')
                        print(f'機械名: {machine_symbol}')
                        print(f'サイクルタイム: {cycle_time}')
                        print(f'自動運転回数: {auto}')
                        print(f'工数: {repeat}')
                        print('*'*20)
                        print('\n')

                        conf = input('登録しますか？ - [Yes/y]')
                        print('\n')
                        if conf == 'y':
                            # INSERTのSQL
                            insert_production_sql = f"""
                                INSERT INTO
                                    production(product_id, machine_id, cycle_time, auto, repeat)
                                VALUES
                                    ('{update_product_id}', '{machine_id}', '{cycle_time}', '{auto}', '{repeat}')
                                """
                            # print(insert_production_sql)
                            cursor = con.cursor()
                            cursor.execute(insert_production_sql)
                            check_list.append(machine_id)
                            print('\n')
                        else:
                            print('====登録とりやめ====')
                    else:
                        check_list.append(machine_id)

    con.commit()
    con.close()
    print('====登録完了====')


def insert_process_to_db(product, db_path):
    """processテーブルにデータを追加する

    product: 追加更新する製品コード
    db_path: データベースのパス
    """
    # DataBase接続
    con = sqlite3.connect(db_path)
    # processを追加するproductの選択
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT
            process.product_id,
            product.code,
            process
        FROM
            process
        INNER JOIN
            product
        ON process.product_id = product.product_id
        WHERE
            product.code = ?
        """,
        (product,)
    )
    res = cursor.fetchall()

    process_list = []
    if res:
        for tpl in res:
            l = []
            l.append(tpl[0])
            l.append(tpl[1])
            symbols = encode_machine_ids_to_symbols(tpl[2], db_path)
            l.append(symbols)
            process_list.append(l)
    df = pd.DataFrame(process_list, columns=('id', 'code', 'process'))
    print(df)
    print('\n')
    # while True:
    #    n = input('更新するprocess No.')
        # print(f'product: {product}')
        # print(df.loc[int(n), 'process'])
        # print(df.loc[int(n), 'id']) # product_id
        # process
        # print(encode_symbols_to_machine_ids(df.loc[int(n), 'process'], db_path))
    #    if int(n) + 1 > len(df):
    #        print('process Noがありません')
    #    else:
    #        break
    insert_process_product = product
    insert_product_id = df.loc[0, 'id']
    # pre_update_symbols = df.loc[int(n), 'process']
    # pre_update_process = encode_symbols_to_machine_ids(pre_update_symbols, db_path)

    # デフォルト値(refererence_product)の情報読み込み
    reference_product = referene_product(db_path)
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT
            process.product_id,
            product.code,
            process
        FROM
            process
        INNER JOIN
            product
        ON process.product_id = product.product_id
        WHERE
            product.code = ?
        """,
        (reference_product,)
    )
    r_res = cursor.fetchall()

    ref_process_list = []
    if r_res:
        for tpl in r_res:
            l = []
            l.append(tpl[1])
            symbols = encode_machine_ids_to_symbols(tpl[2], db_path)
            l.append(symbols)
            ref_process_list.append(l)
    # print(f'r_res: {r_res}, \nref_machine_list: {ref_process_list}')
    ref_df = pd.DataFrame(ref_process_list, columns=('code', 'process'))
    print('参照データ')
    print(ref_df)
    print('\n')

    # 登録機械のprocess作成
    cursor = con.cursor()
    if len(ref_df) >= 1:
        while True:
            n = input('参照するprocess No.')
            # if int(n) + 1 > len(ref_df):
            try:
                if int(n) not in [i for i in range(len(ref_df))]:
                    print('process Noがありません')
                else:
                    break
            except ValueError:
                print('不正な入力です')
                continue
        ref_machine_list = ref_df.loc[int(n), 'process'].split(',')
    else:
        ref_machine_list = None

    machine_list = []
    symbol_list = []
    while True:
        if ref_machine_list:
            ref_machine_name = ref_machine_list.pop(0)
        else:
            ref_machine_name = None
        while True:
            if ref_machine_name:
                machine = input(f'機械名 - [referece: {ref_machine_name}]')
                if len(machine) == 0:
                    machine = ref_machine_name
            else:
                machine = input(f'機械名 - ')
            cursor = con.cursor()
            cursor.execute(
                f"""
                SELECT
                    machine_id
                FROM
                    machine
                WHERE
                    symbol = '{machine}'
                """
            )
            machine_id = cursor.fetchone()
            if machine_id:
                break
            else:
                print('その機械は登録されていません')
        machine_list.append(machine_id[0])
        symbol_list.append(machine)
        q = input('続けて登録しますか？ [終了/n]')
        if q == 'n':
            break

    machine_ids = ','.join(map(str, machine_list))
    symbols = ','.join(symbol_list)
    # print(machine_ids)
    # print(symbols)

    # 登録する
    print('\n')
    print('登録プロセス')
    print('*'*20)
    print(f'product_id: {insert_product_id}')
    print(f'製品名: {insert_process_product}')
    print(f'process: {symbols}')
    print('*'*20)

    conf = ''
    while True:
        conf = input('登録しますか？ Yes: y No: n')
        if conf == 'y' or conf == 'n':
            break
        else:
            print('\n')
            print('input y or n')
            print('\n')
            continue
    if conf == 'y':
        process = machine_ids
        print('\n')
        # print(insert_process_product, pre_update_process)
        print(insert_process_product, process)

        # UPDATEのSQL
        insert_process_sql = f"""
            INSERT INTO
                process(product_id, process)
            VALUES
                ('{insert_product_id}', '{process}')
            """
        cursor = con.cursor()
        cursor.execute(insert_process_sql)
        # print(insert_process_sql)

        # 未登録のproductionデータの抽出
        check_list = []
        while True:
            process_list = process.split(',')
            if set(process_list) == set(check_list):
                break
            else:
                for machine_id in process_list:
                    cursor = con.cursor()
                    cursor.execute(
                        f"""
                        SELECT
                            product_id,
                            machine_id
                        FROM
                            production
                        WHERE
                            product_id = '{insert_product_id}'
                            AND
                            machine_id = '{machine_id}'
                        """
                    )
                    res = cursor.fetchone()

                    # productionデータの登録(未登録の場合)
                    if not res:
                        product_sql = f"SELECT code FROM product WHERE product_id = '{insert_product_id}'"
                        machine_sql = f"SELECT symbol FROM machine WHERE machine_id = '{machine_id}'"
                        print(f'新規登録 - product_id: {insert_product_id}, machine_id: {machine_id}')
                        cursor = con.cursor()
                        cursor.execute(product_sql)
                        product_code = cursor.fetchone()[0]
                        cursor = con.cursor()
                        cursor.execute(machine_sql)
                        machine_symbol = cursor.fetchone()[0]
                        print('\n')
                        print(product_code)
                        print(machine_symbol)
                        print('\n')

                        print('参照するproduct code')
                        print('\n')

                        # utils.db_utils.reference_production呼び出し
                        # [製品コード, 機械名, サイクルタイム, 連続運転回数, 工数]
                        lst = referene_production(db_path)
                        while True:
                            if lst:
                                cycle_time = input(f'サイクルタイム(分) - [reference: {lst[2]}]')
                                if len(cycle_time) == 0:
                                        cycle_time = lst[2]
                                auto = input(f'連続運転(回) - [reference: {lst[3]}]')
                                if len(auto) == 0:
                                        auto = lst[3]
                                repeat = input(f'工数(回) - [reference: {lst[4]}]')
                                if len(repeat) == 0:
                                        repeat = lst[4]
                            else:
                                cycle_time = input('サイクルタイム(分)')
                                auto = input('連続運転(回)')
                                repeat = input('工数(回)')
                            try:
                                cycle_time = int(cycle_time)
                                auto = int(auto)
                                repeat = int(repeat)
                                break
                            except ValueError:
                                print('不正な入力です')
                                continue
                        
                        print('\n')
                        print('*'*20)
                        print(f'製品名: {product_code}')
                        print(f'機械名: {machine_symbol}')
                        print(f'サイクルタイム: {cycle_time}')
                        print(f'自動運転回数: {auto}')
                        print(f'工数: {repeat}')
                        print('*'*20)
                        print('\n')

                        conf = input('登録しますか？ - [Yes/y]')
                        print('\n')
                        if conf == 'y':
                            # INSERTのSQL
                            insert_production_sql = f"""
                                INSERT INTO
                                    production(product_id, machine_id, cycle_time, auto, repeat)
                                VALUES
                                    ('{insert_product_id}', '{machine_id}', '{cycle_time}', '{auto}', '{repeat}')
                                """
                            # print(insert_production_sql)
                            cursor = con.cursor()
                            cursor.execute(insert_production_sql)
                            check_list.append(machine_id)
                            print('\n')
                        else:
                            print('====登録とりやめ====')
                    else:
                        check_list.append(machine_id)

    con.commit()
    con.close()
    print('====登録完了====')


def delete_process_from_db(product, db_path):
    """データベースからprocessを削除する

    product: processを削除するproduct名 例'P1'. 'P2'
    db_path: データベースのpath
    """
    # DataBase接続
    con = sqlite3.connect(db_path)
    # processを追加するproductの選択
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT
            process.product_id,
            product.code,
            process
        FROM
            process
        INNER JOIN
            product
        ON process.product_id = product.product_id
        WHERE
            product.code = ?
        """,
        (product,)
    )
    res = cursor.fetchall()

    process_list = []
    if res:
        for tpl in res:
            l = []
            l.append(tpl[0])
            l.append(tpl[1])
            symbols = encode_machine_ids_to_symbols(tpl[2], db_path)
            l.append(symbols)
            process_list.append(l)
    df = pd.DataFrame(process_list, columns=('id', 'code', 'process'))
    print(df)
    print('\n')
    while True:
        n = input('削除するprocess No.')
        # print(f'product: {product}')
        # print(df.loc[int(n), 'process'])
        # print(df.loc[int(n), 'id']) # product_id
        # process
        # print(encode_symbols_to_machine_ids(df.loc[int(n), 'process'], db_path))
        if int(n) + 1 > len(df):
            print('process Noがありません')
        else:
            break
    delete_process_product = product
    delete_product_id = df.loc[0, 'id']
    pre_update_symbols = df.loc[int(n), 'process']
    pre_update_process = encode_symbols_to_machine_ids(pre_update_symbols, db_path)

    # print(f'delete_process_product: {delete_process_product}')
    # print(f'delete_product_id: {delete_product_id}')
    # print(f'pre_update_symbols: {pre_update_symbols}')
    # print(f'pre_update_process: {pre_update_process}')
    print('\n')
    print('削除するprocessデータ')
    print('*'*20)
    print(f'製品名: {delete_process_product}')
    print(f'process: {pre_update_symbols}')
    print('*'*20)
    print('\n')

    conf = ''
    while True:
        conf = input('削除しますか？ Yes: y No: n')
        if conf == 'y' or conf == 'n':
            break
        else:
            print('\n')
            print('input y or n')
            print('\n')
            continue
    if conf == 'y':
        if len(df) >= 2:
            # DELETEのSQL
            sql = f"""
                DELETE
                FROM
                    process
                WHERE
                    product_id = '{delete_product_id}'
                    AND
                    process = '{pre_update_process}'
                """
        else:
            # UPDATEのSQL
            sql = f"""
                UPDATE process
                SET
                    process = ''
                WHERE
                    product_id = '{delete_product_id}'
                    AND
                    process = '{pre_update_process}'
                """
        cursor = con.cursor()
        cursor.execute(sql)
        # print(delete_process_sql)
        print('====削除完了====')

    con.commit()
    con.close()


def update_production_to_db(product, machine_symbol, db_path):
    """データベースのproductionテーブルを更新する

    product: productionを更新するproduct名 例) 'P1'. 'P2'
    machine_symbol: processの機械名 例) 'NL', 'H1'
    db_path: データベースのpath
    """
    # 編集するproductionデータの抽出
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    try:
        cursor.execute(
            f"""
            SELECT
                production.product_id,
                product.code,
                machine.machine_id,
                machine.symbol,
                production.cycle_time,
                production.auto,
                production.repeat
            FROM
                production
            INNER JOIN
                product
            ON
                production.product_id = product.product_id
            INNER JOIN
                machine
            ON
                machine.machine_id = production.machine_id
            WHERE
                product.code = '{product}'
                AND
                machine.symbol = '{machine_symbol}'
            """
        )
        res = cursor.fetchone()

        df = pd.DataFrame(
            [[res[1], res[3], res[4], res[5], res[6]]],
            columns=('code', 'symbol', 'cycle_time', 'auto', 'repeat')
        )
        print(df)
        

        # print(res)
        # print(f'production_id: {res[0]}')
        # print(f'code: {res[1]}')
        # print(f'machine_id: {res[2]}')
        # print(f'symbol: {res[3]}')
        # print(f'cycle_time: {res[4]}')
        # print(f'auto: {res[5]}')
        # print(f'repeat: {res[6]}')

        cycle_time = input(f'サイクルタイム(分) - [reference: {res[4]}]')
        if len(cycle_time) == 0:
            cycle_time = res[4]
        auto = input(f'連続運転(回) - [reference: {res[5]}]')
        if len(auto) == 0:
            auto = res[5]
        repeat = input(f'工数(回) - [reference: {res[6]}]')
        if len(repeat) == 0:
            repeat = res[6]

        print('\n')
        print('更新するproductionデータ')
        print('*'*20)
        print(f'code: {res[1]}')
        print(f'symbol: {res[3]}')
        print(f'cycle_time: {res[4]}')
        print(f'auto: {res[5]}')
        print(f'repeat: {res[6]}')
        print('*'*20)
        print('\n')
        print('更新後のpductionデータ')
        print('*'*20)
        print(f'code: {res[1]}')
        print(f'symbol: {res[3]}')
        print(f'cycle_time: {cycle_time}')
        print(f'auto: {auto}')
        print(f'repeat: {repeat}')
        print('*'*20)

        conf = ''
        while True:
            conf = input('登録しますか？ Yes: y No: n')
            if conf == 'y' or conf == 'n':
                break
            else:
                print('\n')
                print('input y or n')
                print('\n')
                continue

        if conf == 'y':
            update_production_sql = f"""
                UPDATE
                    production
                SET
                    cycle_time = '{cycle_time}',
                    auto = '{auto}',
                    repeat = '{repeat}'
                WHERE
                    product_id = '{res[0]}'
                    AND
                    machine_id = '{res[2]}'
                """
            # print(update_production_sql)
            cursor = con.cursor()
            cursor.execute(update_production_sql)
    except TypeError:
        print('TypeError')
        pass
    
    con.commit()
    con.close()


def delete_product_from_db(product_code, db_path):
    """
    データベースのproduct, process, productionテーブルから
    product_codeのデータを一括削除する

    product_code: prduct code 例) 'P1', 'P2'
    db_path: データベースのパス
    """
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    cursor.execute(
        f"""
        SELECT
            product_id
        FROM
            product
        WHERE
            code = '{product_code}'
        """
    )
    res = cursor.fetchone()
    product_id = res[0]

    delete_process_sql = f"""
        DELETE FROM process WHERE product_id = '{product_id}
        '"""
    delete_production_sql = f"""
        DELETE FROM production WHERE product_id = '{product_id}
        '"""
    delete_product_sql = f"""
        DELETE FROM product WHERE product_id = '{product_id}
        '"""

    cursor = con.cursor()
    cursor.execute(delete_process_sql)

    cursor = con.cursor()
    cursor.execute(delete_production_sql)

    cursor = con.cursor()
    cursor.execute(delete_product_sql)

    con.commit()
    con.close()
    print('====削除完了====')


def display_new_material_list(db_path):
    """
    最新の鋼材データの一覧を表示する

    db_path: データベースのパス
    """
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(
            """
            SELECT
                material,
                status,
                diameter,
                length,
                history_material.quantity,
                MAX(history_material.date) as 'last undate'
            FROM
                material
            INNER JOIN
                history_material
            ON
                material.material_id = history_material.material_id
            GROUP BY
                material.material_id
            ORDER BY
                diameter
            """, con
        )
    print(df)


def export_material_list(file_path, db_path):
    """
    最新の鋼材データの一覧をexcel形式のファイルに出力する

    db_path: データベースのパス
    file_path: 出力するファイルのpath
    """
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(
            """
            SELECT
                material,
                status,
                diameter,
                length,
                history_material.quantity,
                history_material.note,
                MAX(history_material.date) as 'last undate'
            FROM
                material
            INNER JOIN
                history_material
            ON
                material.material_id = history_material.material_id
            GROUP BY
                material.material_id
            ORDER BY
                diameter
            """, con
        )
    # print(df)
    df.to_excel(file_path, index=False)


def display_past_material_list(db_path):
    """
    過去の鋼材データの一覧を表示する

    date: 表示するデータの最後の日付
    db_path: データベースのパス
    """
    y = input('西暦')
    m = input('月')
    d = input('日')
    date = datetime.datetime(int(y), int(m), int(d))
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(
            f"""
            SELECT
                material,
                status,
                diameter,
                length,
                history_material.quantity,
                MAX(history_material.date) as 'last update'
            FROM
                material
            INNER JOIN
                history_material
            ON
                material.material_id = history_material.material_id
            WHERE
                history_material.date < '{date}'
            GROUP BY
                material.material_id
            ORDER BY
                diameter
            """, con
        )
    print(df)


def display_history_material_data(db_path):
    """
    鋼材の入出庫の履歴を表示する

    diameter: 履歴を表示する鋼材の径
    db_path: データベースのパス
    """
    diameter = input('径を入力')
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(
            f"""
            SELECT
                material,
                status,
                diameter,
                length,
                history_material.quantity,
                history_material.note,
                history_material.date as 'last update'
            FROM
                material
            INNER JOIN
                history_material
            ON
                material.material_id = history_material.material_id
            WHERE
                material.diameter = '{diameter}'
            ORDER BY
                history_material.date DESC
            """, con
        )
    print(df)


def display_material_quantity(db_path):
    """
    最新の鋼材データを表示する

    db_path: データベースのパス
    """
    diameter = input('径を入力')
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(
            f"""
            SELECT
                material,
                status,
                diameter,
                length,
                history_material.quantity,
                MAX(history_material.date) as 'last undate'
            FROM
                material
            INNER JOIN
                history_material
            ON
                material.material_id = history_material.material_id
            WHERE
                diameter = '{diameter}'
            GROUP BY
                material.material_id
            """, con
        )
    print(df)


def return_material_dataframe(db_path):
    """
    最新の鋼材データを返す

    db_path: データベースのパス
    """
    diameter = input('径を入力 ----')
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(
            f"""
            SELECT
                material.material_id,
                material,
                status,
                diameter,
                length,
                history_material.quantity,
                MAX(history_material.date) as 'last update'
            FROM
                material
            INNER JOIN
                history_material
            ON
                material.material_id = history_material.material_id
            WHERE
                diameter = '{diameter}'
            GROUP BY
                material.material_id
            """, con
        )
    return df


def insert_new_material_data(db_path):
    """
    鋼材データを新規登録する

    db_path: データベースのパス
    """
    while True:
        print('参考データの表示')
        r_df = return_material_dataframe(db_path)
        r_dff = r_df[['material', 'status', 'diameter', 'length', 'quantity']]
        print(r_dff)
        number = input('select No.')
        try:
            ref_material_id = r_df.iloc[int(number)]['material_id']
            ref_material = r_df.iloc[int(number)]['material']
            ref_status = r_df.iloc[int(number)]['status']
            ref_diameter = r_df.iloc[int(number)]['diameter']
            ref_length = r_df.iloc[int(number)]['length']

            print('新規登録データの入力')
            material = input(f'材質 - [refernce/{ref_material}]')
            if len(material) == 0:
                material = ref_material
            status = input(f'状態 - [refernce/{ref_status}]')
            if len(status) == 0:
                status = ref_status
            diameter = input(f'径 - [refernce/{ref_diameter}]')
            if len(diameter) == 0:
                diameter = ref_diameter
            length = input(f'長さ - [refernce/{ref_length}]')
            if len(length) == 0:
                length = ref_length

            print('\n')
            print('*'*20)
            print(f'材質: {material}')
            print(f'状態: {status}')
            print(f'径: {diameter}')
            print(f'長さ: {length}')
            print('*'*20)

            conf = input('登録しますか？ - [yes: y]')
            if conf == 'y':
                sql = f"""
                    INSERT INTO material(
                        material,
                        status,
                        diameter,
                        length
                    )
                    VALUES
                        ('{material}', '{status}', '{diameter}', '{length}')
                """
                con = sqlite3.connect(db_path)
                cursor = con.cursor()
                cursor.execute(sql)
                con.commit()
                sql_new_data = f"""
                    SELECT
                        material_id
                    FROM
                        material
                    WHERE
                        material = '{material}'
                        AND
                        status = '{status}'
                        AND
                        diameter = '{diameter}'
                        AND
                        length = '{length}'
                """
                cursor = con.cursor()
                cursor.execute(sql_new_data)
                material_id = cursor.fetchone()[0]
                sql_h = f"""
                    INSERT INTO history_material(
                        material_id,
                        note,
                        date
                        )
                    VALUES
                        ('{material_id}', '新規登録', '{datetime.datetime.now()}')
                """
                cursor = con.cursor()
                cursor.execute(sql_h)
                con.commit()
                con.close()
                print('=== 登録完了 ===')
                break
            else:
                q = input('登録を中止しますか？ - [yes: y]')
                if q == 'y':
                    break
        except:
            print('不正な値です')
            continue


def update_material_data(db_path):
    """
    鋼材の入出庫データを登録する

    db_path: データベースのパス
    """
    while True:
        df = return_material_dataframe(db_path)
        dff = df[['material', 'status', 'diameter', 'length', 'quantity']]
        print(dff)
        number = input('select No. (新規登録: [enter/new])')
        if number == 'new':
            insert_new_material_data(db_path)
            continue
        else:
            try:
                material_id = df.iloc[int(number)]['material_id']
                diameter = df.iloc[int(number)]['diameter']
                quantity = df.iloc[int(number)]['quantity']
                if not quantity:
                    quantity = 0
                # print(material_id)
                # print(f'数量{quantity}')
                break
            except:
                print('不正な値です')
                continue

    print('日付を入力')
    while True:
        n = input('1: 現在の日時を使用  2: 日付を指定')
        if n == '1':
            date = datetime.datetime.now()
            break
        elif n == '2':
            y = input(f'日付を入力\n西暦: - [toray/{datetime.datetime.now().year}]')
            m = input(f'月: - [today/{datetime.datetime.now().month}]')
            d = input(f'日: - [today/{datetime.datetime.now().day}]')
            try:
                date = datetime.datetime(int(y), int(m), int(d)).date()
                break
            except:
                print('不正な日付です')
                continue
        else:
            print('input 1 or 2')

    i_d = input('増減を入力')
    note = input('注記事項')

    print('\n')
    print('*'*20)
    print(f'材質: {df.iloc[int(number)]["material"]}')
    print(f'状態: {df.iloc[int(number)]["status"]}')
    print(f'径: {diameter}')
    print(f'長さ: {df.iloc[int(number)]["length"]}')
    print(f'数量: {quantity + int(i_d)}')
    print(f'注記事項: {note}')
    print(f'日付: {date}')
    print('*'*20)
    while True:
        conf = input('登録しますか？ - [yes: y]')
        if conf == 'y':
            sql = f"""
                INSERT INTO history_material(
                    material_id,
                    quantity,
                    note,
                    date
                    )
                VALUES
                    ('{material_id}', '{quantity + int(i_d)}', '{note}', '{date}')
            """
            con = sqlite3.connect(db_path)
            cursor = con.cursor()
            cursor.execute(sql)
            con.commit()
            con.close()
            print('=== 登録完了 ===')
            break
        else:
            q = input('登録を中止しますか？ - [yes: y]')
            if q == 'y':
                break
            else:
                continue


def revise_material_data(db_path):
    """
    鋼材データを修正する

    db_path: データベースのパス
    """
    while True:
        print('登録データの表示')
        pre_df = return_material_dataframe(db_path)
        pre_dff = pre_df[
            ['material', 'status', 'diameter', 'length', 'quantity']
        ]
        print(pre_dff)
        number = input('select No.')
        try:
            pre_material_id = pre_df.iloc[int(number)]['material_id']
            pre_material = pre_df.iloc[int(number)]['material']
            pre_status = pre_df.iloc[int(number)]['status']
            pre_diameter = pre_df.iloc[int(number)]['diameter']
            pre_length = pre_df.iloc[int(number)]['length']

            print('修正データの入力')
            material = input(f'材質 - [refernce/{pre_material}]')
            if len(material) == 0:
                material = pre_material
            status = input(f'状態 - [refernce/{pre_status}]')
            if len(status) == 0:
                status = pre_status
            diameter = input(f'径 - [refernce/{pre_diameter}]')
            if len(diameter) == 0:
                diameter = pre_diameter
            length = input(f'長さ - [refernce/{pre_length}]')
            if len(length) == 0:
                length = pre_length

            print('\n')
            print('修正前データ')
            print('*'*20)
            print(f'材質: {pre_material}')
            print(f'状態: {pre_status}')
            print(f'径: {pre_diameter}')
            print(f'長さ: {pre_length}')
            print('*'*20)

            print('\n')
            print('修正後データ')
            print('*'*20)
            print(f'材質: {material}')
            print(f'状態: {status}')
            print(f'径: {diameter}')
            print(f'長さ: {length}')
            print('*'*20)

            conf = input('登録更新しますか？ - [yes: y]')
            if conf == 'y':
                sql = f"""
                    UPDATE material
                    SET
                        material = '{material}',
                        status = '{status}',
                        diameter = '{diameter}',
                        length = '{length}'
                    WHERE
                        material_id = '{pre_material_id}'
                """
                con = sqlite3.connect(db_path)
                cursor = con.cursor()
                cursor.execute(sql)
                con.commit()
                print('=== 登録完了 ===')
                break
            else:
                q = input('登録を中止しますか？ - [yes: y]')
                if q == 'y':
                    break
        except:
            print('不正な値です')
            continue


def return_history_material_dataframe(db_path):
    """
    鋼材履歴データを返す

    db_path: データベースのパス
    """
    diameter = input('径を入力')
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(
            f"""
            SELECT
                material.material_id,
                material,
                status,
                diameter,
                length,
                history_material.quantity,
                history_material.note,
                history_material.date as 'last update'
            FROM
                material
            INNER JOIN
                history_material
            ON
                material.material_id = history_material.material_id
            WHERE
                material.diameter = '{diameter}'
            ORDER BY
                history_material.date DESC
            """, con
        )
    return df


def delete_history_material_data(db_path):
    """
    鋼材の履歴データを削除する

    db_path: データベースのパス
    """
    while True:
        print('登録データの表示')
        pre_df = return_history_material_dataframe(db_path)
        pre_dff = pre_df[
            [
                'material', 'status', 'diameter',
                'length', 'quantity', 'note', 'last update'
            ]
        ]
        print(pre_dff)
        number = input('select No.')
        try:
            pre_material_id = pre_df.iloc[int(number)]['material_id']
            pre_material = pre_df.iloc[int(number)]['material']
            pre_status = pre_df.iloc[int(number)]['status']
            pre_diameter = pre_df.iloc[int(number)]['diameter']
            pre_length = pre_df.iloc[int(number)]['length']
            pre_quantity = pre_df.iloc[int(number)]['quantity']
            pre_note = pre_df.iloc[int(number)]['note']
            pre_date = pre_df.iloc[int(number)]['last update']

            print('\n')
            print('削除データ')
            print('*'*20)
            print(f'材質: {pre_material}')
            print(f'状態: {pre_status}')
            print(f'径: {pre_diameter}')
            print(f'長さ: {pre_length}')
            print(f'数量: {pre_quantity}')
            print(f'注記事項: {pre_note}')
            print(f'更新日: {pre_date}')
            print('*'*20)

            conf = input('履歴データを削除しますか？ - [yes: y]')
            if conf == 'y':
                sql = f"""
                    DELETE FROM
                        history_material
                    WHERE
                        material_id = '{pre_material_id}'
                        AND
                        quantity = '{pre_quantity}'
                        AND
                        note = '{pre_note}'
                        AND
                        date = '{pre_date}'
                """
                con = sqlite3.connect(db_path)
                cursor = con.cursor()
                cursor.execute(sql)
                con.commit()
                print('=== 削除完了 ===')
                break
            else:
                q = input('削除を中止しますか？ - [yes: y]')
                if q == 'y':
                    break
        except:
            print('不正な値です')
            continue


def save_material_list(csv_path, db_path):
    """
    最新の鋼材データの一覧をcsvに保存する

    csv_path: 出力するファイルのパス
    db_path: データベースのパス
    """
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(
            """
            SELECT
                material,
                status,
                diameter,
                length,
                history_material.quantity,
                MAX(history_material.date) as 'last undate'
            FROM
                material
            INNER JOIN
                history_material
            ON
                material.material_id = history_material.material_id
            GROUP BY
                material.material_id
            ORDER BY
                diameter
            """, con
        )
    df.to_csv(csv_path)


def check_machine_name(machine_name, db_path):
    """
    データベースに機械の登録があればTrueを、なければFalseを返す

    machine_name: データベースに問い合わせる機械名
    db_path: データベースのパス
    """
    while True:
        con = sqlite3.connect(db_path)
        cursor = con.cursor()
        cursor.execute(
            f"""
            SELECT
                symbol
            FROM
                machine
            WHERE
                symbol = '{machine_name}'
            """
        )
        res = cursor.fetchone()
        if not res:
            return False
        else:
            return True
