import datetime
import jpholiday
import numpy as np
import networkx as nx
import openpyxl as xl


def points_to_sec(lst):
    """点名のリストから区間のリストを作る

    >>> points_to_sec(['a', 'b', 'c', 'd', 'e'])
    ['a-b', 'b-c', 'c-d', 'd-e']

    >>> lst = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    >>> points_to_sec(lst)
    ['1-2', '2-3', '3-4', '4-5', '5-6', \
'6-7', '7-8', '8-9', '9-10']

    """
    route = []
    for x in lst[:-1]:
        sec = str(x) + '-' + str(lst[lst.index(x) + 1])
        route.append(sec)
    return route


def points_to_move_list(dic_points):
    """{'A':[100, 105], 'B':[105, 103]}の様な2点の座標から
    {'A-B':[[1, -1],[1, -1], [1, 0], [1, 0], [1, 0]]}という形の
    2点間の移動用リストの辞書を作成して返す

    >>> d = {'A':[100, 105], 'B':[105, 103]}
    >>> points_to_move_list(d)
    {'A-B': [[1, -1], [1, -1], [1, 0], [1, 0], [1, 0]]}

    """
    key = []
    sec = []
    for k, v in dic_points.items():
        key.append(k)
        sec.append(v)
    key = str(key[0]) + '-' + str(key[1])
    sec = (np.array(sec[1]) - np.array(sec[0])).tolist()

    lst_0_1 = []
    lx = []
    ly = []
    for x in range(abs(int(sec[0]))):
        lx.append(int(sec[0]/abs(sec[0])))
    lst_0_1.append(lx)

    for y in range(abs(int(sec[1]))):
        ly.append(int(sec[1]/abs(sec[1])))
    lst_0_1.append(ly)

    while abs(len(lx)-len(ly)):
        if len(lx) > len(ly):
            ly.append(int(0))
        else:
            lx.append(int(0))
    return {key: np.array([lx, ly]).T.tolist()}


def make_dic_points_from_route(points, route):
    """ 各点の座標の辞書とルートのリストから各区間ごとの点名とと座標の組合せのリストを作る
    points:各ポイントの座標
    route:順路のリスト

    >>> points = {'A' : [100, 100], 'B' : [103, 100], \
'C' : [103, 103], 'D' : [106, 103]}
    >>> route = ['A', 'B', 'C', 'D']
    >>> make_dic_points_from_route(points, route)
    [{'A': [100, 100], 'B': [103, 100]}, {'B': [103, 100], 'C': [103, 103]}, \
{'C': [103, 103], 'D': [106, 103]}]
    """

    dec_points_list = []
    for x in route[:-1]:
        d = {}
        d[x] = points[x]
        d[route[route.index(x) + 1]] = points[route[route.index(x) + 1]]
        dec_points_list.append(d)
    return dec_points_list


def seek_near_point(point, points):
    """現在地と座標を登録した辞書から現在地に一番近いポイント(キー)を取得する
    point:現在地 [101, 101]
    points:座標の辞書 {'A' : [100, 100], 'B' : [110, 105]}

    >>> positions = {'A' : [100, 100], 'B' : [110, 105], \
'C' : [103, 100], 'D' : [106, 90]}
    >>> point = [100 ,90]
    >>> seek_near_point(point, positions)
    'D'

    """
    point = np.array(point, dtype=float)
    d = {}
    for k, v in points.items():
        v = np.array(v)
        d[k] = np.linalg.norm(v-point)
    min_point = min(d, key=d.get)
    return min_point


def route_to_move_list(points, route):
    """地点の座標から移動用のリストを作成する

    >>> points = {'A' : [0, 0], 'B' : [1, 2], 'C' : [3, 4], 'D' : [5, 5]}
    >>> route = ['B', 'A', 'C', 'D']
    >>> route_to_move_list(points, route)
    [[-1, -1], [0, -1], [1, 1], [1, 1], [1, 1], [0, 1], [1, 1], [1, 0]]

    """
    sec = points_to_sec(route)
    move_dic = {}
    for section in make_dic_points_from_route(points, route):
        for k, v in points_to_move_list(section).items():
            move_dic[k] = v
    move_list = []
    for s in sec:
        for ml in move_dic[s]:
            move_list.append(ml)
    return move_list


