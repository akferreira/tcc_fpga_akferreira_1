from .fpgaTile import FpgaTile
from urllib.request import urlopen
import json
from collections import Counter,defaultdict
import random
from . import utils
from time import time_ns

RIGHT = 0
UP = 1
count = 0
success = 0
total = 0
part1 = 0
part2 = 0

class FpgaMatrix:
    def __init__(self,fpgaConfig,logger = None):
        self.logger = logger
        self.matrix = [[FpgaTile(resourceType,column,row,logger) for column,resourceType in enumerate(fpgaConfig['columns'])] for row in range(fpgaConfig['row_count'])]
        self.rowResourceInfo = fpgaConfig['row_resource_info']
        self.rowResources = []
        self.height = len(self.matrix)
        self.width = len(self.matrix[0])

        for row in self.matrix:
            self.rowResources.append([tile.resource for tile in row])

        
    def getAllTiles(self):
        tiles = []
        for row in self.matrix:
            for column in row:
                tiles.append(column)
        return tiles

    def get_tile_range_from_row(self,row, column_range):
        return self.matrix[row][ column_range[0]:column_range[1]+1 ]
    def get_tile_range_from_column(self,row_range,column):
        return self.matrix[row_range[0]:row_range[1]+1][column]

    def getTile(self, coordinate):
        return self.matrix[coordinate[1]][coordinate[0]]


    def exclude_tiles_from_coords(self,coords,excludeAllocated = True):
        filtered_coords = []

        filtered_coords = [coord for coord in coords if excludeAllocated == False or self.getTile(coord).partition is None]
        return filtered_coords

        for coord in coords:
            tile = self.getTile(coord)

            if(excludeAllocated == True and tile.isAvailableForAllocation() == False):
                continue
            filtered_coords.append(coord)


        return filtered_coords


    def create_matrix_loop(self, start_coords, direction=RIGHT,excludeAllocated = True):
        '''
        Gera uma matriz de coordenadas a partir da matriz do fpga, percorrendo o fpga ou horizontalmente da esquerda para direita
        ou verticalmente de baixo para cima.
         RIGHT = 0, UP = 1
        '''
        start_column, start_row = start_coords
        head, tail, body = [], [], []
        if (direction == RIGHT):
            for row in utils.circular_range(start_row, self.height):
                if (row == start_row):
                    tail = [(x, row) for x in range(start_column)]
                    head = [(x, row) for x in range(start_column, self.width)]
                else:
                    body.extend([(x, row) for x in range(self.width)])

        else:
            for column in utils.circular_range(start_column, self.width):
                if (column == start_column):
                    tail = [(column, y) for y in range(start_row)]
                    head = [(column, y) for y in range(start_row, self.height)]
                else:
                    body.extend([(column, y) for y in range(self.height)])

        head.extend(body)
        head.extend(tail)
        coord_loop = self.exclude_tiles_from_coords(head,excludeAllocated)
        return coord_loop


    def isCoordsInnerStatic(self,coords):
        print(coords)
        if (self.getTile(coords).static == False):
            return False

        coord_column, coord_row, = coords
        adjacent_coords = [(coord_column + 1, coord_row), (coord_column - 1, coord_row), (coord_column, coord_row + 1),
                           (coord_column, coord_row - 1)]

        for column, row in adjacent_coords:
            try:
                if (self.getTile((column, row)).static == False):
                    return False
            except IndexError:
                continue

        return True


    def isCoordsEdgeStatic(self, coords):
        if (self.getTile(coords).static == False):
            return False


        coord_column, coord_row, = coords
        adjacent_coords = [(coord_column + 1, coord_row), (coord_column - 1, coord_row), (coord_column, coord_row + 1),
                           (coord_column, coord_row - 1)]
        for column, row in adjacent_coords:
            try:
                if (self.getTile((column, row)).static == False):
                    return True
            except IndexError:
                continue

        return False


    def isCoordsEdgeBoard(self, coords):
        coord_column, coord_row, = coords

        if (coord_column == 0 or coord_row == 0):
            return True

        adjacent_coords = [(coord_column + 1, coord_row), (coord_column - 1, coord_row), (coord_column, coord_row + 1),
                           (coord_column, coord_row - 1)]

        for column, row in adjacent_coords:
            try:
                self.getTile((column, row))
            except IndexError:
                return True

        return False


    def is_region_border_static(self, start_coords, end_coords,StaticRegion = []):
        MINIMUM_COUNT = 2
        start_column, start_row = start_coords
        end_column, end_row = end_coords

        if (start_column > end_column):
            start_column, end_column = end_column, start_column

        if (start_row > end_row):
            start_row, end_row = end_row, start_row

        overlap = False
        for coords in StaticRegion:
            l2, r2 = coords
            overlap = utils.check_region_overlap((start_column-1,start_row-1),(end_column+1,end_row+1),l2,r2)
            if(overlap):
                return True
        return False

    def calculate_region_resources(self, start_coords,end_coords,partitionInfo = {},StaticRegion = []):  # A função só deve retornar um valor válido se a região dada não pega de duas ou mais regiões
        '''
        Calcula a quantidade de recursos em uma dada região retangular.
        Entrada: start_coords -> coordenadas do canto superior esquerdo do retângulo
        end_coords -> coordenadas do canto inferior direito do retângulo
        '''

        overlap = False
        l2,r2 = 0,0
        start_column, start_row = start_coords
        end_column, end_row = end_coords


        #resourceCounter = Counter()
        resourceCount = {'CLB': 0,'BRAM':0, 'IO':0, 'DSP': 0}

        for row in range(start_row, end_row + 1):
            #resourceCounter += Counter(self.rowResources[row][start_column:end_column+1])
            for resource in self.rowResources[row][start_column:end_column+1]:
                resourceCount[resource]+=1

        for resource in resourceCount:
            resourceCount[resource] *= self.rowResourceInfo[resource]


        return resourceCount
        return resourceCounter

    def get_all_edge_static_coords(self,coords,direction = RIGHT):
        scan_coords_temp = self.create_matrix_loop(coords,direction,excludeAllocated = False)
        scan_coords = [coord for coord in scan_coords_temp if self.isCoordsEdgeStatic(coord) == True]
        return scan_coords

    def get_all_edge_board_coords(self,coords,direction):
        scan_coords_temp = self.create_matrix_loop(coords,direction)
        scan_coords = [coord for coord in scan_coords_temp if self.isCoordsEdgeBoard(coord) == True]
        return scan_coords

    def get_partition_coords(self,partition):
        return

    def get_free_resource_count(self):
        return

    def check_region_overlap(self,start1,end1,start2,end2):
        start_col1, start_row1 = start1
        start_col2, start_row2 = start2
        end_col1, end_row1 = end1
        end_col2, end_row2 = end2

        return (not (start_col1 >= end_col2 or end_col1 <= start_col2 or start_row1 >= end_row2 or end_row1 <= start_row2))

    def get_single_partition_resource_report(self,partition):
        partition_tiles = [tile for tile in self.getAllTiles() if tile.partition == partition]
        return

    def get_complete_partition_resource_report(self):
        tiles = [tile for tile in self.getAllTiles() if tile.partition is not None]
        partitions = {}

        for tile in tiles:
            try:
                partitions[tile.partition].append(tile)
            except KeyError:
                partitions[tile.partition] = [tile]

        for partition in partitions.values():
            upperleft_tile = partition[0]
            bottomright_tile = partition[-1]
            upperleft_coords = (upperleft_tile.column,upperleft_tile.row)
            bottomright_coords = (bottomright_tile.column, bottomright_tile.row)
            print(f'{upperleft_tile.partition}: {self.calculate_region_resources(upperleft_coords,bottomright_coords)}')



        return
    

