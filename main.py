from urllib.request import urlopen
import json,os
from collections import Counter,defaultdict
from pathlib import Path
from tqdm import tqdm
import random
from time import time_ns
from src import utils,network
from src.fpgaBoard import FpgaBoard
from config import config
from pymongo import MongoClient,ReplaceOne,ASCENDING,DESCENDING
import argparse
import logging
import re

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
node_id_regex =  re.compile('Nodo(\d+)', re.IGNORECASE)

DB_CONNECTION_STRING = "mongodb://localhost:27017"
DB_NAME = "tcc"

def get_database():
    client = MongoClient(DB_CONNECTION_STRING)
    return client[DB_NAME]

args = config.argparser()
logger = config.config_logger(args)

config_dir = os.path.join(Path(__file__).parent,'config')
log_dir = os.path.join(Path(__file__).parent,'logs')

fpga_config = config.load_fpga_config(config_dir, args.fpga_config_filename,args.partition_config_filename)
topology = utils.load_topology(os.path.join(config_dir,args.topology_filename))
topologias = []

tcc_db = get_database()
topology_collection = tcc_db['topology']
topology_fpga_info = tcc_db['fpga_info']
topology_link_info = tcc_db['link_info']
allocation_possibility = tcc_db['allocation_possibility']
region_resource_data = tcc_db['region_resource_data']

logger.info("start")

allocation_info_temp = allocation_possibility.find()
allocation_info = defaultdict(lambda: defaultdict(dict))
for entry in allocation_info_temp:
    allocation_info[(entry['column'],entry['row'])][entry['size']] = entry['possible']


queries = []
if(args.recreate):
    fpgaBoard = FpgaBoard(fpga_config,logger)
    scan_coords = fpgaBoard.fpgaMatrix.create_matrix_loop((0,0))
    queries = []
    total_len = len(scan_coords) * len(fpga_config['partition_size'].keys())
    count = 0

    #faz uma varredura em todas as coordenadas não estáticas e verifica se é possível alocar uma região para cada tamanho disponível. Armazena os resultados no banco de dados
    coord_pbar = tqdm(total = total_len,ascii = ' #',bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}')
    coord_pbar.set_description('Coordenadas verificadas para alocação')
    for coord in scan_coords:
        break
        for size in fpga_config['partition_size']:
            search_result = fpgaBoard.find_allocation_region(coord,size)
            allocation_info = {'modelo': 'G', 'row': coord[1], 'column': coord[0],'size':size,'possible': search_result is not None}
            coord_pbar.update(1)
            queries.append(ReplaceOne({'modelo': 'G', 'row': coord[1], 'column': coord[0],'size':size}, allocation_info, upsert=True))

    coord_pbar.close()
    logger.info("Atualizando banco de dados")
    #allocation_possibility.bulk_write(queries)

    #formata entradas de allocation possiblity do banco de dados para uma estrutura em dict
    allocation_info_temp = allocation_possibility.find()
    allocation_info = defaultdict(lambda: defaultdict(dict))
    for entry in allocation_info_temp:
        allocation_info[(entry['column'],entry['row'])][entry['size']] = entry['possible']

    logger.info("Geração inicial de redes")

    queries = []
    link_queries = []
    topology_queries = []
    topology_quantity = args.recreate

    with tqdm(total = topology_quantity,desc = 'Geração de redes',bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}',ascii = ' #',position = 0) as topology_pbar:
        for i in range( topology_quantity):
            topologia = {'topology_id': i, 'generation': 0,'topology_data': dict(),'topology_score': None}
            temp_topologia = {'topology_data': dict()}

            with tqdm(total = len(topology.keys()),desc = f'Geração de nodos topologia {i}',bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}',ascii = ' #',position = 1, leave=False) as node_pbar:
                for node_id,network_node in topology.items():

                    link_node = {'topology_id':i,'node_id': node_id,'Links': network_node['Links']}
                    topologia['topology_data'][node_id] = None
                    topologia['topology_data'][node_id] = {'FPGA': dict(),'Links': network_node['Links']}
                    temp_topologia['topology_data'][node_id] = None
                    temp_topologia['topology_data'][node_id] = {'FPGA': dict(),'Links': network_node['Links']}

                    link_queries.append( (ReplaceOne({'topology_id':i,'node_id': node_id},link_node,upsert=True)) )
                    len_fpgas = len(network_node['FPGA'])

                    if(len_fpgas > 0):
                        with tqdm(total = len(network_node['FPGA']) ,desc = f'Particionamento de fpga {node_id}',bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}',ascii = ' #',position=2, leave=False) as fpga_pbar:
                            for pos,fpga in enumerate(network_node['FPGA']):
                                #Cria FPGA zerado e faz uma alocação aleatória completa
                                fpgaBoard = FpgaBoard(fpga_config, logger)
                                fpgaBoard.full_board_allocation(list(fpga_config['partition_size'].keys()),allocation_info)

                                #Cria entrada para o banco de dados
                                db_node = {'topology_id':i,'node_id': node_id,'fpga_id': pos,'generation': 0 }
                                fpga_board_description = fpgaBoard.get_db_dict()
                                db_node.update(fpga_board_description)
                                topologia['topology_data'][node_id]['FPGA'][str(pos)] = fpga_board_description
                                queries.append(ReplaceOne({'topology_id':i,'node_id': node_id,'fpga_id': pos},db_node,upsert=True))
                                temp_topologia['topology_data'][node_id]['FPGA'][pos] = fpgaBoard
                                fpga_pbar.update()

                    node_pbar.update()

                topologia['topology_score'] = network.evaluate_topology(temp_topologia)
                topology_queries.append(ReplaceOne({'topology_id':i},topologia,upsert=True))
                topology_pbar.update()

    logger.info("Atualizando banco de dados")
    topology_collection.bulk_write(topology_queries)
    topology_fpga_info.bulk_write(queries)
    topology_link_info.bulk_write(link_queries)


