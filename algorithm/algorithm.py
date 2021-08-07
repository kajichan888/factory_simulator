#import networkx as nx
import functools
import copy

from models.status import Wstatus
from models.status import Mstatus

from utils.utils import route_to_move_list
from utils.utils import shortest_path
from utils.utils import shortest_path_length

from data.position import POSITIONS
#from data.position import PATH

def continue_set_up(g, machine_list, worker_list, factory_time, step_time):
    for worker in worker_list:
        if (not worker.attendance and worker.position != [] and worker.status != Wstatus.MOVE):
            worker.record_interrupt(factory_time)
            #作業者の位置を記録
            worker_position_mark = copy.copy(worker.position)
            worker.position = []
            if step_time < 10:
                worker.insert_action(
                    functools.partial(
                        worker.move, 'start', 
                        route_to_move_list(
                            POSITIONS, shortest_path(
                                g, POSITIONS, 
                                worker.default_position, 
                                worker_position_mark))))
            else:
                worker.insert_action(
                    functools.partial(
                        worker.warp, 
                        'start', 
                        worker_position_mark))

    for worker in worker_list:
        if (
            worker.schedule and not worker.task_obj 
            and worker.status != Wstatus.MOVE):
            for schedule in worker.schedule:
                if schedule.now_task:
                    """ここを考える
                    移動、別の仕事を実行中、タスク実行中
                    のケースで
                    """
                    #作業者の位置を記録
                    worker_position_mark = copy.copy(worker.position)
                    if (
                        worker.status == Wstatus.WAIT 
                        and worker.position != schedule.position):
                        worker.record_interrupt(factory_time)
                        worker.insert_action(
                        functools.partial(
                            worker.execute_task, schedule
                            ))
                        if step_time < 10:
                            """move -> execute_task
                            """
                            worker.insert_action(
                                functools.partial(
                                    worker.move, schedule.place, 
                                    route_to_move_list(
                                        POSITIONS, shortest_path(
                                            g, POSITIONS, 
                                            worker.position, schedule.position
                                            ))))
                        else:
                            #worker.record_interrupt(factory_time)
                            worker.insert_action(
                                functools.partial(
                                    worker.warp,
                                    schedule.place,
                                    schedule.position
                                )
                            )
                    elif worker.status != Wstatus.MOVE:
                        if worker.position == schedule.position:
                            """移動が完了している場合
                            """
                            worker.record_interrupt(factory_time)
                            worker.insert_action(
                                functools.partial(
                                    worker.execute_task, schedule
                                    ))
                        else:
                            """実行するタスクの位置へ移動して作業
                            """
                            worker.record_interrupt(factory_time)
                            if step_time < 10:
                                """move -> execute_task ->move(タスク実行位置->現在地)
                                """
                                if worker.machine_obj:
                                    worker.insert_action(
                                        functools.partial(
                                            worker.move, worker.machine_obj.machine_name, 
                                            route_to_move_list(
                                                POSITIONS, shortest_path(
                                                    g, POSITIONS, 
                                                    schedule.position, 
                                                    worker_position_mark
                                                    ))))
                                worker.insert_action(
                                    functools.partial(
                                        worker.execute_task, schedule
                                        ))
                                worker.insert_action(
                                    functools.partial(
                                        worker.move, schedule.place, 
                                        route_to_move_list(
                                            POSITIONS, shortest_path(
                                                g, POSITIONS, 
                                                worker.position, schedule.position
                                                ))))
                            else:
                                """warp -> execute_task ->warp(タスク実行位置->現在地)
                                """
                                if worker.machine_obj:
                                    worker.insert_action(
                                        functools.partial(
                                            worker.warp, 
                                            worker.machine_obj.machine_name,
                                            worker_position_mark 
                                            ))
                                worker.insert_action(
                                    functools.partial(
                                        worker.execute_task, schedule
                                        ))
                                worker.insert_action(
                                    functools.partial(
                                        worker.warp, 
                                        schedule.place,
                                        schedule.position
                                        ))
                    else:
                        pass

    for machine in machine_list:
        if machine.status == Mstatus.STOP and not machine.worker_obj:
            free_worker = []
            for worker in worker_list:
                if (
                    not worker.action_list 
                    and worker.status != Wstatus.ON_BREAK
                    and machine.machine_name in worker.charge_list):
                    free_worker.append(worker)
            if free_worker:
                near_worker = sorted(
                    free_worker, key=(
                        lambda w: shortest_path_length(
                            g, POSITIONS, w.position, machine.position)))
                for worker in near_worker:
                    if step_time < 10:
                        if not worker.action_list and not machine.worker_obj:
                            worker.append_action(functools.partial(
                                worker.move, machine.machine_name,
                                route_to_move_list(
                                    POSITIONS, shortest_path(
                                        g, POSITIONS, worker.position, machine.position))))
                            worker.append_action(functools.partial(worker.machine_run, machine))
                            machine.worker_obj = worker
                            worker.machine_obj = machine
                    else:
                        if not worker.action_list and not machine.worker_obj:
                            worker.append_action(functools.partial(
                                worker.warp, 
                                machine.machine_name, 
                                machine.position))
                            worker.append_action(functools.partial(worker.machine_run, machine))
                            machine.worker_obj = worker
                            worker.machine_obj = machine

        if machine.status == Mstatus.NOT_SET and not machine.worker_obj:
            free_worker = []
            for worker in worker_list:
                if (
                    not worker.action_list 
                    and worker.status != Wstatus.ON_BREAK
                    and machine.machine_name in worker.charge_list):
                    free_worker.append(worker)
            if free_worker:
                near_worker = sorted(
                    free_worker, key=(
                        lambda w: shortest_path_length(
                            g, POSITIONS, w.position, machine.position)))
                for worker in near_worker:
                    if step_time < 10:
                        if not worker.action_list and not machine.worker_obj:
                            worker.append_action(functools.partial(
                                worker.move, machine.machine_name,
                                route_to_move_list(
                                    POSITIONS, shortest_path(
                                        g, POSITIONS, worker.position, machine.position))))
                            worker.append_action(functools.partial(worker.machine_continue_set_up, machine))
                            machine.worker_obj = worker
                            worker.machine_obj = machine
                    else:
                        if not worker.action_list and not machine.worker_obj:
                            worker.append_action(functools.partial(
                                worker.warp, 
                                machine.machine_name, 
                                machine.position))
                            worker.append_action(functools.partial(worker.machine_continue_set_up, machine))
                            machine.worker_obj = worker
                            worker.machine_obj = machine
    
    #作業の途中でアクションリストが消えてしまった時の処理
    for worker in worker_list:
        if worker.status == Wstatus.WAIT and not worker.action_list:
            for machine in machine_list:
                if (
                    (machine.status == Mstatus.STOP 
                    or machine.status == Mstatus.SETTING)
                    and machine.worker_obj == worker):
                    if step_time < 10:
                        worker.append_action(functools.partial(
                            worker.move, machine.machine_name,
                            route_to_move_list(
                                POSITIONS, shortest_path(
                                    g, POSITIONS, worker.position, machine.position))))
                        worker.append_action(functools.partial(worker.machine_run, machine))
                        machine.worker_obj = worker
                        worker.machine_obj = machine
                    else:
                        worker.append_action(functools.partial(
                            worker.warp, 
                            machine.machine_name, 
                            machine.position))
                        worker.append_action(functools.partial(worker.machine_run, machine))
                        machine.worker_obj = worker
                        worker.machine_obj = machine