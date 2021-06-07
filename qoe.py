import os, sys, inspect
import numpy as np

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sys.path.insert(0, currentdir)

def is_log(block_file):
    return block_file.endswith(".log")

def cal_single_block_qoe(block_file, a):
    with open(block_file, 'r') as f:
        lines = f.readlines()
    start, end = 0, 0
    for idx, line in enumerate(lines):
        if line.startswith("BlockID  bct"):
            start = idx + 1
        if line.startswith(("connection closed")):
            end = idx
    lines[:] = lines[start : end]
    lines[:] = [line.strip() for line in lines]
    lines[:] = [list(map(float, line.split())) for line in lines]
    blocks = [line for line in lines if len(line) == 5]
    qoe = 0
    max_prio = 3
    prio_weights = [i for i in range(max_prio, 0, -1)]
    Tp = 100
    for block in blocks:
        block_bct = int(block[1])
        block_size = int(block[2])
        block_prio = int(block[3])
        block_ddl = int(block[4])
        block_qoe = (a * prio_weights[block_prio] / max_prio + (1 - a)) * block_size
        ddl_weight = 1
        if block_bct <= block_ddl:
            ddl_weight = 1
        elif block_bct > block_ddl and block_bct < (block_ddl + Tp):
            ddl_weight = ((block_ddl + Tp - block_bct) / Tp)**2
        else:
            ddl_weight = 0
        qoe += block_qoe * ddl_weight 
    return qoe

def cal_player_qoe(a):
    files = list(filter(is_log,os.listdir(currentdir)))
    qoes = [cal_single_block_qoe(file, a) for file in files]
    print(qoes)
    return np.mean(qoes)

if __name__ == "__main__":
    # need to put qoe.py in dir of client's log.
    a = 0.9
    res = cal_player_qoe(a)
    print(res)
