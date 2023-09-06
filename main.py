from urllib.request import urlopen
import json,os
from collections import Counter,defaultdict
from pathlib import Path
from tqdm import tqdm
import random
from time import time_ns
from src import utils
from src.fpgaBoard import FpgaBoard
from config import config
from pymongo import MongoClient,ReplaceOne,ASCENDING,DESCENDING
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

DB_CONNECTION_STRING = "mongodb://localhost:27017"
DB_NAME = "tcc"

def get_database():
    client = MongoClient(DB_CONNECTION_STRING)
    return client[DB_NAME]

def child_region_allocation(fpga,partitions_parent1, partitions_parent2):
    allocation_possible = True

    print(f'inicio {len(partitions_parent1)}.{len(partitions_parent2)}')

    while (allocation_possible):
        allocated_p1 = False
        allocated_p2 = False

        for partition in partitions_parent1:
            start_coords, end_coords = partition['coords']
            allocation_result_p1 = fpga.allocate_region(start_coords,end_coords,partition['resources'])
            if(allocation_result_p1 is not None):
                allocated_p1 = True
                partitions_parent1.remove(partition)
                break
        for partition in partitions_parent2:
            start_coords, end_coords = partition['coords']
            allocation_result_p2 = fpga.allocate_region(start_coords,end_coords,partition['resources'])
            if(allocation_result_p2 is not None):
                allocated_p1 = True
                partitions_parent2.remove(partition)
                break

        allocation_possible = allocated_p1 or allocated_p2

    print(f'final {len(partitions_parent1)}.{len(partitions_parent2)}')
    return fpga,partitions_parent1,partitions_parent2


args = config.argparser()
logger = config.config_logger(args)

config_dir = os.path.join(Path(__file__).parent,'config')
log_dir = os.path.join(Path(__file__).parent,'logs')


fpga_config = utils.load_json_config_file( os.path.join(config_dir,fpga_config_filename) )
fpga_config.update(utils.load_json_config_file( os.path.join(config_dir,partition_config_filename)))
topology = utils.load_topology(os.path.join(config_dir,fpga_topology_filename))
topologias = []

tcc_db = get_database()
collection_name = tcc_db['collection_test']
allocation_possibility = tcc_db['allocation_possibility']
region_resource_data = tcc_db['region_resource_data']



#fpgaBoard.full_board_allocation(sizes = list(fpga_config['partition_size'].keys()))
#fpgaBoard.get_complete_partition_resource_report()
#utils.print_board(fpgaBoard,toFile=True,figloc = args.fig_loc)
#fpgaBoard.save_allocated_to_file(args.fpga_data_loc)
allocation_info_temp = allocation_possibility.find()
allocation_info = defaultdict(lambda: defaultdict(dict))
for entry in allocation_info_temp:
    allocation_info[(entry['column'],entry['row'])][entry['size']] = entry['possible']

logger.info("start")




queries = []
if(args.recreate):
    for i in range(2):
        print(f"topologia {i}")
        topologia = {}
        for node_id,fpga_node in topology.items():
            topologia[node_id] = []
            #{'FPGA': [],'Links': fpga_node['Links']}
            print(node_id)
            for pos,fpga in enumerate(fpga_node['FPGA']):
                print(f"{pos=}")
                fpgaBoard = FpgaBoard(fpga_config, logger)
                fpgaBoard.full_board_allocation(list(fpga_config['partition_size'].keys()),allocation_info)
                db_node = {'topology_id':i,'node_id': node_id,'fpga_id': pos}
                db_node.update(fpgaBoard.get_db_dict())
                topologia[node_id].append(fpgaBoard)


                queries.append(ReplaceOne({'topology_id':i,'node_id': node_id,'fpga_id': pos},db_node,upsert=True))
                #collection_name.replace_one({'topology_id':i,'node_id': node_id,'fpga_id': pos},db_node,upsert=True)

        topologias.append(topologia)
    collection_name.bulk_write(queries)

else:
    topologias = defaultdict(lambda: defaultdict(dict))
    new_topologias = defaultdict(lambda: defaultdict(dict))
    partititon_topology = defaultdict(list)

    fpgas = collection_name.find().sort([('topology_id',1),('node_id', 1),('fpga_id', 1)])
    for fpga in fpgas:
        print(f"topology {fpga['topology_id']}.{fpga['node_id']}.fpga {fpga['fpga_id']}")
        #board = FpgaBoard(fpga_config,logger)
        for partition in fpga['partitions'].values():
            start_coords,end_coords = partition['coords']
            #board.allocate_region(start_coords,end_coords,partition['resources'])
            partititon_topology[fpga['topology_id']].append(partition)

        #topologias[ fpga['topology_id'] ][ fpga['node_id'] ][fpga['fpga_id']] = board
        new_topologias[fpga['topology_id']][fpga['node_id']][fpga['fpga_id']] = FpgaBoard(fpga_config,logger)

    for topology_id,topology in new_topologias.items():
        for node_id,node in topology.items():
            for fpga_id,fpga in node.items():
                #print(f'{topology_id}//{node_id}//{fpga_id}')
                new_topologias[topology_id][node_id][fpga_id], partititon_topology[0], partititon_topology[1] = child_region_allocation(new_topologias[topology_id][node_id][fpga_id],partititon_topology[0],partititon_topology[1])
                new_topologias[topology_id][node_id][fpga_id].full_board_allocation(list(fpga_config['partition_size'].keys()),allocation_info)
    fpga_test =  new_topologias[0]['Nodo7'][0]
    print(fpga_test.get_complete_partition_resource_report())

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

logger.info("start")



for i in range(10):
    fpgaBoard = FpgaBoard(fpga_config,logger)
    fpgaBoard.full_board_allocation(list(fpga_config['partition_size'].keys()),allocation_info )
    partition_info = fpgaBoard.partitionInfo

logger.info("end")

exit(0)