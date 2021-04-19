'''
quick start : python3 main.py --ip {dtp_server ip} --server_name dtp_server --client_name dtp_client --network traces_1.txt
'''
import os, platform, json
import shutil
import time
import numpy as np
import argparse
from tqdm import tqdm
from qoe import cal_single_block_qoe
import re
import json

# the numbers that you can control
numbers = 60
server_ip = "127.0.0.1"
port = "5555"

# the default parameters of network trace generation
# S_BWS = [0.005, 0.5, 1, 10, 42] # Mbps
# RTTS = [200, 400, 600, 800] # ms
# LOSSES = [10**(-5), 10**(-4), 10**(-3), 10**(-2), 2*10**(-2), 5 * 10**(-2), 10**(-1), 2 * 10**(-1)]
# C_BWS = [0.5] #Mbps

S_BWS = [100, 42] # Mbps
RTTS = [600, 800] # ms
LOSSES = [0.01]
C_BWS = [0.1, 0.05] #Mbps

TEST_TRACES_PATH = "./test_traces"

# define parser
parser = argparse.ArgumentParser()

# container settings
parser.add_argument('--ip', type=str, required=False, help="the ip of container_server_name that required")

parser.add_argument('--port', type=str, default="5555",help="the port of dtp_server that required,default is 5555, and you can randomly choose")

parser.add_argument('--numbers', type=int, default=60, help="the numbers of blocks that you can control")

parser.add_argument('--server_name', type=str, required=True, default="dtp_server", help="the container_server_name ")

parser.add_argument('--client_name', type=str, required=True, default="dtp_client", help="the container_client_name ")

# baseline setting
parser.add_argument('--type', type=int, required=True, default=0, help="0: DTP, 1: TCP, 2:DTP-Space")

parser.add_argument('--run_path', type=str, default="/home/aitrans-server/", help="the path of aitrans_server")

parser.add_argument('--solution_files', type=str, default=None, help="the path of solution files")

parser.add_argument('--baselines',action="store_true", default=False, help="use generated network traces to create baselines")

parser.add_argument('--config', type=str, default=None, help="configuration file to reimplementate test")

# application setting

parser.add_argument('--block', type=str, default=None, help="the block trace file ")

# network settings
parser.add_argument('--network_s', type=str, default=None, help="the network trace file for server")

parser.add_argument('--network_c', type=str, default=None, help="the network trace file for client")

parser.add_argument('--sbw', type=float, help="choose the bandwidth baseline traces for baseline tests")

parser.add_argument('--cbw', type=float, help="choose the bandwidth baseline traces for baseline tests")

parser.add_argument('--loss', type=float, help="set the loss")

parser.add_argument('--rtt', type=int, help="set the rtt")

parser.add_argument('--asymmetry', action="store_false", default=True)

# program settings
parser.add_argument('--run_times', type=int, default=1, help="The times that you want run repeatly")

parser.add_argument('--enable_print', type=bool, default=False, help="Whether or not print information of processing")

parser.add_argument('--rtime', type=int, default=3, help="seconds to wait before the server stops")

# retest setting
parser.add_argument('--retest', type=str, default=None)

# parse argument
params                = parser.parse_args()
server_ip             = params.ip
port                  = params.port
numbers               = params.numbers
container_server_name = params.server_name
container_client_name = params.client_name

p_type                = params.type
docker_run_path       = params.run_path
solution_files        = params.solution_files
test_baseline         = params.baselines
config_file           = params.config

block_trace           = params.block

network_s             = params.network_s
network_c             = params.network_c
p_s_bw                = params.sbw
p_c_bw                = params.cbw
p_loss                = params.loss
p_rtt                 = params.rtt
p_asymmetry           = params.asymmetry

run_times             = params.run_times
enable_print          = params.enable_print
p_rtime               = params.rtime

retest                = params.retest

network_trace         = network_s or network_c

