from src import utils,network,vsguerra
from src.fpgaBoard import FpgaBoard
from random import choices
from config import config
from pymongo import MongoClient,ReplaceOne,ASCENDING,DESCENDING
import json,os,re,csv
from collections import Counter,defaultdict,OrderedDict
from multiprocessing import Pool,Lock
from functools import partial
from tqdm import tqdm
from pathlib import Path
from time import time_ns,monotonic

config_dir = os.path.join(Path(__file__).parent.parent,'config')
log_dir = os.path.join(Path(__file__).parent.parent,'logs')
default_topologia_dir = os.path.join(Path(__file__).parent.parent, 'topology')

"""
POPSIZE: 100 - 500
ELITESIZEP - 0 - 0.25
REALLOC = 0.0 - 1.0
RESIZE = 0.0 - 1.0


"""

def get_best_of_last_generation(topology_collection):
    aggregation_query = [
        {'$match': {}},
        {'$group':
            {'_id': '$generation','minScore': {'$min': '$topology_score'},'maxScore': {'$max': '$topology_score'},
             'nodes': {'$first': '$$ROOT.node_count'}, 'links': {'$first': '$$ROOT.link_count'},
             'avgScore': {'$avg': '$topology_score'},'population': {'$sum': 1}} },
        {
            '$addFields': {'avgScore': {'$round': ['$avgScore', 4]}}},
        {'$sort': {'_id': 1}},
        {'$project': {'_id': 0,'generation': '$_id','minScore': 1,'maxScore': 1,'avgScore': 1,'population': 1,'nodes':1,'links':1}}
    ]

    result = list(topology_collection.aggregate(aggregation_query))
    last_generation = result[-1]
    return last_generation

def populate_allocation_possibility(args,allocation_possibility,fpga_config,logger):
    allocation_possibility.drop()
    fpgaBoard = FpgaBoard(fpga_config, logger)
    scan_coords = fpgaBoard.fpgaMatrix.create_matrix_loop((0, 0))
    queries = []

    total_len = len(scan_coords) * len(fpga_config['partition_size'].keys())
    # faz uma varredura em todas as coordenadas não estáticas e verifica se é possível alocar uma região para cada tamanho disponível. Armazena os resultados no banco de dados
    coord_pbar = tqdm(total=total_len, ascii=' #', bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}')
    coord_pbar.set_description('Coordenadas verificadas para alocação')
    for coord in scan_coords:
        for size in fpga_config['partition_size']:
            allocation_region,search_result = fpgaBoard.find_allocation_region(coord, size)
            allocation_info = {'modelo': 'G', 'row': coord[1], 'column': coord[0], 'size': size,
                               'possible': allocation_region is not None}
            coord_pbar.update(1)
            queries.append(
                ReplaceOne({'modelo': 'G', 'row': coord[1], 'column': coord[0], 'size': size}, allocation_info,
                           upsert=True))

    coord_pbar.close()
    logger.info("Atualizando banco de dados para possibilidade de alocações")
    allocation_possibility.bulk_write(queries)

def create_new_population(args,fpga_config,logger,topology_collection,allocation_possibility):
    topology_collection.drop()

    if(allocation_possibility is not None and allocation_possibility.count_documents({}) == 0):
        populate_allocation_possibility(args,allocation_possibility,fpga_config,logger)

    # formata entradas de allocation possiblity do banco de dados para uma estrutura em dict
    allocation_info_temp = list(allocation_possibility.find())
    allocation_info = defaultdict(lambda: defaultdict(dict))



    for entry in allocation_info_temp:
        allocation_info[(entry['column'], entry['row'])][entry['size']] = entry['possible']

    logger.info("Geração inicial de redes")
    if(args['agnostic']):
        topology = utils.load_topology(os.path.join(args['topology_dir'], 'agnostic_topology.json'))
    else:
        topology = utils.load_topology(os.path.join(args['topology_dir'], args['topology_filename']))

    topology_queries = []
    topology_quantity = args['recreate']
    recreate_pool = Pool(args['cpu'])
    topology_creation_func = partial(network.create_topology_db_from_json, topology, fpga_config, logger,
                                     dict(allocation_info))
    with tqdm(total=topology_quantity, desc='Geração de redes', bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}',
              ascii=' #', position=0) as topology_pbar:
        for result in recreate_pool.imap_unordered(topology_creation_func,
                                                   [topology_id for topology_id in range(topology_quantity)]):
            topology_queries.append(result)
            topology_pbar.update()

    recreate_pool.close()
    recreate_pool.join()
    logger.info("Atualizando banco de dados para primeira geração de topologias")
    topology_collection.bulk_write(topology_queries)

    return monotonic()

