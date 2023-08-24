from .fpgaTile import FpgaTile
from urllib.request import urlopen
import json
from collections import Counter,defaultdict
import random
from . import utils

RIGHT = 0
UP = 1


class FpgaMatrix:
    def __init__(self,fpgaConfig,logger = None):
        self.logger = None
        self.matrix = [[FpgaTile(resourceType,column,row,logger) for column,resourceType in enumerate(fpgaConfig['columns'])] for row in range(fpgaConfig['row_count'])]
        self.rowResourceInfo = fpgaConfig['row_resource_info']
        self.height = len(self.matrix)
        self.width = len(self.matrix[0])
        
    def getAllTiles(self):
        tiles = []
        for row in self.matrix:
            for column in row:
                tiles.append(column)
        return tiles

    def getTile(self, coordinate):
        return self.matrix[coordinate[1]][coordinate[0]]

    def create_matrix_loop(self, start_coords, direction=RIGHT,excludeStatic = False,excludeAllocated = True):
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
        coord_loop = [coords for coords in head if
                      (excludeStatic == False or self.getTile(coords).static == False) and
                      (excludeAllocated == False or self.getTile(coords).partition is None)
                      ]
        return [coords for coords in head if(excludeStatic == False or self.getTile(coords).static == False)]


    def isCoordsInnerStatic(self, coords):
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


    def is_region_border_static(self, start_coords, end_coords):
        MINIMUM_COUNT = 2
        start_column, start_row = start_coords
        end_column, end_row = end_coords

        if (start_column > end_column):
            start_column, end_column = end_column, start_column

        if (start_row > end_row):
            start_row, end_row = end_row, start_row

        for row in range(start_row, end_row + 1):
            for column in range(start_column, end_column + 1):
                adjacent_coords = [(column + 1, row), (column - 1, row), (column, row + 1), (column, row - 1)]
                for adjacent_coord in adjacent_coords:
                    try:
                        if (self.isCoordsEdgeStatic(adjacent_coord) == True):
                            return True
                    except IndexError:
                        continue

        return False

    def calculate_region_resources(self, start_coords,end_coords):  # A função só deve retornar um valor válido se a região dada não pega de duas ou mais regiões
        '''
        Calcula a quantidade de recursos em uma dada região retangular.
        Entrada: start_coords -> coordenadas do canto superior esquerdo do retângulo
        end_coords -> coordenadas do canto inferior direito do retângulo
        '''
        start_column, start_row = start_coords
        end_column, end_row = end_coords

        try:
            self.getTile(start_coords)
            self.getTile(end_coords)

        except IndexError as Error:
            logger.error(f"Cannot calculate resources for region {start_coords}::{end_coords}. Out of bounds")
            return

        if (start_column > end_column):
            start_column, end_column = end_column, start_column

        if (start_row > end_row):
            start_row, end_row = end_row, start_row

        resourceCount = {'BRAM': 0,'CLB': 0, 'DSP': 0, 'IO': 0}
        currentPartition = self.getTile(start_coords).partition

        for row in range(start_row, end_row + 1):
            for column in range(start_column, end_column + 1):

                if (self.getTile((column, row)).partition != currentPartition):
                    return

                resource = self.getTile((column, row)).resource
                resourceCount[resource] += self.rowResourceInfo[resource]

        return resourceCount

    def get_all_edge_static_coords(self,coords,direction):
        scan_coords_temp = self.create_matrix_loop(coords,direction)
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
    

