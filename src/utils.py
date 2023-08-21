# @title Utils
import matplotlib.pyplot as plt
from urllib.request import urlopen
import json
import random
import numpy as np




class AllocationError():

    def __init__(self):
        return


def generate_random_fpga_coord(max_row, max_column, fpgaBoard):
    randx = random.randrange(max_column)
    randy = random.randrange(max_row)

    return (randx, randy)


def circular_range(start, stop):
    return [i for i in range(start, stop)] + [i for i in range(start)]


def load_json_config_url(url):
    response = urlopen(url)
    config = json.loads(response.read())
    return config

def load_json_config_file(path):
    print(path)
    with open(path) as json_file:
        config = json.load(json_file)
        return config


def is_resource_count_sufficient(resources1, resources2):
    return (resources1['CLB'] >= resources2['CLB'] and resources1['DSP'] >= resources2['DSP'] and resources1['BRAM'] >= resources2['BRAM'])

def sortCoords(coord1,coord2):
    return
          



def print_board(fpgaBoard):
    print_array = np.zeros([fpgaBoard.dimensions[0] * 20, fpgaBoard.dimensions[1]])
    for row_number, row_content in enumerate(fpgaBoard.matrix):
        for column_number, tile in enumerate(row_content):
            for i in range(20):
                print_array[row_number * 20 + i][column_number] = (tile.partition + 1) * 20 if tile.partition is not None else 0

    plt.matshow(print_array)
    plt.show()