# parse and store baseline config
baseline_config = {
    "type": p_type,
    "sbws": S_BWS,
    "cbws": C_BWS,
    "rtts": RTTS,
    "losses": LOSSES,
    "asymmetry": p_asymmetry,
    "run_times": run_times,
    "rtime": p_rtime
}
# judge system
order_preffix = " " if "windows" in platform.system().lower() else "sudo "
tc_preffix_s = "" if network_s or test_baseline or retest else "# "
tc_preffix_c = "" if network_c or test_baseline or retest else "# "
cur_path = os.getcwd() + '/'
compile_preffix = ''

# move shell scripts to tmp directory
tmp_shell_preffix = "./tmp"
if not os.path.exists(tmp_shell_preffix):
    os.mkdir(tmp_shell_preffix)

# move logs to log diectory
logs_preffix = "./logs"
if not os.path.exists(logs_preffix):
    os.mkdir(logs_preffix)


# check whether local file path is right
if block_trace and not os.path.exists(block_trace):
    raise ValueError("no such block trace in '%s'" % (cur_path + block_trace))
if network_trace and test_baseline:
    raise ValueError("only either network or baselises option can be used")
if network_s and not os.path.exists(network_s):
    raise ValueError("no such network trace in '%s'" % (cur_path + network_s))
if network_c and not os.path.exists(network_c):
    raise ValueError("no such network trace in '%s'" % (cur_path + network_c))
# if network_trace and not os.path.exists(network_trace):
#     raise ValueError("no such network trace in '%s'" % (cur_path + network_trace))
if solution_files:
    if not os.path.exists(solution_files):
        raise ValueError("no such solution_files in '%s'" % (cur_path + solution_files))
    tmp = os.listdir(solution_files)
    if not "solution.cxx" in tmp:
        raise ValueError("There is no solution.cxx in your solution path : %s" % (cur_path + solution_files))
    if not "solution.hxx" in tmp:
        raise ValueError("There is no solution.hxx in your solution path : %s" % (cur_path + solution_files))
    # if upload files that already finished compile
    compile_preffix = '#' if "libsolution.so" in tmp else ''

def prepare_docker_files(s_trace_path=None, c_trace_path=None):
    # init block trace
    if block_trace:
        os.system(order_preffix + "docker cp " + block_trace + ' ' + container_server_name + ":%strace/block_trace/aitrans_block.txt" % (docker_run_path))
    # init network traces
    if test_baseline:
        if s_trace_path is None or c_trace_path is None:
            raise ValueError("Either of baseline traces is None in a baseline test")
        os.system(order_preffix + "docker cp " + s_trace_path + ' ' + container_server_name + ":%strace/traces.txt" % (docker_run_path))
        os.system(order_preffix + "docker cp " + c_trace_path + ' ' + container_client_name + ":%strace/traces.txt" % (docker_run_path)) 
    if network_s:
        os.system(order_preffix + "docker cp " + network_s + ' ' + container_server_name + ":%strace/traces.txt" % (docker_run_path))
    if network_c:
        os.system(order_preffix + "docker cp " + network_c + ' ' + container_client_name + ":%strace/traces.txt" % (docker_run_path))
    # init solution files
    if solution_files:
        os.system(order_preffix + "docker cp " + solution_files + ' ' + container_server_name + ":%sdemo/." % (docker_run_path))

