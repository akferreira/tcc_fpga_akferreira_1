# @title FpgaBoard.py
from urllib.request import urlopen
import json
from collections import Counter,defaultdict
import random

from . import utils
from .fpgaTile import FpgaTile

RIGHT = 0
UP = 1

class FpgaBoard():
  def __init__(self,fpga_config):
    self.dimensions = [0,0]
    self.rowResourceInfo = defaultdict(int)
    self.partitionCount = 0
    self.resourceCount = {'BRAM': 0,'CLB': 0, 'DSP': 0, 'IO': 0}
    self.config = fpga_config
    self.load_config(fpga_config)

  def get_tile(self,coordinate):
    return self.matrix[coordinate[1]][coordinate[0]]

  @property
  def matrix(self):
    return self._matrix

  @matrix.setter
  def matrix(self,newMatrix):
    self._matrix = newMatrix
    self.dimensions = [len(newMatrix),len(newMatrix[0])]

    for row in newMatrix:
      for column in row:
        self.inc_resource(column.resource)


  def load_config(self,fpga_config):
    self.rowResourceInfo = fpga_config['row_resource_info']
    self.matrix = [[FpgaTile(resourceType,fpga_config['row_count']) for resourceType in fpga_config['columns']] for row in range(fpga_config['row_count'])] #repete a lista de colunas "linhas" vezes, criando uma
    self.set_static_region(fpga_config['static_region']['coords'])                                                                               #matriz de dimensõeslinha x coluna
    self.partitionCount+=1
    return

  def inc_resource(self,resource):
    if(self.rowResourceInfo is None):
      print(f"ERRO: RowResourceInfo não setado \n")
      return

    self.resourceCount[resource]+= self.rowResourceInfo[resource]

  def isCoordsInnerStatic(self,coords):
    if(self.get_tile(coords).static == False):
      return False

    coord_column,coord_row, = coords
    adjacent_coords = [(coord_column+1,coord_row),(coord_column-1,coord_row),(coord_column,coord_row+1),(coord_column,coord_row-1)]

    for coord_X,coord_Y in adjacent_coords:
      try:
        if(self.matrix[coord_Y][coord_X].static == False):
            return False
      except IndexError:
        continue

    return True


  def isCoordsEdgeStatic(self,coords):
    if(self.get_tile(coords).static == False):
      return False

    coord_column,coord_row, = coords
    adjacent_coords = [(coord_column+1,coord_row),(coord_column-1,coord_row),(coord_column,coord_row+1),(coord_column,coord_row-1)]
    for coord_X,coord_Y in adjacent_coords:
      try:
        if(self.matrix[coord_Y][coord_X].static == False):
            return True
      except IndexError:
        continue

    return False

  def isCoordsEdgeBoard(self,coords):
    coord_column,coord_row, = coords
    
    if(coord_column == 0 or coord_row == 0):
      return True

    adjacent_coords = [(coord_column + 1, coord_row), (coord_column - 1, coord_row), (coord_column, coord_row + 1),(coord_column, coord_row - 1)]

    for coord_X,coord_Y in adjacent_coords:
      try:
        self.matrix[coord_Y][coord_X]
      except IndexError:
        return True

    return False

  def is_region_border_static(self,start_coords, end_coords):
    start_column, start_row = start_coords
    end_column, end_row = end_coords

    if(start_column > end_column):
      start_column,end_column = end_column,start_column

    if(start_row > end_row):
      start_row,end_row = end_row,start_row

    for row in range(start_row, end_row + 1):
      for column in range(start_column, end_column + 1):
        adjacent_coords = [(column + 1, row), (column - 1, row), (column, row + 1), (column, row - 1)]
        for adjacent_coord in adjacent_coords:
          try:
            if(self.isCoordsEdgeStatic(adjacent_coord) == True):
              return True
          except IndexError:
            continue
            
    return False

  def calculate_region_resources(self,start_coords,end_coords): #A função só deve retornar um valor válido se a região dada não pega de duas ou mais regiões
    '''
    Calcula a quantidade de recursos em uma dada região retangular.
    Entrada: start_coords -> coordenadas do canto superior esquerdo do retângulo
    end_coords -> coordenadas do canto inferior direito do retângulo
    '''
    start_column,start_row = start_coords
    end_column,end_row = end_coords

    try:
      self.get_tile(start_coords)
      self.get_tile(end_coords)

    except IndexError as Error:
      print(f"Coordinates out of bounds!")
      return

    if(start_column > end_column): 
      start_column,end_column = end_column,start_column

    if(start_row > end_row):
      start_row,end_row = end_row,start_row

    resourceCount = defaultdict(int)
    currentPartition = self.get_tile(start_coords).partition

    for row in range(start_row,end_row+1):
      for column in range(start_column,end_column+1):

        if(self.matrix[row][column].partition != currentPartition):
          return
          if (self.isCoordsEdgeStatic((column, row)) == True):
            continue
          else:
            return

        resource = self.matrix[row][column].resource
        resourceCount[resource] += self.rowResourceInfo[resource]

    return resourceCount

  def set_static_region(self,static_subcoords):
    '''
    Recebe uma lista de coordenadas que demarcam retangulos e marca todos os blocos compreendidos dentro
    desses retângulos como pertencentes a região estática do fpga
    '''

    if self.matrix is None:
      print(f"ERRO: Mapa do fpga não setado \n")
      return

    for static_coords in static_subcoords:
      upper_left,bottom_right = static_coords
      print(static_coords)
      for column in range(upper_left[0],bottom_right[0]+1):
        for line in range(upper_left[1],bottom_right[1]):
          self.matrix[line][column].static = True

    return

  def create_matrix_loop(self,start_coords,direction = RIGHT):
    '''
    Gera uma matriz de coordenadas a partir da matriz do fpga, percorrendo o fpga ou horizontalmente da esquerda para direita
    ou verticalmente de baixo para cima.
     RIGHT = 0, UP = 1
    '''
    start_column,start_row = start_coords
    head,tail,body = [],[],[]
    if(direction == RIGHT):
      for row in utils.circular_range(start_row,self.dimensions[0]):
        if(row == start_row):
          tail = [(x,row) for x in range(start_column)]
          head = [(x,row) for x in range(start_column,self.dimensions[1])]
        else:
          body.extend([(x,row) for x in range(self.dimensions[1])])

    else:
      for column in utils.circular_range(start_column,self.dimensions[1]):
        if(column == start_column):
          tail = [(column,y) for y in range(start_row)]
          head = [(column,y) for y in range(start_row,self.dimensions[0])]
        else:
          body.extend([(column,y) for y in range(self.dimensions[0])])

    head.extend(body)
    head.extend(tail)
    return head



  def get_all_edge_static_coords(self,coords,direction):
    scan_coords_temp = self.create_matrix_loop(coords,direction)
    scan_coords = [coord for coord in scan_coords_temp if self.isCoordsEdgeStatic(coord) == True]
    return scan_coords

  def get_all_edge_board_coords(self,coords,direction):
    scan_coords_temp = self.create_matrix_loop(coords,direction)
    scan_coords = [coord for coord in scan_coords_temp if self.isCoordsEdgeBoard(coord) == True]
    return scan_coords


  def find_nearest_static_tile_coords(self,coords,direction = RIGHT):
    '''
    Busca o bloco da região estática mais próximo da coordenada dada. Recebe também como parâmetro em que direção essa busca será feita
    RIGHT = 0, UP = 1
    '''
    if(self.get_tile(coords).static ==  True):
      print(f"{coords} belong to a static region")
      return

    scan_coords_temp = self.create_matrix_loop(coords,direction)
    scan_coords = [coord for coord in scan_coords_temp if self.isCoordsInnerStatic(coord) == False]

    for current_coord in scan_coords:
        if(self.matrix[current_coord[1]][current_coord[0]].static == True and current_coord != coords):
          return current_coord

    return

  def find_allocation_region(self, start_coord, size, direction=RIGHT,logger = None):

    if (self.get_tile(start_coord).isAvailableForAllocation() == False):
      print(f"Can't allocate for {start_coord}")
      return
    
    size_info = self.config['partition_size'][size]
    print("start")
    scan_coords = self.get_all_edge_static_coords(start_coord, direction) + self.get_all_edge_board_coords(start_coord,direction)
    scan_coords = self.create_matrix_loop(start_coord,direction)
    scan_coords = [coords for coords in scan_coords if self.get_tile(coords).static == False]

    for current_static_coord in scan_coords:
      if (current_static_coord is None):
        print(f"Can't allocate for {start_coord}")
        return

      if(current_static_coord == (159,13)):
        print("aa")

      current_resource_count = self.calculate_region_resources(start_coord, current_static_coord)

      if (current_static_coord == (159, 13)):
        print(current_resource_count)

      if (current_resource_count is not None):
        if (current_static_coord == (159, 13)):
          print(f'{current_resource_count} ||| {current_static_coord} = {utils.is_resource_count_sufficient(current_resource_count,size_info)}. static border = {self.is_region_border_static(start_coord,current_static_coord)}')
        if (utils.is_resource_count_sufficient(current_resource_count,size_info) and self.is_region_border_static(start_coord,current_static_coord)):
          print(f"Succesfully found an available region with {current_resource_count} at {start_coord} to {current_static_coord}")
          return [start_coord, current_static_coord]

    print("end")
    return None
  
  
  

  def allocate_region(self,start_coords,end_coords):
    start_column,start_row = start_coords
    end_column,end_row = end_coords

    if(start_column > end_column):
      start_column,end_column = end_column,start_column
      print("ha")
      #start_column+=1
      #end_column+=1


    if(start_row > end_row):
      start_row,end_row = end_row,start_row
      print("hey")
      #start_row+=1
      #end_row+=1

    print(f"allocating from {start_column},{start_row} to {end_column},{end_row}")

    for column in range(start_column,end_column+1):
      for row in range(start_row,end_row+1):
        if(self.matrix[row][column].isAvailableForAllocation() == False):
          print(f'Unavailable tile found in region at {column}.{row}. Aborting partition {self.partitionCount} allocation')
          return
    
    for column in range(start_column,end_column+1):
      for row in range(start_row,end_row+1):
        if(self.matrix[row][column].static == False):
          self.matrix[row][column].partition = self.partitionCount


    self.partitionCount+=1


