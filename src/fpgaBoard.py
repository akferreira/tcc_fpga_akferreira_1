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
  def __init__(self,fpgaConfig,logger = None):
    self.dimensions = [0,0]
    self.rowResourceInfo = dict()
    self.partitionCount = 0
    self.resourceCount = {'BRAM': 0,'CLB': 0, 'DSP': 0, 'IO': 0}
    self.config = fpgaConfig
    self.logger = logger
    self.load_config(fpgaConfig,logger)


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


  def load_config(self,fpgaConfig,logger = None):
    self.rowResourceInfo = fpgaConfig['row_resource_info']
    self.fpgaMatrix = FpgaMatrix(fpgaConfig,logger)
    self.set_static_region(fpgaConfig['static_region']['coords'])
    self.partitionCount+=1
    return

  def inc_resource(self,resource):
    if(self.rowResourceInfo is None):
      self.logger.error(f"RowResourceInfo não setado")
      return

    self.resourceCount[resource]+= self.rowResourceInfo[resource]

  def set_static_region(self, static_subcoords):
    '''
    Recebe uma lista de coordenadas que demarcam retangulos e marca todos os blocos compreendidos dentro
    desses retângulos como pertencentes a região estática do fpga
    '''
    for static_coords in static_subcoords:
      upper_left, bottom_right = static_coords
      for column in range(upper_left[0], bottom_right[0] + 1):
        for line in range(upper_left[1], bottom_right[1]):
          self.getTile((column, line)).static = True

    return

##
  def find_allocation_region(self, start_coord, size, direction=RIGHT):

    if (self.getTile(start_coord).isAvailableForAllocation() == False):
      self.logger.debug(f"Can't allocate for {start_coord}. Coords are unavailable for allocation")
      return
    
    size_info = self.config['partition_size'][size]
    scan_coords = self.fpgaMatrix.create_matrix_loop(start_coord,direction,excludeStatic = True)

    for current_static_coord in scan_coords:
      if (current_static_coord is None):
        self.logger.error(f"Can't allocate for {start_coord}. Found a None tile in the iteration coords")
        return

      current_resource_count = self.fpgaMatrix.calculate_region_resources(start_coord, current_static_coord)

      if (current_resource_count is not None):
        if (utils.is_resource_count_sufficient(current_resource_count,size_info) and self.fpgaMatrix.is_region_border_static(start_coord,current_static_coord)):
          self.logger.info(f"Succesfully found an available region with {current_resource_count} at [{start_coord};{current_static_coord}]")
          return [start_coord, current_static_coord]

    self.logger.debug(f"No allocation found for {start_coord} that satisfies {size_info}")
    return None
  
  
  
##
  def allocate_region(self,start_coords,end_coords):
    start_column,start_row = start_coords
    end_column,end_row = end_coords

    if(start_column > end_column):
      start_column,end_column = end_column,start_column
        
    if(start_row > end_row):
      start_row,end_row = end_row,start_row

    self.logger.info(f"Attempting allocation for [({start_column},{start_row});({end_column},{end_row})]")

    for column in range(start_column,end_column+1):
      for row in range(start_row,end_row+1):
        if(self.getTile((column,row)).isAvailableForAllocation() == False):
          self.logger.info(f'Unavailable tile found in region at ({column},{row}). Aborting partition {self.partitionCount} allocation')
          return
    
    for column in range(start_column,end_column+1):
      for row in range(start_row,end_row+1):
        if(self.getTile((column,row)).static == False):
          self.getTile((column,row)).partition = self.partitionCount

    self.logger.info('Succesfully allocated region')
    self.partitionCount+=1


