import enum


class Mstatus(enum.Enum):
    """機械の状態
    """
    EMPUTY = enum.auto() #未計画
    NOT_SET = enum.auto() #段取り前
    SETTING = enum.auto() #段取り、取付中
    STOP = enum.auto() #停止中
    RUNNING = enum.auto() #稼働中
    TROUBLE = enum.auto() #故障中

    
class Pstatus(enum.Enum):
    """製品の状態
    """
    MATERIAL = enum.auto() #素材,加工前
    IN_LATHE = enum.auto() #L加工中
    IN_MILLING = enum.auto() #F加工中
    DONE = enum.auto() #完了

    
class Wstatus(enum.Enum):
    """作業者の状態
    """
    WAIT = enum.auto() #待機中
    MOVE = enum.auto() #移動中
    WORK = enum.auto() #作業中
    ON_BREAK = enum.auto() #休憩、勤務時間外