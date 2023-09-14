from urllib.request import urlopen
import json,os,re
from collections import Counter,defaultdict
from multiprocessing import Pool,Lock
from pathlib import Path
from tqdm import tqdm
from random import random,choices,shuffle
from hashlib import md5
from src import utils,network
from src.fpgaBoard import FpgaBoard
from config import config
from pymongo import MongoClient,ReplaceOne,ASCENDING,DESCENDING
import argparse
import logging
from functools import partial

fpga_config_url = 'https://raw.githubusercontent.com/akferreira/tcc_fpga_akferreira_1/main/fpga.json'
partition_config_url = 'https://raw.githubusercontent.com/akferreira/tcc_fpga_akferreira_1/main/partition.json'
fpga_config_filename = 'fpga.json'
partition_config_filename = 'partition.json'
fpga_topology_filename = 'topologia.json'
logfile_filename = 'run.log'
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



if __name__ == '__main__':
    logger.info("Iniciando")

    tcc_db = get_database()
    topology_collection = tcc_db['topology']
    allocation_possibility = tcc_db['allocation_possibility']



    if(args.export_topology):
        allocation_info_cursor = allocation_possibility.find()     #allocation_info é o dicionário que contém a informação se para uma coordenada e tamanho de partição,
        allocation_info = defaultdict(lambda: defaultdict(dict)) # a alocação é possível ou não

        for entry in allocation_info_cursor:
            allocation_info[(entry['column'],entry['row'])][entry['size']] = entry['possible']

        topology_db_print = topology_collection.find_one({'generation':130, 'topology_id':110})
        topology_print = network.create_topology_fpgaboard_from_db(topology_db_print,fpga_config,logger,allocation_info)
        utils.print_board(topology_print['Nodo0']['FPGA']['0'],toFile=True,figloc='testGeneration1.png')
        print(topology_print)



        exit(0)

    queries = []
    if(args.recreate):
        fpgaBoard = FpgaBoard(fpga_config,logger)
        scan_coords = fpgaBoard.fpgaMatrix.create_matrix_loop((0,0))
        queries = []
        total_len = len(scan_coords) * len(fpga_config['partition_size'].keys())

        topology_collection.drop()
        allocation_possibility.drop()


        #faz uma varredura em todas as coordenadas não estáticas e verifica se é possível alocar uma região para cada tamanho disponível. Armazena os resultados no banco de dados
        coord_pbar = tqdm(total = total_len,ascii = ' #',bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}')
        coord_pbar.set_description('Coordenadas verificadas para alocação')
        for coord in scan_coords:
            for size in fpga_config['partition_size']:
                search_result = fpgaBoard.find_allocation_region(coord,size)
                allocation_info = {'modelo': 'G', 'row': coord[1], 'column': coord[0],'size':size,'possible': search_result is not None}
                coord_pbar.update(1)
                queries.append(ReplaceOne({'modelo': 'G', 'row': coord[1], 'column': coord[0],'size':size}, allocation_info, upsert=True))

        coord_pbar.close()
        logger.info("Atualizando banco de dados para possibilidade de alocações")
        allocation_possibility.bulk_write(queries)

        #formata entradas de allocation possiblity do banco de dados para uma estrutura em dict
        allocation_info_temp = allocation_possibility.find()
        allocation_info = defaultdict(lambda: defaultdict(dict))
        for entry in allocation_info_temp:
            allocation_info[(entry['column'],entry['row'])][entry['size']] = entry['possible']



        logger.info("Geração inicial de redes")

        topology_queries = []
        topology_quantity = args.recreate
        recreate_pool = Pool(os.cpu_count() - 1)
        topology_creation_func = partial(network.create_topology_db_from_json,topology,fpga_config,logger,dict(allocation_info))
        with tqdm(total=topology_quantity, desc='Geração de redes', bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}',ascii=' #', position=0) as topology_pbar:
            for result in recreate_pool.imap_unordered(topology_creation_func,[topology_id for topology_id in range(topology_quantity)]):
                topology_queries.append(result)
                topology_pbar.update()


        recreate_pool.close()
        recreate_pool.join()
        logger.info("Atualizando banco de dados para primeira geração de topologias")
        topology_collection.bulk_write(topology_queries)

    else:
        allocation_info_cursor = allocation_possibility.find()     #allocation_info é o dicionário que contém a informação se para uma coordenada e tamanho de partição,
        allocation_info = defaultdict(lambda: defaultdict(dict)) # a alocação é possível ou não

        for entry in allocation_info_cursor:
            allocation_info[(entry['column'],entry['row'])][entry['size']] = entry['possible']

        logger.info("Iniciando algortimo genético")

        total_len =  topology_collection.count_documents({'generation': args.start_generation})
        elite_len = args.elite

        if(args.elitep):
            elite_len = total_len*args.elitep

        children_len = total_len-elite_len
        logger.info(f"Criando gerações {args.start_generation+1} a {args.start_generation+args.iterations}")

        for generation in range( args.start_generation, args.start_generation+args.iterations):
            logger.info(f"Criando geração {generation+1} de {args.start_generation+args.iterations}")
            sizes = list(fpga_config['partition_size'].keys())
            topologia_cursor = topology_collection.find({'generation': generation}).sort([('topology_id',1)])
            topologia_elite_cursor = topology_collection.find({'generation': generation}).sort([('topology_score',-1)]).limit(elite_len)
            elite_indexes = [topology['topology_id'] for topology in topologia_elite_cursor]
            non_elite_indexes = []

            parent_topologias = list(topologia_cursor)
            topologies_index,topologies_scores = [],[]
            topologies_choices = []
            for topology in parent_topologias:
                if(topology['topology_id'] not in elite_indexes):
                    non_elite_indexes.append(topology['topology_id'])

                topologies_index.append(topology['topology_id'])
                topologies_scores.append(topology['topology_score'])

            logger.info(f"Elite igual a {elite_len}. Gerando redes para os {children_len} individuos restantes de {total_len}")

            topologies_choices = choices(topologies_index,weights = topologies_scores, k = 2*children_len)
            queries = []
            ga_args = []
            for i in range(0, len(topologies_choices), 2):
                p1, p2 = topologies_choices[i], topologies_choices[i + 1]
                pos = int(i / 2)
                child_id = non_elite_indexes[pos]
                ga_args.append((dict(parent_topologias[p1]),dict(parent_topologias[p2]),child_id,fpga_config,logger,sizes,dict(allocation_info),args.full_alloc_rate,args.resize_rate))


            pool = Pool(args.cpu)
            with tqdm(total=children_len, desc="Gerando redes filhas", ascii=" *",bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}') as pbar:
                for result in pool.imap_unordered(network.create_child_topology_db_unpacker,ga_args):
                    queries.append(result)
                    pbar.update()
            pool.close()
            pool.join()

            for elite_index in elite_indexes:
                elite_topology = parent_topologias[elite_index]
                elite_topology['generation']+=1
                elite_topology.pop("_id",None)
                query = ReplaceOne({'topology_id':elite_topology['topology_id'],'generation': elite_topology['generation']},elite_topology,upsert=True)
                queries.append(query)

            logger.info(f"Atualizando banco de dados para geração {generation+1}")
            topology_collection.bulk_write(queries)

        logger.info("Fim")


