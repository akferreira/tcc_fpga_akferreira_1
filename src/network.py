from src import utils,db
from src.fpgaBoard import FpgaBoard
from src import vsguerra
from multiprocessing import Lock
from pymongo import MongoClient,ReplaceOne,ASCENDING,DESCENDING
from collections import defaultdict
from random import shuffle,random
import json,os
from tqdm import tqdm
from copy import deepcopy

tcc_db = db.get_database(MongoClient)
request_info = tcc_db['requests_info']


def child_region_allocation(fpga,partitions_parent1, partitions_parent2):
    allocation_possible = True

    loop_partitions_parent1 = partitions_parent1[:]
    loop_partitions_parent2 = partitions_parent2[:]
    shuffle(partitions_parent1)
    shuffle(partitions_parent2)

    while (allocation_possible):
        allocated_p1 = False
        allocated_p2 = False


        #varredura nas partições da topologia do pai 1 até achar uma partição que possa ser alocada
        for partition in loop_partitions_parent1:
            start_coords, end_coords = partition['coords']
            allocation_result_p1 = fpga.allocate_region(start_coords,end_coords,partition['resources'])
            loop_partitions_parent1.remove(partition)
            if(allocation_result_p1 is not None):
                allocated_p1 = True
                partitions_parent1.remove(partition)
                break

        #varredura nas partições da topologia do pai 2 até achar uma partição que possa ser alocada
        for partition in loop_partitions_parent2:
            start_coords, end_coords = partition['coords']
            allocation_result_p2 = fpga.allocate_region(start_coords,end_coords,partition['resources'])

            loop_partitions_parent2.remove(partition)
            if(allocation_result_p2 is not None):
                allocated_p1 = True
                partitions_parent2.remove(partition)
                break

        allocation_possible = allocated_p1 or allocated_p2

    #print(f'final {len(partitions_parent1)}.{len(partitions_parent2)}')
    return fpga,partitions_parent1,partitions_parent2

def initialize_child_topology(topology_p1,topology_p2,child_id,fpga_config,logger,req_topology_filename):
    child_topology = defaultdict(lambda: defaultdict(dict))
    partititons_parents = [[],[]]

    child_topology['topology_id'] = child_id
    child_topology['topology_score'] = None
    child_topology['filename'] = req_topology_filename
    child_topology['generation'] = topology_p1['generation']+1
    child_topology['node_count'] = topology_p1['node_count']
    child_topology['link_count'] = topology_p1['link_count']

    for node_id,node in topology_p1['topology_data'].items():
        child_topology['topology_data'][node_id] = {'FPGA': dict(), 'Links': node['Links']}

        for fpga_id,fpga in node['FPGA'].items():
            child_topology['topology_data'][node_id]['FPGA'][fpga_id] = FpgaBoard(fpga_config,logger)

            for partition in fpga['partitions'].values():
                partititons_parents[0].append(partition)

    for node_id,node in topology_p2['topology_data'].items():
        for fpga_id,fpga in node['FPGA'].items():
            for partition in fpga['partitions'].values():
                partititons_parents[1].append(partition)

    return child_topology,partititons_parents
def populate_child_topology(topology,partititon_p1,partititon_p2,sizes,allocation_info,full_aloc_rate,resize_rate):
    for node_id,node in topology['topology_data'].items():
        if ('FPGA' in node):
            for fpga_id,fpga in node['FPGA'].items():
                topology['topology_data'][node_id]['FPGA'][fpga_id], partititon_p1, partititon_p2 = child_region_allocation(fpga,partititon_p1,partititon_p2)
                if(random() <= full_aloc_rate):
                    topology['topology_data'][node_id]['FPGA'][fpga_id].full_board_allocation(sizes[:],allocation_info)
                if(random() <= resize_rate):
                    topology['topology_data'][node_id]['FPGA'][fpga_id].full_board_resize(200,1,10)

        else:
            topology[node_id]['FPGA'] = []

    return topology

def save_topology_to_file(topology,path):
    output = {}

    for node_id,node in topology['topology_data'].items():
        output[node_id] = {'FPGA':[],'Links': node['Links']}
        for fpga in node['FPGA'].values():
            if(fpga):
                output[node_id]['FPGA'].append(fpga.get_complete_partition_resource_report() )

    utils.save_json_file(output,path)
    return

