BLOCK_TRACE_DIR = $(CURDIR)/../block_trace
TEST_TRACE_DIR = $(CURDIR)/test_traces
DOCKER_DIR = $(CURDIR)/..

TYPE_DTP = 0
TYPE_TCP = 1
TYPE_SPACE = 2
TYPE = $(TYPE_DTP)

NETWORK_S = $(TEST_TRACE_DIR)/sbw0.005000_cbw0.500000_loss0.200000_rtt200_s.txt
NETWORK_C = $(TEST_TRACE_DIR)/sbw0.005000_cbw0.500000_loss0.200000_rtt200_c.txt

BLOCK = $(BLOCK_TRACE_DIR)/raw/aitrans_block.txt

RTIME = 10

all: baseline_dtp baseline_tcp parse

.PHONY: baseline

parse:
	python data_process.py

copy:
	cp -r ./baselines_bk ~/baseline_data_process

network:
	python baseline.py --server_name aitrans_server --client_name aitrans_client --block $(BLOCK) --network_s $(NETWORK_S) --network_c $(NETWORK_C) --rtime $(RTIME)

retest:
	python baseline.py --server_name aitrans_server --client_name aitrans_client --block $(BLOCK) --retest $(TESTID) --rtime $(RTIME)

baseline_space:
	cd $(DOCKER_DIR) && make pre_docker_space && make image_test
	python baseline.py --server_name aitrans_server --client_name aitrans_client --block $(BLOCK) --baselines --type $(TYPE_SPACE)

baseline_tcp:
	cd $(DOCKER_DIR) && make pre_docker_tcp && make image_tc_test
	python baseline.py --server_name aitrans_server --client_name aitrans_client --block $(BLOCK) --baselines --type $(TYPE_TCP)

baseline_dtp:
	cd $(DOCKER_DIR) && make pre_docker_aitrans && make image_tc_test
	python baseline.py --server_name aitrans_server --client_name aitrans_client --block $(BLOCK) --baselines --type $(TYPE_DTP)
