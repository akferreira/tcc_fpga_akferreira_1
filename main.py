from urllib.request import urlopen
import json,os
from collections import Counter,defaultdict
from pathlib import Path
from tqdm import tqdm
import random
from src import utils
from src.fpgaBoard import FpgaBoard
from config import config
import argparse
import logging

fpga_config_url = 'https://raw.githubusercontent.com/akferreira/tcc_fpga_akferreira_1/main/fpga.json'
partition_config_url = 'https://raw.githubusercontent.com/akferreira/tcc_fpga_akferreira_1/main/partition.json'
fpga_config_filename = 'fpga.json'
partition_config_filename = 'partition.json'
fpga_topology_filename = 'topologia.json'
logfile_filename = 'run.log'
coord_X = 0
coord_Y = 1
matrix_line = 0
matrix_column = 1


args = config.argparser()
logger = config.config_logger(args)

config_dir = os.path.join(Path(__file__).parent,'config')
log_dir = os.path.join(Path(__file__).parent,'logs')


fpga_config = utils.load_json_config_file( os.path.join(config_dir,fpga_config_filename) )
fpga_config.update(utils.load_json_config_file( os.path.join(config_dir,partition_config_filename)))
topology = utils.load_topology(os.path.join(config_dir,fpga_topology_filename))
fpgaBoard = FpgaBoard(fpga_config,logger)


fpgaBoard.full_board_allocation(sizes = list(fpga_config['partition_size'].keys()))
fpgaBoard.get_complete_partition_resource_report()
utils.print_board(fpgaBoard,toFile=True,figloc = args.fig_loc)
fpgaBoard.save_allocated_to_file(args.fpga_data_loc)
exit(0)