def save_topology_db(topology,topology_collection):
    db_topology = defaultdict(lambda: defaultdict(dict))
    for node_id,node in topology['topology_data'].items():
        db_topology['topology_data'][node_id]['FPGA'] = dict()
        db_topology['topology_data'][node_id]['Links'] = topology['topology_data'][node_id]['Links']

        for fpga_id,fpga in node['FPGA'].items():
            if(fpga):
                db_topology['topology_data'][node_id]['FPGA'][str(fpga_id)] = fpga.get_db_dict()

    db_topology['topology_id'] = topology['topology_id']

    db_topology['generation'] = topology['generation']
    db_topology['topology_score'] = topology['topology_score']
    topology_collection.replace_one({'topology_id':topology['topology_id'],'generation': db_topology['generation']},db_topology,upsert=True)

def create_request_list(topology,nodos_G,runs = 30):
    req = int(nodos_G * 1.5 * 4.5)
    req_qtd = 0
    lista_requisicoes = [vsguerra.ler_Requisicoes(vsguerra.gerador_Req(nodos_G, req, topology)) for i in range(runs)]
    return lista_requisicoes
def evaluate_topology(topology,topology_filename = None):
    nodos_G = len(topology['topology_data'].keys())
    fpga_count = 0
    for node_id,node in topology['topology_data'].items():
        fpga_count += len(node['FPGA'])

    runs = 30
    req_per_run = int(fpga_count * 4.5)
    req_qtd = 0

    if(topology_filename is None):
        print("no comparison")
        lista_requisicoes = [ vsguerra.ler_Requisicoes(vsguerra.gerador_Req(nodos_G,req_per_run,topology)) for i in range(runs)]

    else:
        #print(f"não é none: {topology_filename}")
        request_entry = request_info.find_one({'topology_filename' : topology_filename})
        runs = len(request_entry['requests'])
        req_per_run = len(request_entry['requests'][0])
        #print(f"{runs=}..{req_per_run=}")

        lista_requisicoes = []
        for req_sublist in request_entry['requests']:
            lista_req_temp = []

            for request in req_sublist:
                req = vsguerra.Req(**request)
                functions = request['func']
                req.func = [vsguerra.Function(function['name_func'],function['name_imp'],function['clb'],function['bram'],function['dsp']) for function in functions]
                lista_req_temp.append(req)

            lista_requisicoes.append(lista_req_temp)



    for requisao in lista_requisicoes:
        #print(requisao)
        lista_Paths,lista_Nodos= vsguerra.ler_Topologia(topology)
        resultado = vsguerra.greedy(requisao,lista_Paths,lista_Nodos)
        req_qtd += resultado[0]
        #print(resultado)

    #topology['topology_score'] = req_qtd/(req*runs)

    return req_qtd/(req_per_run*runs)

def format_topology_db(topology):
    db_topology = defaultdict(lambda: defaultdict(dict))

    for node_id,node in topology['topology_data'].items():
        db_topology['topology_data'][node_id]['FPGA'] = dict()
        db_topology['topology_data'][node_id]['Links'] = topology['topology_data'][node_id]['Links']

        for fpga_id,fpga in node['FPGA'].items():
            if(fpga):
                db_topology['topology_data'][node_id]['FPGA'][str(fpga_id)] = fpga.get_db_dict()

    db_topology['topology_id'] = topology['topology_id']
    db_topology['node_count'] = topology['node_count']
    db_topology['link_count'] = topology['link_count']
    db_topology['generation'] = topology['generation']
    db_topology['topology_score'] = topology['topology_score']
    return db_topology

def create_child_topology(topology_p1,topology_p2,child_id,fpga_config,logger,sizes,allocation_info,realloc_rate,resize_rate,req_topology_filename):
    child_topology,partititon_topology = initialize_child_topology(topology_p1,topology_p2,child_id,fpga_config,logger,req_topology_filename)
    child_topology = populate_child_topology(child_topology,partititon_topology[0],partititon_topology[1],sizes,allocation_info,realloc_rate,resize_rate)
    child_topology['topology_score'] = evaluate_topology(child_topology,req_topology_filename)
    child_topology['filename'] = req_topology_filename

    return child_topology