# prepare shell code
def prepare_shell_code():
    client_run_line = './client --no-verify http://{0}:{1}'.format(server_ip, port) if type == 0 or type == 1 \
        else 'LD_LIBRARY_PATH=./lib:./lib/libtorch/lib ./client {0} {1} & > ./client.log & '.format(server_ip, port)
    client_run = '''
    #!/bin/bash
    cd {0}
    {1} python3 traffic_control.py -load trace/traces.txt > tc.log 2>&1 &
    rm client.log > tmp.log 2>&1
    sleep 0.2
    {2}
    {1} python3 traffic_control.py --reset eth0
    '''.format(docker_run_path, tc_preffix_c, client_run_line)

    server_run_line = 'LD_LIBRARY_PATH=./lib ./bin/server {0} {1} trace/block_trace/aitrans_block.txt &> ./log/server_aitrans.log &'.format(server_ip, port) if type == 0 or type == 1 \
        else 'LD_LIBRARY_PATH=./lib:./lib/libtorch/lib ./bin/server {0} {1} trace/block_trace/aitrans_block.txt &> ./log/server_aitrans.log &'.format(server_ip, port)
         
    server_run = '''
    #!/bin/bash
    cd {2}
    {3} python3 traffic_control.py -aft 3.1 -load trace/traces.txt > tc.log 2>&1 &

    cd {2}demo
    {5} rm libsolution.so ../lib/libsolution.so
    {5} g++ -shared -fPIC solution.cxx -I include -o libsolution.so > compile.log 2>&1
    cp libsolution.so ../lib

    # check port
    a=`lsof -i:{4} | awk '/server/ {{print$2}}'`
    if [ $a > 0 ]; then
        kill -9 $a
    fi

    cd {2}
    rm log/server_aitrans.log 
    {6}
    '''.format(server_ip, port, docker_run_path, tc_preffix_s, port, compile_preffix, server_run_line)

    with open(tmp_shell_preffix + "/server_run.sh", "w", newline='\n')  as f:
        f.write(server_run)

    with open(tmp_shell_preffix + "/client_run.sh", "w", newline='\n') as f:
        f.write(client_run)

# run shell order
order_list = [
    order_preffix + " docker cp ./traffic_control.py " + container_server_name + ":" + docker_run_path,
    order_preffix + " docker cp ./traffic_control.py " + container_client_name + ":" + docker_run_path,
    order_preffix + " docker cp %s/server_run.sh " %(tmp_shell_preffix) + container_server_name + ":" + docker_run_path,
    order_preffix + " docker cp %s/client_run.sh " %(tmp_shell_preffix) + container_client_name + ":" + docker_run_path,
    order_preffix + " docker exec -itd " + container_server_name + " nohup /bin/bash %sserver_run.sh" % (docker_run_path)
]

def load_baseline_trace_lists():
    return os.listdir(TEST_TRACES_PATH)
    
def run_dockers():
    global server_ip, order_list
    qoe_sample = []
    run_seq = 0
    retry_times = 0
    while run_seq < run_times:
        print("The %d round :" % (run_seq))

        print("--restart docker--")
        os.system("docker restart %s %s" % (container_server_name, container_client_name))
        time.sleep(5)
        # get server ip after restart docker
        if not server_ip:
            out = os.popen("docker inspect %s" % (container_server_name)).read()
            out_dt = json.loads(out)
            server_ip = out_dt[0]["NetworkSettings"]["IPAddress"] 

        prepare_shell_code()
        for idx, order in enumerate(order_list):
            print(idx, " ", order)
            os.system(order)

        # ensure server established succussfully
        time.sleep(3)
        print("run client")
        os.system(order_preffix + " docker exec -it " + container_client_name + "  /bin/bash %sclient_run.sh" % (docker_run_path))
        # ensure connection closed
        time.sleep(p_rtime)

        stop_server = '''
        #!/bin/bash
        cd {0}
        a=`lsof -i:{1} | awk '/server/ {{print$2}}'`
        if [ $a > 0 ]; then
            kill -9 $a
        fi
        {2} kill `ps -ef | grep python | awk '/traffic_control/ {{print $2}}'`
        {2} python3 traffic_control.py --reset eth0
        '''.format(docker_run_path, port, tc_preffix_s)

        with open(tmp_shell_preffix + "/stop_server.sh", "w", newline='\n')  as f:
            f.write(stop_server)

        print("stop server")
        os.system(order_preffix + " docker cp %s/stop_server.sh " %(tmp_shell_preffix) + container_server_name + ":%s" % (docker_run_path))
        os.system(order_preffix + " docker exec -it " + container_server_name + "  /bin/bash %sstop_server.sh" % (docker_run_path))
        # move logs
        os.system(order_preffix + " rm -f logs/*")
        os.system(order_preffix + " docker cp " + container_client_name + ":%sclient.log %s/." % (docker_run_path, logs_preffix))
        os.system(order_preffix + " docker cp " + container_server_name + ":%slog/server_aitrans.log %s/." % (docker_run_path, logs_preffix))
        os.system(order_preffix + " docker cp " + container_server_name + ":%sdemo/compile.log %s/compile.log" % (docker_run_path, logs_preffix))
        if network_trace or test_baseline or retest: 
            os.system(order_preffix + " docker cp " + container_client_name + ":%stc.log %s/client_tc.log" % (docker_run_path, logs_preffix))
            os.system(order_preffix + " docker cp " + container_server_name + ":%stc.log %s/server_tc.log" % (docker_run_path, logs_preffix))
        # move .so file
        os.system(order_preffix + " docker cp " + container_server_name + ":%slib/libsolution.so %s/." % (docker_run_path, logs_preffix))

        # cal qoe
        now_qoe = cal_single_block_qoe("%s/client.log" % (logs_preffix), 0.9)
        # rerun main.py if server fail to start
        try:
            f = open("%s/client.log" % (logs_preffix), 'r')
            if len(f.readlines()) <= 5:
                print("server run fail, begin restart!")
                retry_times += 1
                continue
        except:
            print("Can not find %/client.log, file open fail!" % (logs_preffix))
        # with open("%s/client.log" % (logs_preffix), 'r') as f:
        #     if len(f.readlines()) <= 5:
        #         if enable_print:
        #             print("server run fail, begin restart!")
        #         continue
        qoe_sample.append(now_qoe)
        print("qoe : ", now_qoe)
        run_seq += 1

    if run_times > 1:
        print("qoe_sample : ", qoe_sample)

    return qoe_sample, retry_times

