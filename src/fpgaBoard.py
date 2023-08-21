# @title FpgaBoard.py
from urllib.request import urlopen
import json
from collections import Counter,defaultdict
import random

from . import utils
from .fpgaTile import FpgaTile
from .fpgaMatrix import FpgaMatrix

RIGHT = 0
UP = 1

class FpgaBoard():
  def __init__(self,fpgaConfig):
    self.dimensions = [0,0]
    self.rowResourceInfo = defaultdict(int)
    self.partitionCount = 0
    self.resourceCount = {'BRAM': 0,'CLB': 0, 'DSP': 0, 'IO': 0}
    self.config = fpgaConfig
    self.load_config(fpgaConfig)

  def getTile(self,coordinates):
    return self.fpgaMatrix.getTile(coordinates)

  def getMatrix(self):
    return self.fpgaMatrix.matrix

  @property
  def fpgaMatrix(self):
    return self._matrix

  @fpgaMatrix.setter
  def fpgaMatrix(self,newMatrix):
    self._matrix = newMatrix
    self.dimensions = [newMatrix.height,newMatrix.width]

    for row in newMatrix.matrix:
      for column in row:
        self.inc_resource(column.resource)


  def load_config(self,fpgaConfig):
    self.rowResourceInfo = fpgaConfig['row_resource_info']
    self.fpgaMatrix = FpgaMatrix(fpgaConfig)
    self.set_static_region(fpgaConfig['static_region']['coords'])
    self.partitionCount+=1
    return

  def inc_resource(self,resource):
    if(self.rowResourceInfo is None):
      print(f"ERRO: RowResourceInfo não setado \n")
      return

    self.resourceCount[resource]+= self.rowResourceInfo[resource]

  def set_static_region(self, static_subcoords):
    '''
    Recebe uma lista de coordenadas que demarcam retangulos e marca todos os blocos compreendidos dentro
    desses retângulos como pertencentes a região estática do fpga
    '''
    for static_coords in static_subcoords:
      upper_left, bottom_right = static_coords
      print(static_coords)
      for column in range(upper_left[0], bottom_right[0] + 1):
        for line in range(upper_left[1], bottom_right[1]):
          self.getTile((column, line)).static = True

    return

##
  def find_allocation_region(self, start_coord, size, direction=RIGHT,logger = None):

    if (self.getTile(start_coord).isAvailableForAllocation() == False):
      print(f"Can't allocate for {start_coord}")
      return
    
    size_info = self.config['partition_size'][size]
    scan_coords = self.fpgaMatrix.create_matrix_loop(start_coord,direction)
    scan_coords = [coords for coords in scan_coords if self.getTile(coords).static == False]

    for current_static_coord in scan_coords:
      if (current_static_coord is None):
        print(f"Can't allocate for {start_coord}")
        return

      current_resource_count = self.fpgaMatrix.calculate_region_resources(start_coord, current_static_coord)

      if (current_resource_count is not None):
          #print(f'{current_resource_count} ||| {current_static_coord} = {utils.is_resource_count_sufficient(current_resource_count,size_info)}. static border = {self.is_region_border_static(start_coord,current_static_coord)}')
        if (utils.is_resource_count_sufficient(current_resource_count,size_info) and self.fpgaMatrix.is_region_border_static(start_coord,current_static_coord)):
          print(f"Succesfully found an available region with {current_resource_count} at {start_coord} to {current_static_coord}")
          return [start_coord, current_static_coord]


    return None
  
  
  
##
  def allocate_region(self,start_coords,end_coords):
    start_column,start_row = start_coords
    end_column,end_row = end_coords

    if(start_column > end_column):
      start_column,end_column = end_column,start_column
        
    if(start_row > end_row):
      start_row,end_row = end_row,start_row

    print(f"allocating from {start_column},{start_row} to {end_column},{end_row}")

    for column in range(start_column,end_column+1):
      for row in range(start_row,end_row+1):
        if(self.getTile((column,row)).isAvailableForAllocation() == False):
          print(f'Unavailable tile found in region at {column}.{row}. Aborting partition {self.partitionCount} allocation')
          return
    
    for column in range(start_column,end_column+1):
      for row in range(start_row,end_row+1):
        if(self.getTile((column,row)).static == False):
          self.getTile((column,row)).partition = self.partitionCount


    self.partitionCount+=1


