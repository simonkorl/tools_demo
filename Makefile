BLOCK_TRACE_DIR = $(CURDIR)
TEST_TRACE_DIR = $(CURDIR)

# default image tag: $(IMAGE_NAME):$(TYPE).$(VERSION).$(TAIL)
IMAGE_NAME = some_image

TYPE_TMP = 0
TYPE = $(TYPE_TMP)

VERSION = 0

TAIL = 0

SERVER_NAME = aitrans_server
CLIENT_NAME = aitrans_client

NETWORK_S = $(TEST_TRACE_DIR)/sbw0.005000_cbw0.500000_loss0.200000_rtt200_s.txt
NETWORK_C = $(TEST_TRACE_DIR)/sbw0.005000_cbw0.500000_loss0.200000_rtt200_c.txt

BLOCK = $(BLOCK_TRACE_DIR)/aitrans_block.txt

RTIME = 3

RUN_TIMES = 1

.PHONY: all

test: _restart_docker
	python main.py --server_name $(SERVER_NAME) --client_name $(CLIENT_NAME)

parse:
	python data_process.py

copy:
	cp -r ./baselines_bk ~/baseline_data_process

network:
	python baseline.py --type $(TYPE) --server_name $(SERVER_NAME) --client_name $(CLIENT_NAME) --block $(BLOCK) --network_s $(NETWORK_S) --network_c $(NETWORK_C) --rtime $(RTIME)

retest:
	python baseline.py --type $(TYPE) --server_name $(SERVER_NAME) --client_name $(CLIENT_NAME) --block $(BLOCK) --retest $(TESTID) --rtime $(RTIME)

baseline_tmp: TYPE=9
baseline_tmp:
	make _baseline_base

baseline_space: TYPE=2
baseline_space:
	make _baseline_base

baseline_tcp: TYPE=1
baseline_tcp:
	make _baseline_base

baseline_dtp: TYPE=0
baseline_dtp:
	make _baseline_base

_baseline_base:
	make _restart_docker
	make baseline

_restart_docker:
	sudo docker stop $(SERVER_NAME); \
	sudo docker stop $(CLIENT_NAME); \
	sudo docker rm $(SERVER_NAME); \
	sudo docker rm $(CLIENT_NAME); \
	sudo docker run --privileged -dit --cap-add=NET_ADMIN --name $(SERVER_NAME) $(IMAGE_NAME):$(TYPE).$(VERSION).$(TAIL); \
	sudo docker run --privileged -dit --cap-add=NET_ADMIN --name $(CLIENT_NAME) $(IMAGE_NAME):$(TYPE).$(VERSION).$(TAIL); \

baseline: _restart_docker
	python baseline.py --server_name $(SERVER_NAME) --client_name $(CLIENT_NAME) --block $(BLOCK) --baselines --type $(TYPE) --run_times $(RUN_TIMES) --rtime $(RTIME) 