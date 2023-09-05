import argparse
import logging


def argparser():
    parser = argparse.ArgumentParser(prog='Fpga automated partition tool')
    parser.add_argument('-d','--debug',action='store_true')
    parser.add_argument('-s', '--silent', action='store_true')
    parser.add_argument('--recreate', action='store_true')
    parser.add_argument('--fpga-config-loc',dest= 'fpga_config_filename',default = 'fpga.json')
    parser.add_argument('--partition-config-loc',dest = 'partition_config_filename',default = 'partition.json')
    parser.add_argument('--log-loc',dest='log_loc',default = 'log.json')
    parser.add_argument('--fig-loc', dest='fig_loc',default = 'FpgaAllocation.png')
    parser.add_argument('--topologia-loc', dest='top_loc',default='topologia.json')
    parser.add_argument('--fpga-data-loc',dest='fpga_data_loc', default='fpga_data.json')
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
    else:
      logger.setLevel(logging.INFO)
    return logger