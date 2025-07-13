module sync_fifo 
#( 
	parameter integer DATA_WIDTH = 'd32,

/* The FIFO_DEPTH must be greater or equalt to 1 */
	parameter integer FIFO_DEPTH = 'd64
)
(
	input  wire 				clk,
	input  wire 				arst_n,
	input  wire 				srst,

	output wire 						in_rdy_o,
	input  wire							in_vld_i,
	input  wire [DATA_WIDTH-1:0]		in_data_i,

	input  wire 						out_rdy_i,
	output wire 						out_vld_o,
	output wire [DATA_WIDTH-1:0]		out_data_o,

	output wire 						empty_o,
	output wire 						full_o
);

localparam  integer FIFO_DEPTH_L2 = $clog2(FIFO_DEPTH);

reg [DATA_WIDTH-1:0] fifo_mem [FIFO_DEPTH-1:0];
reg [FIFO_DEPTH_L2-1:0] wr_ptr, rd_ptr;

wire write_vld = in_rdy_o & in_vld_i & ~full_o;
wire read_vld  = out_rdy_i & out_vld_o & ~empty_o;

always @(posedge clk) begin 
	if( !arst_n || srst ) begin 
		wr_ptr <= 'b0;
		rd_ptr <= 'b0;
	end
end


/* Handling the writes to the FIFO  */
always @(posedge clk) begin 
	if(write_vld) begin 
		fifo_mem[wr_ptr] <= in_data_i;
	end
end

/* Handling reads from the fifo */
assign out_data_o = fifo_mem[rd_ptr];

/* Handling the rd/wr pointers */
always @(posedge clk) begin 
	if (write_vld) begin
		wr_ptr <= (wr_ptr == FIFO_DEPTH-1) ? 0 : wr_ptr + 1;
	end

	if (read_vld) begin
		rd_ptr <= (rd_ptr == FIFO_DEPTH-1) ? 0 : rd_ptr + 1;
	end
end

assign full_o    = ((wr_ptr+1'b1) == rd_ptr);
assign empty_o   = (wr_ptr == rd_ptr);
assign in_rdy_o  = ~full_o;
assign out_vld_o = ~empty_o;

  initial begin
    $dumpfile("dump.vcd");
    $dumpvars(1, sync_fifo);
end

endmodule
