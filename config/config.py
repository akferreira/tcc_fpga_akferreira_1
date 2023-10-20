import argparse
import logging
import os
from src import utils
from pathlib import Path
from functools import partial, partialmethod

def argparser():
    parser = argparse.ArgumentParser(description='Fpga automated partition tool')
    parser.add_argument('-d','--debug',action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-s', '--silent', action='store_true')

    ga_parser = parser.add_argument_group('Parâmetros de configuração do algoritmo genético')
    ga_parser.add_argument('--recreate', action='store',type=int, help = 'Quantidade de indivíduos a serem criados para a geração inicial', metavar='[0-1000]')
    ga_parser.add_argument('--ga',action='store_true',help = 'Roda o algoritmo genético sobre a população criada previamente')
    ga_parser.add_argument('--start-generation', action='store',type=int,default = 0, help = 'Geração dos pais a partir da qual se iniciará o algoritmo genético')
    ga_parser.add_argument('--iterations', action='store', type=int, default=10, help = 'Quantidade de gerações a serem criadas', metavar=f"[0-999]")
    ga_parser.add_argument('--elite', action='store',dest= 'elite',type=int,default = 20, help = 'Tamanho inteiro da elite da população', metavar='[0-100]')
    ga_parser.add_argument('--elitep', action='store',dest= 'elitep',type=float,default = None, help = 'Tamanho percentual da elite da população', metavar='[0-1]')
    ga_parser.add_argument('--realloc-rate', type=float, default = 0.35, help = 'Probabilidade de executar nova alocação aleatória nos filhos', metavar = '[0-1]')
    ga_parser.add_argument('--resize-rate',dest='resize_rate',type=float, default = 0.8, metavar = '[0-1]', help = 'Probabilidade de redimensionar as partições dos filhos')
    ga_parser.add_argument('--cpu',type=int,default = os.cpu_count()-1)
    ga_parser.add_argument('--testing',action='store_true')
    ga_parser.add_argument('--agnostic',action='store_true')

    default_config_dir = os.path.join(Path(__file__).parent.parent, 'config')
    default_log_dir = os.path.join(Path(__file__).parent.parent, 'logs')
    default_topologia_dir = os.path.join(Path(__file__).parent.parent, 'topology')

    file_parser =  parser.add_argument_group('Parâmetros de configuração de arquivos de entrada e saída')
    file_parser.add_argument('--fpga-config-loc',dest= 'fpga_config_filename',default = 'fpga.json')
    file_parser.add_argument('--partition-config-loc',dest = 'partition_config_filename',default = 'partition.json')
    file_parser.add_argument('--log-loc',dest='log_loc',default = 'log.json')
    file_parser.add_argument('--fig-loc', dest='fig_loc',default = 'FpgaAllocation.png')
    file_parser.add_argument('--topology-filename', dest='topology_filename',default='topologia.json')
    file_parser.add_argument('--fpga-data-loc',dest='fpga_data_loc', default='fpga_data.json')
    file_parser.add_argument('--export-topology', action='store_true')
    file_parser.add_argument('--generate-base-topologies', action='store_true')
    file_parser.add_argument('--log-dir', default = default_log_dir)
    file_parser.add_argument('--topology-dir', default = default_topologia_dir)



    args = parser.parse_args()

    return args

def load_fpga_config(config_dir,fpga_config_filename,partition_config_filename):
    fpga_config_location = os.path.join(config_dir,fpga_config_filename)
    partition_config_location = os.path.join(config_dir,partition_config_filename)

    fpga_config = utils.load_json_config_file(fpga_config_location)
    fpga_config.update(utils.load_json_config_file(partition_config_location))

    return fpga_config

def validate_parser_args(args):
    return


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