def run_ga_on_created_population(args,fpga_config,logger,topology_collection,allocation_possibility,max_time = None,run_number = None):
    allocation_info_cursor = allocation_possibility.find()  # allocation_info é o dicionário que contém a informação se para uma coordenada e tamanho de partição,
    allocation_info = defaultdict(lambda: defaultdict(dict))  # a alocação é possível ou não

    for entry in allocation_info_cursor:
        allocation_info[(entry['column'], entry['row'])][entry['size']] = entry['possible']

    logger.info("Iniciando algortimo genético")

    total_len = topology_collection.count_documents({'generation': args['start_generation']})
    elite_len = args['elite']

    if (args['elitep']):
        elite_len = int(total_len * args['elitep'])

    children_len = total_len - elite_len
    logger.info(f"Criando gerações {args['start_generation'] + 1} a {args['start_generation'] + args['iterations']}")

    pool = Pool(args['cpu'])

    t2 = monotonic()

    for generation in range(args['start_generation'], args['start_generation'] + args['iterations']):
        t3 = monotonic()
        if(max_time is not None and (t3 - t2) >= max_time):
            logger.info("Tempo esgotado para execução")
            break
        logger.info(f"Criando geração {generation + 1} de {args['start_generation'] + args['iterations']}")
        sizes = list(fpga_config['partition_size'].keys())
        topologia_cursor = topology_collection.find({'generation': generation}).sort([('topology_id', 1)])
        topologia_elite_cursor = topology_collection.find({'generation': generation}).sort(
            [('topology_score', -1)]).limit(elite_len)
        elite_indexes = [topology['topology_id'] for topology in topologia_elite_cursor]
        non_elite_indexes = []

        parent_topologias = list(topologia_cursor)
        topologies_index, topologies_scores = [], []
        topologies_choices = []
        for topology in parent_topologias:
            if (topology['topology_id'] not in elite_indexes):
                non_elite_indexes.append(topology['topology_id'])

            topologies_index.append(topology['topology_id'])
            topologies_scores.append(topology['topology_score'])

        logger.info(
            f"Elite igual a {elite_len}. Gerando redes para os {children_len} individuos restantes de {total_len}")

        topologies_choices = choices(topologies_index, weights=topologies_scores, k=2 * children_len)
        queries = []
        ga_args = []
        for i in range(0, len(topologies_choices), 2):
            p1, p2 = topologies_choices[i], topologies_choices[i + 1]
            pos = int(i / 2)
            child_id = non_elite_indexes[pos]
            ga_args.append((dict(parent_topologias[p1]), dict(parent_topologias[p2]), child_id, fpga_config, logger,
                            sizes, dict(allocation_info), args['realloc_rate'], args['resize_rate']))

        #pool = Pool(args['cpu'])
        with tqdm(total=children_len, desc="Gerando redes filhas", ascii=" *",
                  bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}') as pbar:
            for result in pool.imap_unordered(network.create_child_topology_db_unpacker, ga_args):
                queries.append(result)
                pbar.update()
        #pool.close()
        #pool.join()

        for elite_index in elite_indexes:
            elite_topology = parent_topologias[elite_index]
            elite_topology['generation'] += 1
            elite_topology.pop("_id", None)
            query = ReplaceOne(
                {'topology_id': elite_topology['topology_id'], 'generation': elite_topology['generation']},
                elite_topology, upsert=True)
            queries.append(query)

        logger.info(f"Atualizando banco de dados para geração {generation + 1}")
        topology_collection.bulk_write(queries)
        if(max_time is not None):
            csv_path = os.path.join(args['log_dir'], 'topology_stats')
            csv_filename = "timed_results.csv"
            maxScore = utils.save_current_topology_stats_to_csv(topology_collection, csv_path, csv_filename,
                                                                args['realloc_rate'], args['resize_rate'], elite_len, t3-t2,run_number)
        #write to timed_results.csv
        #must have an additional header_ execution number

    pool.close()
    if(args['agnostic'] == False):
        csv_path = os.path.join(args['log_dir'], 'topology_stats')
        # csv_filename = f"p{total_len}_{(args['topology_filename']).replace('.json','')}_realloc{int(args['realloc_rate']*100)}_res{int(args['resize_rate']*100)}_elite{elite_len}.csv"
        csv_filename = "results.csv"
        maxScore = utils.save_current_topology_stats_to_csv(topology_collection, csv_path, csv_filename, args['realloc_rate'], args['resize_rate'], elite_len, t3-t2,run_number)
        return maxScore

def run_ga_on_new_population(args,fpga_config,logger,topology_collection,allocation_possibility,max_time = None,run_number = None):
    t0 = monotonic()
    t1 = create_new_population(args, fpga_config, logger, topology_collection, allocation_possibility)
    ga_max_time = None if max_time is None else (max_time - (t1 - t0))
    best = run_ga_on_created_population(args, fpga_config, logger, topology_collection, allocation_possibility,ga_max_time,run_number)
    return best
