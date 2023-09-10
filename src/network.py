from src import utils
from src.fpgaBoard import FpgaBoard
from src import vsguerra
from collections import defaultdict
from random import shuffle,random
import json,os


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

def initialize_children_topology(fpgas,links, child_id,fpga_config,logger):
    """
    Entrada :
    links -> lista dos links de cada nodo de cada topologia
    """
    child_topology = defaultdict(lambda: defaultdict(dict))
    partititon_topology = defaultdict(list)
    child_topology['topology_id'] = child_id

    for link in links:
        topology_id = link['topology_id']
        node_id = link['node_id']

        #Cria um nodo na topologia filha com os links do nodo correspondente na topologia pai
        if(topology_id == 0):
            child_topology['topology_data'][node_id]['Links'] = link['Links']
            child_topology['topology_data'][node_id]['FPGA'] = {}


    for fpga in fpgas:
        topology_id = fpga['topology_id']
        node_id = fpga['node_id']
        fpga_id = fpga['fpga_id']

        child_topology['generation'] = fpga['generation']
        child_topology['topology_score'] = None

        for partition in fpga['partitions'].values():
            start_coords,end_coords = partition['coords']
            partititon_topology[topology_id%2].append(partition)

        if(topology_id  % 2):
            child_topology['topology_data'][node_id]['FPGA'][fpga_id]  = FpgaBoard(fpga_config,logger)

    return child_topology,partititon_topology

def populate_child_topology(topology,partititon_p1,partititon_p2,sizes,allocation_info,full_aloc_rate,resize_rate):
    for node_id,node in topology['topology_data'].items():
        if ('FPGA' in node):
            for fpga_id,fpga in node['FPGA'].items():
                topology['topology_data'][node_id]['FPGA'][fpga_id], partititon_p1, partititon_p2 = child_region_allocation(fpga,partititon_p1,partititon_p2)
                if(random() <= full_aloc_rate):
                    topology['topology_data'][node_id]['FPGA'][fpga_id].full_board_allocation(sizes[:],allocation_info)
                if(random() <= resize_rate):
                    topology['topology_data'][node_id]['FPGA'][fpga_id].full_board_resize()

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

    json_output = json.dumps(output, indent=4)
    utils.save_json_file(json_output,path)
    return

def save_topology_db(topology,topology_collection):
    db_topology = defaultdict(lambda: defaultdict(dict))
    for node_id,node in topology['topology_data'].items():
        db_topology['topology_data'][node_id]['FPGA'] = dict()
        for fpga_id,fpga in node['FPGA'].items():
            if(fpga):
                db_topology['topology_data'][node_id]['FPGA'][str(fpga_id)] = fpga.get_db_dict()
                db_topology['topology_data'][node_id]['Links'] = topology['topology_data'][node_id]['Links']

    db_topology['topology_id'] = topology['topology_id']

    db_topology['generation'] = topology['generation']
    db_topology['topology_score'] = topology['topology_score']
    topology_collection.replace_one({'topology_id':topology['topology_id']},db_topology,upsert=True)

def evaluate_topology(topology):
    runs = 100
    req = 50
    nodos_G = len(topology['topology_data'].keys())
    req_qtd = 0
    lista_requisicoes = [ vsguerra.ler_Requisicoes(vsguerra.gerador_Req(nodos_G,req,topology)) for i in range(runs)]



    for requisao in lista_requisicoes:
        lista_Paths,lista_Nodos= vsguerra.ler_Topologia(topology)
        resultado = vsguerra.greedy(requisao,lista_Paths,lista_Nodos)
        req_qtd += resultado[0]

    #topology['topology_score'] = req_qtd/(req*runs)

    return req_qtd/(req*runs)
