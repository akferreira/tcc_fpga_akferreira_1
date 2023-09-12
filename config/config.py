import argparse
import logging
import os
from src import utils
from functools import partial, partialmethod

def argparser():
    parser = argparse.ArgumentParser(prog='Fpga automated partition tool')
    parser.add_argument('-d','--debug',action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-s', '--silent', action='store_true')
    parser.add_argument('--recreate', action='store',type=int)
    parser.add_argument('--start-generation', action='store',type=int,default = 0)
    parser.add_argument('--iterations', action='store', type=int, default=10)
    parser.add_argument('--elite', action='store',dest= 'elite_len',type=int,default = 0)
    parser.add_argument('--fpga-config-loc',dest= 'fpga_config_filename',default = 'fpga.json')
    parser.add_argument('--partition-config-loc',dest = 'partition_config_filename',default = 'partition.json')
    parser.add_argument('--log-loc',dest='log_loc',default = 'log.json')
    parser.add_argument('--fig-loc', dest='fig_loc',default = 'FpgaAllocation.png')
    parser.add_argument('--topologia-loc', dest='topology_filename',default='topologia.json')
    parser.add_argument('--fpga-data-loc',dest='fpga_data_loc', default='fpga_data.json')
    parser.add_argument('--full-alloc-rate', dest='full_alloc_rate', type=float, default = 0.25)
    parser.add_argument('--resize_rate',dest='resize_rate',type=float, default = 0.8)
    args = parser.parse_args()
    return args

def load_fpga_config(config_dir,fpga_config_filename,partition_config_filename):
    fpga_config_location = os.path.join(config_dir,fpga_config_filename)
    partition_config_location = os.path.join(config_dir,partition_config_filename)

    fpga_config = utils.load_json_config_file(fpga_config_location)
    fpga_config.update(utils.load_json_config_file(partition_config_location))

    return fpga_config




def config_logger(args):
    logger = logging.getLogger('fpgaLogger')
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s :: %(levelname)-8s :: %(message)s',"%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logging.VERBOSE = logging.INFO - 5
    logging.addLevelName(logging.VERBOSE, 'VERBOSE')
    logging.Logger.verbose = partialmethod(logging.Logger.log, logging.VERBOSE)
    logging.verbose = partial(logging.log, logging.VERBOSE)

    if(args.debug == True):
      logger.setLevel(logging.DEBUG)
    elif(args.verbose == True):
      logger.setLevel(logging.VERBOSE)
    elif(args.silent == True):
      logger.setLevel(logging.ERROR)
    else:
      logger.setLevel(logging.INFO)
    return logger