def create_child_topology_db_unpacker(args):
    topology_p1, topology_p2, child_id, fpga_config, logger, sizes, allocation_info, realloc_rate, resize_rate,req_topology_filename = args
    return create_child_topology_db(topology_p1,topology_p2,child_id,fpga_config,logger,sizes,allocation_info,realloc_rate,resize_rate,req_topology_filename)


def create_child_topology_db(topology_p1,topology_p2,child_id,fpga_config,logger,sizes,allocation_info,realloc_rate,resize_rate,req_topology_filename):
    #print("hello")
    child_topology =  create_child_topology(topology_p1,topology_p2,child_id,fpga_config,logger,sizes,allocation_info,realloc_rate,resize_rate,req_topology_filename)
    child_topology_db = format_topology_db(child_topology)
    child_topology_db['filename'] = req_topology_filename
    #print("goodbye")

    return ReplaceOne({'topology_id':child_topology_db['topology_id'],'generation': child_topology_db['generation']},dict(child_topology_db),upsert=True)



def create_topology_db_from_json(json_topology,fpga_config,logger,allocation_info,topology_id,return_db_op = True, req_topology_filename = None):
    topologia = {'topology_id': topology_id, 'generation': 0, 'node_count' : len(json_topology),'link_count': None,'topology_data': dict(), 'topology_score': None,'filename': req_topology_filename}
    temp_topologia = {'topology_data': dict()} #para calculo de fitness
    link_count = 0
    for node_id, network_node in json_topology.items():
        topologia['topology_data'][node_id] = None
        topologia['topology_data'][node_id] = {'FPGA': dict(), 'Links': network_node['Links']}
        temp_topologia['topology_data'][node_id] = None
        temp_topologia['topology_data'][node_id] = {'FPGA': dict(), 'Links': network_node['Links']}
        link_count += len(network_node['Links'])

        len_fpgas = len(network_node['FPGA'])

        if (len_fpgas > 0):
            for pos, fpga in enumerate(network_node['FPGA']):
                # Cria FPGA zerado e faz uma alocação aleatória completa
                fpgaBoard = FpgaBoard(fpga_config, logger)
                fpgaBoard.full_board_allocation(list(fpga_config['partition_size'].keys()), allocation_info)

                # Cria entrada para o banco de dados
                fpga_board_description = fpgaBoard.get_db_dict()
                topologia['topology_data'][node_id]['FPGA'][str(pos)] = fpga_board_description
                temp_topologia['topology_data'][node_id]['FPGA'][pos] = fpgaBoard

    topologia['topology_score'] = evaluate_topology(temp_topologia,req_topology_filename)
    topologia['link_count'] = int(link_count/2)
    if(return_db_op):
        return ReplaceOne({'topology_id': topology_id, 'generation': 0}, topologia, upsert=True)
    else:
        return topologia

def create_topology_fpgaboard_from_db(db_topology,fpga_config,logger,allocation_info):
    topologia = {}
    for node_id, network_node in db_topology['topology_data'].items():
        topologia[node_id] = None
        topologia[node_id] = {'FPGA': dict(), 'Links': network_node['Links']}

        len_fpgas = len(network_node['FPGA'])

        if (len_fpgas > 0):
            for pos, fpga in network_node['FPGA'].items():
                # Cria FPGA zerado e faz uma alocação aleatória completa
                fpgaBoard = FpgaBoard(fpga_config, logger)

                for partition in fpga['partitions'].values():
                    start_coords, end_coords = partition['coords']
                    fpgaBoard.allocate_region(start_coords, end_coords, partition['resources'])

                topologia[node_id]['FPGA'][pos] = fpgaBoard

    return topologia

def create_agnostic_topology(topology,agnostic_fpga,fpga_config,logger,allocation_info):
    topologia = {}
    for node_id, network_node in topology.items():
        topologia[node_id] = None
        topologia[node_id] = {'FPGA': dict(), 'Links': network_node['Links']}
        for pos, empty_fpga in enumerate(network_node['FPGA']):
            # Cria FPGA zerado e faz uma alocação aleatória completa
            fpgaBoard = FpgaBoard(fpga_config, logger)

            for partition in agnostic_fpga['partitions'].values():
                start_coords, end_coords = partition['coords']
                fpgaBoard.allocate_region(start_coords, end_coords, partition['resources'])

            topologia[node_id]['FPGA'][pos] = fpgaBoard



    return topologia


def export_topology_to_files(topology):
    return
