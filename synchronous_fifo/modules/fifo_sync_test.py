import os
import sys
from pathlib import Path
from random import getrandbits

import cocotb
from cocotb.clock import Clock
from cocotb.handle import SimHandleBase
from cocotb.runner import get_runner
from cocotb.triggers import RisingEdge
from cocotb.queue import Queue


from collections import deque
from typing import Dict, Any

class DataValidMonitor:
    """
    Reusable Monitor of one-way control flow (data/valid) streaming data interface

    Args
        clk: clock signal
        valid: control signal noting a transaction occured
        datas: named handles to be sampled when transaction occurs
    """

    def __init__(
        self, clk: SimHandleBase, datas: Dict[str, SimHandleBase], valid: SimHandleBase
    ):
        self.values = Queue[Dict[str, int]]()
        self._clk = clk
        self._datas = datas
        self._valid = valid
        self._coro = None

    def start(self) -> None:
        """Start monitor"""
        if self._coro is not None:
            raise RuntimeError("Monitor already started")
        self._coro = cocotb.start_soon(self._run())

    def stop(self) -> None:
        """Stop monitor"""
        if self._coro is None:
            raise RuntimeError("Monitor never started")
        self._coro.kill()
        self._coro = None



    def _sample(self) -> Dict[str, Any]:
        return {name: handle.value for name, handle in self._datas.items()}

    async def _run(self) -> None:
        while True:
            await RisingEdge(self._clk)
            if self._valid.value.binstr != "1":
                await RisingEdge(self._valid)
                continue
            self.values.put_nowait(self._sample())
class FifoSyncTest:

    def __init__(self, fifo_entity: SimHandleBase):
        self.dut = fifo_entity
        self.input_mon = DataValidMonitor(
            clk= self.dut.clk,
            valid=self.dut.in_vld_i,
            datas={
                "input_data": self.dut.in_data_i,
                "input_ready": self.dut.out_rdy_i
            }
        )

        self.output_mon = DataValidMonitor(
        clk=self.dut.clk,
        valid=self.dut.out_vld_o,
        datas={
            "output_data": self.dut.out_data_o,
            "output_ready": self.dut.in_rdy_o
        }
    )
        
        self._checker = None
        
    def start(self) -> None:
        """Start the input and output monitors"""
        self.input_mon.start()
        self.output_mon.start()
        self._checker = cocotb.start_soon(self._check_fifo())


    def stop(self) -> None:
        """Stop the input and output monitors"""
        if self._checker is not None:
            self._checker.kill()
            self._checker = None
        self.input_mon.stop()
        self.output_mon.stop()

    def model(self, input_data: int) -> int:
        """Model the FIFO behavior"""
        # Simple model that returns the input data as output
        return input_data

    async def _check_fifo(self) -> None:
        cycles = 0
        while cycles < 1000:  
            await RisingEdge(self.dut.clk)
            cycles += 1
            if self.input_mon.values.empty() or self.output_mon.values.empty():
                continue

            input_data = self.input_mon.values.get_nowait()
            output_data = self.output_mon.values.get_nowait()

            expected_output = self.model(input_data["input_data"])

            if output_data["output_data"] != expected_output:
                raise AssertionError(
                    f"Output data mismatch: expected {expected_output}, got {output_data['output_data']}"
                )


@cocotb.test(
    expect_error=IndexError
    if cocotb.simulator.is_running() and cocotb.SIM_NAME.lower().startswith("ghdl")
    else None,
)
async def test_fifo_sync(dut) -> None:
   
   
    fifo_model = deque()

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    fifo_test = FifoSyncTest(dut)
    dut._log.info("Initialize and reset model")

    dut.arst_n.value = 0
    dut.in_vld_i.value = 0
    dut.out_rdy_i.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.arst_n.value = 1

    input_data_list = []
    output_data_list = []

    for _ in range(10):
        val = getrandbits(32)
        input_data_list.append(val)
        dut.in_data_i.value = val
        dut.in_vld_i.value = 1
        await RisingEdge(dut.clk)


    dut.in_vld_i.value = 0


    for _ in range(10):  
        dut.out_rdy_i.value = 1
        await RisingEdge(dut.clk)
        if dut.out_vld_o.value:
            output_data_list.append(dut.out_data_o.value.integer)

    assert len(output_data_list) == len(input_data_list), (
        f"Output data count mismatch: expected {len(input_data_list)}, got {len(output_data_list)}"
    )
    for i in range(len(input_data_list)):
        assert output_data_list[i] == input_data_list[i], (
            f"Mismatch:\nSent: {input_data_list[i]}\nGot:  {output_data_list[i]}"
        )
    
def test_fifo_sync_runner():
    
    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
    sim = os.getenv("SIM", "icarus")


    runner = get_runner()
    if not runner:
        raise RuntimeError("Cocotb runner not found. Ensure you are running this in a cocotb environment.")
    
    proj_path = Path(__file__).resolve().parent
    verilog_sources = [proj_path / "src" / "tb" / "fifo_sync.sv"]
    


    runner = get_runner(sim)

    runner.build(
        hdl_toplevel="sync_fifo",
        verilog_sources=verilog_sources,
        always=True,
    )

    runner.test(
        hdl_toplevel="sync_fifo",
        hdl_toplevel_lang=hdl_toplevel_lang,
        test_module="fifo_sync_test",
    )

if __name__ == "__main__":
    test_fifo_sync_runner()