def generate_net_trace(s_bws, c_bws, losses, rtts, asymmetry=True):
    '''
    generate consistent network trace
    
    example: 0, 1, 0.00001, 100 # @0 second, 1Mbps, loss rate=0.00001, 100ms latency
    '''
    if not os.path.exists(TEST_TRACES_PATH):
        os.mkdir(TEST_TRACES_PATH)

    test_pairs = []

    # create server, client tc file
    if asymmetry:
        if len(s_bws) != len(c_bws):
            raise ValueError("when `asymmetry` is True, the length of `sbw` should be equal to that of `cbw`")
        for i in range(len(s_bws)):
            sbw = s_bws[i]
            cbw = c_bws[i]
            for rtt in rtts:
                for loss in losses:
                    filename_s = "sbw%f_cbw%f_loss%f_rtt%d_s.txt" % (sbw, cbw, loss, rtt)
                    filepath_s = os.path.join("./test_traces/", filename_s)
                    with open(filepath_s, 'w') as f:
                        f.write("0,%f,%f,%f" % (sbw, loss, rtt / 2 / 1000))

                    filename_c = "sbw%f_cbw%f_loss%f_rtt%d_c.txt" % (sbw, cbw, loss, rtt)
                    filepath_c = os.path.join("./test_traces/", filename_c)
                    with open(filepath_c, 'w') as f:
                        f.write("0,%f,%f,%f" % (cbw, loss, rtt / 2 / 1000))
                    
                    test_pairs.append((filename_s, filename_c))
    else:
        for sbw in s_bws:
            for rtt in rtts:
                for loss in losses:
                    filename_s = "sbw%f_cbw%f_loss%f_rtt%d_s.txt" % (sbw, sbw, loss, rtt)
                    filepath_s = os.path.join("./test_traces/", filename_s)
                    with open(filepath_s, 'w') as f:
                        f.write("0,%f,%f,%f" % (sbw, loss, rtt / 2 / 1000))

                    filename_c = "sbw%f_cbw%f_loss%f_rtt%d_c.txt" % (sbw, sbw, loss, rtt)
                    filepath_c = os.path.join("./test_traces/", filename_c)
                    with open(filepath_c, 'w') as f:
                        f.write("0,%f,%f,%f" % (sbw, loss, rtt / 2 / 1000))
                        
                    test_pairs.append((filename_s, filename_c))
    
    return test_pairs

