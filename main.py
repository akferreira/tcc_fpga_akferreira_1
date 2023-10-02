from urllib.request import urlopen
import json,os,re,csv
from collections import Counter,defaultdict,OrderedDict
from multiprocessing import Pool,Lock
from pathlib import Path
from tqdm import tqdm
from random import random,choices,shuffle,randrange
import pandas as pd
from src import utils,network,vsguerra,ga
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


topologias = []



if __name__ == '__main__':
    logger.info("Iniciando")

    tcc_db = get_database()
    topology_collection = tcc_db['topology']
    allocation_possibility = tcc_db['allocation_possibility']
    resource_info = tcc_db['resource_info']


    if(args.generate_base_topologies):
        topology_per_node_count = 20
        node_range = [i for i in range(10,41,5)]
        link_range = [(node_count*1.2,node_count*1.3) for node_count in node_range]

        for node_count,link_interval in zip(node_range,link_range):
            i = 0
            while(i < topology_per_node_count):
                for link_count in range(int(link_interval[0]), int(link_interval[1]+1)):
                    if(i >= topology_per_node_count):
                        break

                    base_topology_dir = os.path.join(args.topology_dir,f"topology_N{node_count}_{i}.json")
                    base_topology = vsguerra.gerador_Topologia(node_count,link_count)
                    utils.save_json_file(base_topology,base_topology_dir)
                    i+=1

        exit(0)

    elif(args.testing):
        POPSIZES = [100,125,150,175,200,225,250,275,300,325,350,375,400,425,450,475,500]
        GENERATIONS = [10,10,20,20,40,40,50,50,60,70,80,90]
        ELITE_SIZES = [0.1,0.2]
        REALLOC_LIST = [i/10 for i in range(10)]
        RESIZE_LIST = [i/10 for i in range(10)]
        ga_args = vars(args)

        for i in range(900):
            ga_args['realloc_rate'] = choices(REALLOC_LIST)[0]
            ga_args['resize_rate'] = choices(RESIZE_LIST)[0]
            ga_args['elitep'] = choices(ELITE_SIZES)[0]
            ga_args['recreate'] = choices(POPSIZES)[0]
            ga_args['iterations'] = choices(GENERATIONS)[0]
            ga_args['topology_filename'] = f"topology_N10_{randrange(100)%20}.json"
            logger.info(f"Teste número {i} .. {ga_args}")
            ga.run_ga_on_new_population(ga_args, fpga_config, logger, topology_collection, allocation_possibility)

        exit(0)




    elif(args.export_topology):
        allocation_info_cursor = allocation_possibility.find()     #allocation_info é o dicionário que contém a informação se para uma coordenada e tamanho de partição,
        allocation_info = defaultdict(lambda: defaultdict(dict)) # a alocação é possível ou não

        for entry in allocation_info_cursor:
            allocation_info[(entry['column'],entry['row'])][entry['size']] = entry['possible']

        topology_db_print = topology_collection.find_one({'generation':30, 'topology_id':110})
        topology_print = network.create_topology_fpgaboard_from_db(topology_db_print,fpga_config,logger,allocation_info)
        utils.print_board(topology_print['Nodo1']['FPGA']['0'],toFile=True,figloc='testGeneration1.png')
        print(topology_print)


    elif(args.recreate):
        ga.create_new_population( vars(args),fpga_config,logger,topology_collection,allocation_possibility)
        exit(0)

    elif(args.ga):
        best = ga.run_ga_on_created_population(vars(args),fpga_config,logger,topology_collection,allocation_possibility)
        exit(0)
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
                ga_args.append((dict(parent_topologias[p1]),dict(parent_topologias[p2]),child_id,fpga_config,logger,sizes,dict(allocation_info),args.realloc_rate,args.resize_rate))


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

        csv_path = os.path.join(args.log_dir,'topology_stats')
        #csv_filename = f"p{total_len}_{(args.topology_filename).replace('.json','')}_realloc{int(args.realloc_rate*100)}_res{int(args.resize_rate*100)}_elite{elite_len}.csv"
        csv_filename = "results.csv"
        utils.save_current_topology_stats_to_csv(topology_collection,csv_path,csv_filename,args.realloc_rate,args.resize_rate,elite_len)

        logger.info("Fim")
        exit(0)
    else:
        board = FpgaBoard(fpga_config, logger)
        allocation_info_cursor = allocation_possibility.find()  # allocation_info é o dicionário que contém a informação se para uma coordenada e tamanho de partição,
        allocation_info = defaultdict(lambda: defaultdict(dict))  # a alocação é possível ou não
        board.full_board_allocation(list(fpga_config['partition_size'].keys()), allocation_info)
        logger.info("end")
        utils.print_board(board,toFile = True)

        #resource_info.replace_one({'modelo' : 'G'},precalc_resources,upsert=True)


