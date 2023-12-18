# @title Utils
from src import network,db
import matplotlib.pyplot as plt
from urllib.request import urlopen
from collections import Counter,defaultdict,OrderedDict
from pymongo import DESCENDING
import os
import json
import random
import numpy as np
import pandas as pd
from copy import copy,deepcopy


class AllocationError():

    def __init__(self):
        return




def generate_random_fpga_coord(fpgaMatrix):
    max_row = fpgaMatrix.height
    max_column = fpgaMatrix.width
    randx = random.randrange(max_column)
    randy = random.randrange(max_row)

    return (randx, randy)

def coord_diff(start_coord,end_coord):
    start_coord,end_coord = sort_coords(start_coord, end_coord)

    return end_coord[0]-start_coord[0]+1,end_coord[1]-start_coord[1]+1

def check_region_overlap(start1,end1,start2,end2):
    start_col1, start_row1 = start1 #l1
    start_col2, start_row2 = start2#l2
    end_col1, end_row1 = end1#r1
    end_col2, end_row2 = end2#r2

    if(start_col1 > end_col2 or end_col1 < start_col2 or start_row1 > end_row2 or end_row1 < start_row2):
        return False

    return True

def full_overlap_check(start_coords,end_coords,partitionInfo,StaticRegion):
    overlap = False
    l2, r2 = 0, 0
    start_column, start_row = start_coords
    end_column, end_row = end_coords

    if (start_column > end_column):
        start_column, end_column = end_column, start_column

    if (start_row > end_row):
        start_row, end_row = end_row, start_row

    for coords in partitionInfo.values():
        l2, r2 = coords['coords']
        overlap = check_region_overlap((start_column, start_row), (end_column, end_row), l2, r2)
        if (overlap):
            return True

    for coords in StaticRegion:
        l2, r2 = coords
        overlap = check_region_overlap((start_column, start_row), (end_column, end_row), l2, r2)
        if (overlap):
            return True

    return False


def generate_random_direction(directions):
    return random.randrange(len(directions))


def generate_random_size(sizes):
    return sizes[random.randrange(len(sizes))]


def circular_range(start, stop):
    return [i for i in range(start, stop)] + [i for i in range(start)]


def load_json_config_url(url):
    response = urlopen(url)
    config = json.loads(response.read())
    return config


def load_json_config_file(path):
    with open(path) as json_file:
        config = json.load(json_file)
        return config

def save_json_file(json_output,path):
    file_output = json.dumps(json_output, indent=4)
    with open(path,'w') as json_file:
        json_file.write(file_output)
    return



def save_current_topology_stats_to_csv(topology_collection,path,topology_filename,realloc_rate,resize_rate,elite,elapsed_time = None,run_counter =None, topology_id = None):
    aggregation_query = [
        {'$match': {}},
        {'$group':
            {'_id': '$generation','minScore': {'$min': '$topology_score'},'maxScore': {'$max': '$topology_score'},
             'nodes': {'$first': '$$ROOT.node_count'}, 'links': {'$first': '$$ROOT.link_count'},
             'avgScore': {'$avg': '$topology_score'},'population': {'$sum': 1}} },
        {
            '$addFields': {'avgScore': {'$round': ['$avgScore', 4]}},
            '$addFields': {'maxScore': {'$round': ['$maxScore', 4]}}},
        {'$sort': {'_id': 1}},
        {'$project': {'_id': 0,'generation': '$_id','minScore': 1,'maxScore': 1,'avgScore': 1,'population': 1,'nodes':1,'links':1}}
    ]

    result = list(topology_collection.aggregate(aggregation_query))
    header = ['nodes','links','generation','population','realloc_rate','resize_rate','elite','time','run','topology_id','maxScore']
    csv_path = os.path.join(path,topology_filename)
    stats_df = pd.DataFrame.from_records([result[-1]])
    stats_df['topology_id'] = topology_id
    stats_df['realloc_rate'] = realloc_rate
    stats_df['resize_rate'] = resize_rate
    stats_df['elite'] = elite
    stats_df['time'] = round(elapsed_time,4)
    stats_df['run'] = run_counter
    stats_df = stats_df[header]
    header = None if os.path.isfile(csv_path) else header
    stats_df.to_csv(csv_path, sep=';', decimal=',', header=header, index=False,mode='a')
    return result[-1]['maxScore']


def register_best_topology_from_run(topology_collection, log_collection,ga_args,run_number,generational_results):

    result = list(topology_collection.find({}).sort( [('topology_score',-1)]).limit(1) )
    best_topology = result[0]
    best_topology['topology_id'] = ga_args['topology_filename']
    best_topology['topology_score'] = round(best_topology['topology_score'],4)
    best_topology['resize_rate'] = ga_args['resize_rate']
    best_topology['elitep'] = ga_args['elitep']
    best_topology['population'] = ga_args['recreate']
    best_topology['run_number'] = run_number
    best_topology['generational_results'] = generational_results

    log_collection.insert_one(best_topology)
    return

def get_best_current_score(topology_collection):
    result = list(topology_collection.find({}).sort([('topology_score', -1)]).limit(1))
    best_topology = result[0]
    return round(best_topology['topology_score'],4)
