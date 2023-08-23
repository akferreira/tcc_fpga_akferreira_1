from urllib.request import urlopen
import json,os
from collections import Counter,defaultdict
from pathlib import Path
import random
from src import utils
from src.fpgaBoard import FpgaBoard
import argparse
import logging

fpga_config_url = 'https://raw.githubusercontent.com/akferreira/tcc_fpga_akferreira_1/main/fpga.json'
partition_config_url = 'https://raw.githubusercontent.com/akferreira/tcc_fpga_akferreira_1/main/partition.json'
fpga_config_filename = 'fpga.json'
partition_config_filename = 'partition.json'
coord_X = 0
coord_Y = 1
matrix_line = 0
matrix_column = 1
logger = None

def config_argparser():
  parser = argparse.ArgumentParser(prog='Fpga automated partition tool')
  parser.add_argument('-d','--debug',action='store_true')
  parser.add_argument('-s', '--silent', action='store_true')
  args = parser.parse_args()
  return args

def config_logger(args):
  logger = logging.getLogger('fpgaLogger')
  handler = logging.StreamHandler()
  formatter = logging.Formatter('%(asctime)s :: %(levelname)-8s :: %(message)s',"%Y-%m-%d %H:%M:%S")
  handler.setFormatter(formatter)
  logger.addHandler(handler)
  if(args.debug == True):
    print("debug\n")
    logger.setLevel(logging.DEBUG)
  elif(args.silent == True):
    logger.setLevel(logging.ERROR)
  return logger


args = config_argparser()
logger = config_logger(args)

parent_dir = Path(__file__).parent.parent
fpga_config = utils.load_json_config_file( os.path.join(parent_dir,fpga_config_filename) )
fpga_config.update(utils.load_json_config_file( os.path.join(parent_dir,partition_config_filename)))
fpgaBoard = FpgaBoard(fpga_config,logger)

random_coords =  utils.generate_random_fpga_coord(15, 182, fpgaBoard)
allocation_coords = fpgaBoard.fpgaMatrix.create_matrix_loop(random_coords,excludeStatic = True)
logger.info(len(allocation_coords))
for i,coords in enumerate(allocation_coords):
  logger.debug(f'Attempt number {i} at {coords}')
  allocation_region_test = fpgaBoard.find_allocation_region(coords, 'S')
  if(allocation_region_test is not None):
    break


if (allocation_region_test is not None):
  fpgaBoard.allocate_region(allocation_region_test[0], allocation_region_test[1])


utils.print_board(fpgaBoard)
fpgaBoard.fpgaMatrix.get_complete_partition_resource_report()
exit(0)