if __name__ == "__main__":
    # retest with network config in each line of server_error.log
    if retest is not None:
        DIRNAME_PARSE_PATTERN = re.compile(r'sbw(\d|.+)_cbw(\d|.+)_loss(\d|.+)_rtt(\d+)_(\d+)')
        BACKUP_BASE_PATH = "./baselines_bk"
        retest_dir = os.path.join(BACKUP_BASE_PATH, retest)
        if os.path.exists(retest_dir):
            with open(os.path.join(retest_dir, 'server_error.log')) as file:
                paths = file.readlines()
                if len(paths) == 0:
                    # don't need to retry
                    print("don't need to retest")
                    exit()
                else:
                    for dir in paths:
                        config = dir.split('/')[-1]
                        match = DIRNAME_PARSE_PATTERN.match(config)
                        backup_path = str(dir).strip()
                        if not os.path.exists(backup_path):
                            os.mkdir(backup_path)
                        print("Logs in %s" % backup_path)

                        sbws = [float(match.group(1))]
                        cbws = [float(match.group(2))]
                        losses = [float(match.group(3))]
                        rtts = [float(match.group(4))]

                        net_filename_pairs = generate_net_trace(sbws, cbws, losses, rtts, asymmetry=True)
                        s_name, c_name = net_filename_pairs[0]
                        prepare_docker_files(os.path.join(TEST_TRACES_PATH, s_name), os.path.join(TEST_TRACES_PATH, c_name))
                        qoe_samples, retry_times = run_dockers()
                        # copy logs
                        logs_list = os.listdir(logs_preffix)
                        for file in logs_list:
                            if not file.endswith("log"):
                                continue
                            shutil.copy(os.path.join(logs_preffix, file), backup_path)
                        # save qoe
                        with open(os.path.join(backup_path, "qoe.log"), "w") as f:
                            for qoe in qoe_samples:
                                f.write(str(qoe))
                                f.write("\n") 
                        # save retry times
                        with open(os.path.join(backup_path, "retry.log"), "w") as f:
                            f.write(str(retry_times))
    elif test_baseline:
        # test baselines with given network parameters
        if p_s_bw is not None:
            sbws = [p_s_bw]
        else:
            sbws = S_BWS
        baseline_config["sbws"] = sbws

        if p_loss is not None:
            losses = [p_loss]
        else:
            losses = LOSSES
        baseline_config["losses"] = losses

        if p_rtt is not None:
            rtts = [p_rtt]
        else:
            rtts = RTTS
        baseline_config["rtts"] = rtts

        if p_c_bw is not None:
            cbws = [p_c_bw for sbw in sbws]
        else:
            cbws = C_BWS
        baseline_config["cbws"] = cbws

        net_filename_pairs = generate_net_trace(sbws, cbws, losses, rtts, asymmetry=p_asymmetry)
        
        # backup logs and qoe
        BACKUP_BASE_PATH = "./baselines_bk/t%i" % time.time()
        if not os.path.exists(BACKUP_BASE_PATH):
            os.mkdir(BACKUP_BASE_PATH)
        BACKUP_TRACE_PATH = os.path.join(BACKUP_BASE_PATH, "raw")

        if not os.path.exists(BACKUP_TRACE_PATH):
            os.mkdir(BACKUP_TRACE_PATH)

        with open(os.path.join(BACKUP_BASE_PATH, "config.json"), 'w') as f:
            json.dump(baseline_config, f)

        for s_name, c_name in tqdm(net_filename_pairs):
            backup_path = os.path.join(BACKUP_TRACE_PATH, s_name[:-6] + "_" + str(p_type))
            if not os.path.exists(backup_path):
                os.mkdir(backup_path)
            print("Logs in %s" % backup_path)
            prepare_docker_files(os.path.join(TEST_TRACES_PATH, s_name), os.path.join(TEST_TRACES_PATH, c_name))
            qoe_samples, retry_times = run_dockers()
            # copy logs
            logs_list = os.listdir(logs_preffix)
            for file in logs_list:
                if not file.endswith("log"):
                    continue
                shutil.copy(os.path.join(logs_preffix, file), backup_path)
            # save qoe
            with open(os.path.join(backup_path, "qoe.log"), "w") as f:
                for qoe in qoe_samples:
                    f.write(str(qoe))
                    f.write("\n")
            # save retry times
            with open(os.path.join(backup_path, "retry.log"), "w") as f:
                f.write(str(retry_times))
    else:
        prepare_docker_files()
        run_dockers()