else:
    allocation_info_temp = allocation_possibility.find()
    allocation_info = defaultdict(lambda: defaultdict(dict))

    for entry in allocation_info_temp:
        allocation_info[(entry['column'],entry['row'])][entry['size']] = entry['possible']

    logger.info("start")

    fpgas_cursor = topology_fpga_info.find().sort([('topology_id',1),('node_id', 1),('fpga_id', 1)])
    parent_fpgas = []
    for entry in fpgas_cursor:
        index = int(entry['topology_id'] /2)
        try:
            parent_fpgas[index].append(entry)
        except IndexError:
            parent_fpgas.append([])
            parent_fpgas[index] = [entry]


    links = list(topology_link_info.find({'topology_id':0}).sort([('topology_id',1),('node_id', 1)]))
    sizes = list(fpga_config['partition_size'].keys())

    with tqdm(total = len(parent_fpgas),desc="Creating children networks",ascii = " *",bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}') as network_pbar:
        for child_id,fpgas in enumerate(parent_fpgas):
            new_topology,partititon_topology = network.initialize_children_topology(fpgas,links,child_id,fpga_config,logger)
            new_topology['generation']+=1
            new_topology = network.populate_child_topology(new_topology,partititon_topology[0],partititon_topology[1],sizes,allocation_info,args.full_alloc_rate,args.resize_rate)
            new_topology['topology_score'] = network.evaluate_topology(new_topology)
            #network.save_topology_to_file(new_topology,f"topology_test{child_id}.json")
            network.save_topology_db(new_topology,topology_collection)
            network_pbar.update()

logger.info("end")
exit(0)








fpgaBoard = FpgaBoard(fpga_config,logger)
scan_coords = fpgaBoard.fpgaMatrix.create_matrix_loop((0,0))
queries = []
total_len = len(scan_coords) * len(fpga_config['partition_size'].keys())
count = 0
for coord in scan_coords:
    for size in fpga_config['partition_size']:
        search_result = fpgaBoard.find_allocation_region(coord,size)
        allocation_info = {'modelo': 'G', 'row': coord[1], 'column': coord[0],'size':size,'possible': search_result is not None}
        count+=1
        print(f"{count} of {total_len}")
        queries.append(ReplaceOne({'modelo': 'G', 'row': coord[1], 'column': coord[0],'size':size}, allocation_info, upsert=True))

allocation_possibility.bulk_write(queries)
exit(0)

for i in range(100):
    fpgaBoard = FpgaBoard(fpga_config,logger)
    fpgaBoard.full_board_allocation(list(fpga_config['partition_size'].keys()),allocation_info )
    partition_info = fpgaBoard.partitionInfo

logger.info("end")

exit(0)


