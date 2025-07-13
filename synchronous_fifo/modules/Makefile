TOPLEVEL_LANG ?= verilog
SIM ?= icarus
PWD=$(shell pwd)

DATA_WIDTH = 32
FIFO_DEPTH = 64

VERILOG_SOURCES= $(PWD)/../src/tb/sync_fifo.sv

COMPILE_ARGS += -Psync_fifo.DATA_WIDTH=$(DATA_WIDTH) -Psync_fifo.FIFO_DEPTH=$(FIFO_DEPTH)

TOPLEVEL := sync_fifo
MODULE 	:= fifo_sync_test

include $(shell cocotb-config --makefiles)/Makefile.sim