def register_best_topology_from_agnostic_run(log_collection,ga_args,run_number,generational_results,gnostic_score,agnostic_topology,agnostic_score):

    #result = list(topology_collection.find({}).sort( [('topology_score',-1)]).limit(1) )
    #best_topology = result[0]
    #agnostic_topology = dict()
    for node,node_info in agnostic_topology['topology_data'].items():
        fpga_dict = dict()
        print(node_info['FPGA'])
        for key,fpga in node_info['FPGA'].items():
            fpga_dict[str(key)] = fpga.get_db_dict()

        agnostic_topology['topology_data'][node]['FPGA'] = fpga_dict

    agnostic_topology['agnostic'] = True
    agnostic_topology['topology_id'] = ga_args['topology_filename']
    agnostic_topology['topology_score'] = round(gnostic_score,4)
    agnostic_topology['agnostic_score'] = round(agnostic_score,4)
    agnostic_topology['resize_rate'] = ga_args['resize_rate']
    agnostic_topology['elitep'] = ga_args['elitep']
    agnostic_topology['population'] = ga_args['recreate']
    agnostic_topology['run_number'] = run_number
    agnostic_topology['generational_results'] = generational_results
    log_collection.insert_one(agnostic_topology)
    return

def extrapolate_atomic_run_to_full_topology(topology_collection,allocation_possibility,fpga_config,logger, ga_args):
    allocation_info_cursor = allocation_possibility.find()     #allocation_info é o dicionário que contém a informação se para uma coordenada e tamanho de partição,
    allocation_info = defaultdict(lambda: defaultdict(dict)) # a alocação é possível ou não
    temp_topology = topology_collection.find_one({},{"_id":0},sort = [("generation", DESCENDING),('topology_score',DESCENDING)])
    fpga_agnostic = None

    for node_id in range(10):
        try:
            fpga_agnostic = temp_topology['topology_data'][f'Nodo{node_id}']['FPGA']['0']
            break
        except KeyError:
            continue

    base_topology = load_topology(os.path.join(ga_args['topology_dir'], ga_args['topology_filename']))
    link_count = int(sum([len(network_node['Links']) for node_id, network_node in base_topology.items()])/2)
    topology_agnostic = network.create_agnostic_topology(base_topology,fpga_agnostic,fpga_config,logger,allocation_info)
    print(topology_agnostic['Nodo8'])
    topology_agnostic_temp = {'topology_data': copy(topology_agnostic)}
    print("copied")
    print(topology_agnostic_temp['topology_data']['Nodo8'])

    comp_filename = ga_args['topology_filename'] if ga_args['compare'] else None
    agnostic_score = network.evaluate_topology(topology_agnostic_temp, comp_filename)
    header = ['nodes','links','generation','population','realloc_rate','resize_rate','elite','maxScore']
    path = os.path.join(ga_args['log_dir'], 'topology_stats')

    csv_filename = F"agnostic_results_{ga_args['network_size']}.csv"
    csv_path = os.path.join(path,csv_filename)
    df = pd.DataFrame({'nodes': ga_args['network_size'], 'links': link_count,'generation': ga_args['iterations'],'population': ga_args['recreate'],
                    'realloc_rate': ga_args['realloc_rate'],'resize_rate': ga_args['resize_rate'],'elite': int(ga_args['elitep']*ga_args['recreate']), 'maxScore': agnostic_score},index=[0])
    header = None if os.path.isfile(csv_path) else header
    df.to_csv(csv_path, sep=';', decimal=',', header=header, index=False,mode='a')
    print("return")
    print(topology_agnostic_temp['topology_data']['Nodo8'])
    return agnostic_score,topology_agnostic_temp


def is_resource_count_sufficient(resources1, resources2):
    return (resources1['CLB'] >= resources2['CLB'] and resources1['DSP'] >= resources2['DSP'] and resources1['BRAM'] >=
            resources2['BRAM'])


def sort_coords(start_coords,end_coords):
    start_column, start_row = start_coords
    end_column, end_row = end_coords

    if (start_column > end_column):
        start_column, end_column = end_column, start_column

    if (start_row > end_row):
        start_row, end_row = end_row, start_row

    return [(start_column,start_row),(end_column,end_row)]

def get_edge_coords_region(start_coords,end_coords):
    return

def print_board(fpgaBoard, toFile=False, figloc='FpgaAllocation.png'):
    print_array = np.zeros([fpgaBoard.fpgaMatrix.height * 20, fpgaBoard.fpgaMatrix.width])
    for row_number, row_content in enumerate(fpgaBoard.getMatrix()):
        for column_number, tile in enumerate(row_content):
            for i in range(20):
                print_array[row_number * 20 + i][column_number] = ( tile.partition + 1) * 20 if tile.partition is not None else 0

    plt.matshow(print_array)
    if (toFile):
        plt.savefig(figloc)
    else:
        plt.show()


def load_topology(path):
    topology = load_json_config_file(path)
    fpga_topology = {}
    for entry in topology:
        nodo,data = list(entry.items())[0]
        fpga_topology[nodo] = {'Links': data['Links']}
        try:
            fpga_topology[nodo]['FPGA'] = data['FPGA'][0]
        except IndexError:
            fpga_topology[nodo]['FPGA'] = data['FPGA']

    return fpga_topology

def update_topology(topology,):
    return
