BLOCK_TRACE_DIR = $(CURDIR)/../block_trace
TEST_TRACE_DIR = $(CURDIR)/test_traces
DOCKER_DIR = $(CURDIR)/..

TYPE_DTP = 0
TYPE_TCP = 1
TYPE_SPACE = 2
TYPE_TMP = 9
TYPE = $(TYPE_TMP)

VERSION = 0

IMAGE_NAME = simonkorl0228/qoe_test_image

NETWORK_S = $(TEST_TRACE_DIR)/sbw0.005000_cbw0.500000_loss0.200000_rtt200_s.txt
NETWORK_C = $(TEST_TRACE_DIR)/sbw0.005000_cbw0.500000_loss0.200000_rtt200_c.txt

BLOCK = $(BLOCK_TRACE_DIR)/raw/aitrans_block.txt

RTIME = 3

RUN_TIMES = 1

.PHONY: all

parse:
	python data_process.py

copy:
	cp -r ./baselines_bk ~/baseline_data_process

network:
	python baseline.py --type $(TYPE) --server_name aitrans_server --client_name aitrans_client --block $(BLOCK) --network_s $(NETWORK_S) --network_c $(NETWORK_C) --rtime $(RTIME)

retest:
	python baseline.py --type $(TYPE) --server_name aitrans_server --client_name aitrans_client --block $(BLOCK) --retest $(TESTID) --rtime $(RTIME)

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
	sudo docker stop aitrans_server; \
	sudo docker stop aitrans_client; \
	sudo docker rm aitrans_server; \
	sudo docker rm aitrans_client; \
	sudo docker run --privileged -dit --cap-add=NET_ADMIN --name aitrans_server $(IMAGE_NAME):$(TYPE).$(VERSION).2; \
	sudo docker run --privileged -dit --cap-add=NET_ADMIN --name aitrans_client $(IMAGE_NAME):$(TYPE).$(VERSION).2; \

baseline: _restart_docker
	python baseline.py --server_name aitrans_server --client_name aitrans_client --block $(BLOCK) --baselines --type $(TYPE) --run_times $(RUN_TIMES) --rtime $(RTIME) 