def shortest_path(g, points, point_a, point_b):
    """グラフオブジェクトで2点間の最短経路を求める
    g: nxグラフオブジェクト
    points: 各地点の座標リスト
    point_a, point_b:経路を求める2点

    >>> import networkx as nx
    >>> import numpy as np
    >>> path = [('F', 'G'), ('G', 'H'), ('H', 'I'), ('A', 'F'), \
('B','F'), ('C', 'G'), ('D', 'H'), ('E', 'I')]
    >>> g = nx.Graph()
    >>> g.add_edges_from(path)
    >>> points = {'A' : [5, 5], 'B' : [5, 25], 'C' : [15, 15], \
'D' : [20, 5], 'E' : [35, 25], 'F' : [5, 10],  'G' : [15, 10], \
'H' : [20, 10],'I' : [35, 10]}
    >>> shortest_path(g, points, 'A', 'E')
    ['A', 'F', 'G', 'H', 'I', 'E']
    """
    for i, j in g.edges:
        g.edges[i, j]['dist'] = np.linalg.norm(
            np.array(points[i]) - np.array(points[j]))
    min_path = nx.dijkstra_path(g, point_a, point_b, weight='dist')
    return min_path


def shortest_path_length(g, points, point_a, point_b):
    """
    g: nxグラフオブジェクト
    points: 各地点の座標リスト
    point_a, point_b:経路を求める2点
    >>> import networkx as nx
    >>> import numpy as np
    >>> path = [('F', 'G'), ('G', 'H'), ('H', 'I'), ('A', 'F'), \
('B','F'), ('C', 'G'), ('D', 'H'), ('E', 'I')]
    >>> g = nx.Graph()
    >>> g.add_edges_from(path)
    >>> points = {\
        'A' : [5, 5], 'B' : [5, 25], 'C' : [15, 15], 'D' : [20, 5], \
        'E' : [35, 25], 'F' : [5, 10],  'G' : [15, 10], 'H' : [20, 10], \
        'I' : [35, 10]}
    >>> shortest_path_length(g, points, 'A', 'E')
    50.0
    """
    for i, j in g.edges:
        g.edges[i, j]['dist'] = np.linalg.norm(
            np.array(points[i]) - np.array(points[j]))
    min_path_length = nx.dijkstra_path_length(
        g, point_a, point_b, weight='dist')
    return min_path_length


