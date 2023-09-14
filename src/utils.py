# @title Utils
import matplotlib.pyplot as plt
from urllib.request import urlopen
from hashlib import md5
import json
import random
import numpy as np


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
    with open(path,'w') as json_file:
        json_file.write(json_output)
    return


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
