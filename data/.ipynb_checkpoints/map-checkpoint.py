# [[[X1, X2], [Y1, Y2]], [[X1, X2], [Y1, Y2]]]
WALL = [
    [[3, 10], [0,0]], 
    [[12, 28], [8,8]],
    [[3,3], [8,2.5]],
]

MAZE = [
    [1 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 if i == 0 or i==39 else 0 for i in range(40)],
    [1 for i in range(40)],    
]

MACHINE_POSITION = {
    'L1' : [[35, 26], [37, 26],[37, 28],[35, 28]], 
    'L2' : [[20, 2], [21, 2], [21, 4], [20, 4]], 
    'M1' : [[15, 16], [17, 16], [17, 18], [15, 18]], 
    'M2' : [[6, 26], [8, 26], [8, 28], [6, 28]], 
    'M3' : [[2, 5], [4, 5], [4, 7], [2, 7]]
}

"""
MACHINE_POSITION = {
    'L1' : [35, 26, 37, 28], 
    'L2' : [20, 2 ,21, 4], 
    'M1' : [15, 16, 17, 18], 
    'M2' : [6, 26, 8, 28], 
    'M3' : [2, 5, 4, 7]
}
"""
