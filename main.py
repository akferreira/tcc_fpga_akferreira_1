from urllib.request import urlopen
import json,os
from collections import Counter,defaultdict
from pathlib import Path
import random
from src import utils
from src.fpgaBoard import FpgaBoard
import logging

fpga_config_url = 'https://raw.githubusercontent.com/akferreira/tcc_fpga_akferreira_1/main/fpga.json'
partition_config_url = 'https://raw.githubusercontent.com/akferreira/tcc_fpga_akferreira_1/main/partition.json'
fpga_config_filename = 'fpga.json'
partition_config_filename = 'partition.json'
coord_X = 0
coord_Y = 1
matrix_line = 0
matrix_column = 1

parent_dir = Path(__file__).parent.parent
fpga_config = utils.load_json_config_file( os.path.join(parent_dir,fpga_config_filename) )
fpga_config.update(utils.load_json_config_file( os.path.join(parent_dir,partition_config_filename)))
fpgaBoard = FpgaBoard(fpga_config)

print(fpga_config["partition_size"]['S'])
print(fpgaBoard.calculate_region_resources( (0,13),(86,14)))
print("--")

# print(fpga_config["partition_size"])
# print(fpgaBoard.dimensions)
# print(f"Inner static {fpgaBoard.isCoordsInnerStatic((60,3))}")

# fpgaBoard.allocate_region((0,0),(71,1))
random_coords =  utils.generate_random_fpga_coord(15, 182, fpgaBoard)
print(f"{random_coords}")
count = 0

for i in range(30):
  count = i
  allocation_region_test = fpgaBoard.find_allocation_region(random_coords, 'S')
  if(allocation_region_test is not None):
    break
  #print(allocation_region_test )
print(f"{count=}")
print(allocation_region_test )
if (allocation_region_test is not None):
  fpgaBoard.allocate_region(allocation_region_test[0], allocation_region_test[1])

allocation_region_test = fpgaBoard.find_allocation_region((170,4), 'S')
if (allocation_region_test is not None):
  fpgaBoard.allocate_region(allocation_region_test[0], allocation_region_test[1])

utils.print_board(fpgaBoard)
exit(0)

fpgaBoard.allocate_region((59,14),(152, 13) )
print(fpgaBoard.calculate_region_resources((59,14),(152, 13) ))
utils.print_board(fpgaBoard)


print(fpgaBoard.isCoordsEdgeBoard( (0,0) ))