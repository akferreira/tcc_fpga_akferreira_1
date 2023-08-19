from urllib.request import urlopen
import json
from collections import Counter,defaultdict
import random

from . import utils
from .fpgaBoard import FpgaBoard

fpga_config_url = 'https://raw.githubusercontent.com/akferreira/tcc_fpga_akferreira_1/main/fpga.json'
partition_config_url = 'https://raw.githubusercontent.com/akferreira/tcc_fpga_akferreira_1/main/partition.json'
coord_X = 0
coord_Y = 1
matrix_line = 0
matrix_column = 1



fpga_config = utils.load_json_config(fpga_config_url)
fpga_config.update(utils.load_json_config(partition_config_url))
fpgaBoard = FpgaBoard(fpga_config)
print([fpgaBoard.matrix[0][i].resource for i in range(fpgaBoard.dimensions[1])])

print(fpgaBoard.resourceCount)

static_coord = fpgaBoard.find_nearest_static_tile_coords((0, 0), direction=0)
print(static_coord)
allocation_region_test = fpgaBoard.find_allocation_region((0, 0), 'S')
print(f"Allocation: {allocation_region_test}")
# print(fpgaBoard.calculate_region_resources( (80,3),static_coord))
# print(fpga_config["partition_size"])
# print(fpgaBoard.dimensions)
# print(f"Inner static {fpgaBoard.isCoordsInnerStatic((60,3))}")

# fpgaBoard.allocate_region((0,0),(71,1))

print(utils.generate_random_fpga_coord(15, 182, fpgaBoard))
count = 0
allocation_region_test = None

allocation_region_test = fpgaBoard.find_allocation_region((0, 2), 'S')
fpgaBoard.allocate_region(allocation_region_test[0], allocation_region_test[1])

for attempt in range(1):
  print(f'attempt number {attempt + 1}')
  allocation_region_test = fpgaBoard.find_allocation_region((30, 0), 'S')

  if (allocation_region_test is not None):
    break

if (allocation_region_test is not None):
  fpgaBoard.allocate_region(allocation_region_test[0], allocation_region_test[1])
utils.print_board(fpgaBoard)
print(fpgaBoard.matrix[2][59].partition)
print(fpgaBoard.matrix[2][59].static)