def sec_to_timedelta_8h(time):
    """秒をdatetime.timedelta型に変換する。8時間で日付を更新する

    >>> sec_to_timedelta_8h(28800)
    datetime.timedelta(days=1)
    >>> str(sec_to_timedelta_8h(28800))
    '1 day, 0:00:00'
    """
    td = datetime.timedelta(
        seconds=(
            (time // (8*60*60)) * (24*60*60)
            + (time % (8*60*60))
        )
    )
    return td


def sec_to_timedelta_9h(time):
    """秒をdatetime.timedelta型に変換する。8時間で日付を更新する

    >>> sec_to_timedelta_9h(9*60*60)
    datetime.timedelta(days=1)
    >>> str(sec_to_timedelta_9h(9*60*60))
    '1 day, 0:00:00'
    """
    td = datetime.timedelta(
        seconds=(
            (time // (9*60*60)) * (24*60*60)
            + (time % (9*60*60))
        )
    )
    return td


def eight_hour_return_week(sec):
    """秒を入力すると曜日を返す。稼働時間8時間ごとに日付は更新する
    0日目:月, 1日目:火 ・・・ 4日目:金   土日は飛ばして
    5日目:月 ,6日目:火 ・・・
    という風にする

    >>> eight_hour_return_week(10)
    'Mon'
    >>> eight_hour_return_week(100000)
    'Thu'
    >>> eight_hour_return_week(8*60*60) #8時間*60分*60秒
    'Tue'
    """

    week = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri'}
    t = datetime.timedelta(seconds=(
        (sec // (8*60*60)) * (24*60*60)
        + (sec % (8*60*60))
    )
                          )
    return week[(t.days) % 5]


def nine_hour_return_week(sec):
    """秒を入力すると曜日を返す。稼働時間8時間ごとに日付は更新する
    0日目:月, 1日目:火 ・・・ 4日目:金   土日は飛ばして
    5日目:月 ,6日目:火 ・・・
    という風にする

    >>> nine_hour_return_week(10)
    'Mon'
    >>> nine_hour_return_week(100000)
    'Thu'
    >>> nine_hour_return_week(9*60*60) #9時間*60分*60秒
    'Tue'
    >>> nine_hour_return_week(5 * 9*60*60 + 1) #9時間*60分*60秒
    'Mon'
    """

    week = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri'}
    t = datetime.timedelta(seconds=(
        (sec // (9*60*60)) * (24*60*60)
        + (sec % (9*60*60))
    )
                          )
    return week[(t.days) % 5]


def time_converter(START_TIME, str_time):
    """時:分形式の文字列を始業時刻からの時間を秒に変換して返す
    例) start_time = '8:00'
    8:00 -> 0
    9:00 -> 3600 # 1*60*60

    >> time_converter('8:00', '8:00')
    0
    >> time_converter('8:00', '8:30')
    1800
    >> time_converter('8:30', '9:00')
    1800
    >> time_converter('8:00', '9:00')
    3600
    """
    st = START_TIME.split(':')  # 8:00 ->['8', '00']
    t = str_time.split(':')
    return (
        (int(t[0]) - int(st[0])) * 60 * 60
        + (int(t[1]) - int(st[1])) * 60
    )


def return_biz_day(BASE_DATE, date_count):
    """BASE_DATEから土日祝日を除いた date_count後の日付を返す

    平日5日+土日2日
    >>> return_biz_day(datetime.date(2021, 1, 20), 5)
    datetime.date(2021, 1, 27)

    1,2,3 祝日 -> date_count = 0 は1/4
    >>> return_biz_day(datetime.date(2021, 1, 1), 1)
    datetime.date(2021, 1, 5)
    """
    dt = BASE_DATE
    if date_count == 0:
        while dt.weekday() >= 5 or jpholiday.is_holiday(dt):
            dt += datetime.timedelta(days=1)
    else:
        if dt.weekday() >= 5 or jpholiday.is_holiday(dt):
            for _ in range(date_count):
                while dt.weekday() >= 5 or jpholiday.is_holiday(dt):
                    dt += datetime.timedelta(days=1)
                dt += datetime.timedelta(days=1)
        else:
            for _ in range(date_count):
                dt += datetime.timedelta(days=1)
                while dt.weekday() >= 5 or jpholiday.is_holiday(dt):
                    dt += datetime.timedelta(days=1)
            
    return dt


def count_holiday(day1, day2):
    """
    day1からday2の間に休日が何日あるか計算
    
    2021/4/3(土), 4/4(日)
    >>> count_holiday(datetime.datetime(2021, 4, 1), datetime.datetime(2021, 4, 6))
    2
    """
    if day1 <= day2:
        start_day = day1
        end_day = day2
    else:
        start_day = day2
        end_day = day1
    delta = (end_day - start_day).days
    d = 0
    if delta > 0:
        for i in range(delta):
            if start_day.weekday() >= 5 or jpholiday.is_holiday(start_day):
                d += 1
            start_day += datetime.timedelta(days=1)
    return d


def adjast_column_width_excel(file_path):
    """
    excelファイルの列幅を自動調整する

    file_path: excelファイルのパス
    """

    # read input xlsx
    wb1 = xl.load_workbook(filename=file_path)
    ws1 = wb1.worksheets[0]

    # set column width
    for col in ws1.columns:
        max_length = 0
        column = col[0].column
        # print(column ,type(column))

        for cell in col:
            if len(str(cell.value)) > max_length:
                max_length = len(str(cell.value))

        adjusted_width = (max_length + 2) * 1.2
        column_name =xl.utils.get_column_letter(column)
        ws1.column_dimensions[column_name].width = adjusted_width

    # save xlsx file
    wb1.save(file_path)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
