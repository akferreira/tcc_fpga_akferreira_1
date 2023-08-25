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
MIN_ROW_DIFF = 1
MIN_COL_DIFF = 10
MIN_AREA = {'S':35, 'M': 140, 'L':300}

class FpgaBoard():
  def __init__(self,fpgaConfig,logger):
    self.dimensions = [0,0]
    self.rowResourceInfo = dict()
    self.partitionCount = 0
    self.partitionInfo = {}
    self.resourceCount = {'BRAM': 0,'CLB': 0, 'DSP': 0, 'IO': 0}
    self.staticRegion = None
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
    return

  def inc_resource(self,resource):
    if(self.rowResourceInfo is None):
      self.logger.error(f"RowResourceInfo não setado")
      return

    self.resourceCount[resource]+= self.rowResourceInfo[resource]

  def set_static_region(self, static_coords):
    '''
    Recebe uma lista de coordenadas que demarcam retangulos e marca todos os blocos compreendidos dentro
    desses retângulos como pertencentes a região estática do fpga
    '''
    self.staticRegion = static_coords

    for static_subcoords in static_coords:
      upper_left, bottom_right = static_subcoords
      for column in range(upper_left[0], bottom_right[0] + 1):
        for line in range(upper_left[1], bottom_right[1]):
          self.getTile((column, line)).static = True

    self.classify_static_tiles()
    self.partitionCount += 1
    return

  def classify_static_tiles(self):
    static_coords = self.fpgaMatrix.get_all_edge_static_coords((0,0))
    for coords in static_coords:
      static_tile = self.getTile(coords)
      static_tile.edgeStatic = True
      static_tile.innerStatic = False

  def find_allocation_region(self, start_coord, size, direction=RIGHT):

    if (self.getTile(start_coord).isAvailableForAllocation() == False):
      self.logger.debug(f"Can't allocate for {start_coord}. Coords are unavailable for allocation")
      return
    
    size_info = self.config['partition_size'][size]
    scan_coords = self.fpgaMatrix.create_matrix_loop(start_coord,direction,excludeStatic = True)

    for current_coord in scan_coords:
      if (current_coord is None):
        self.logger.error(f"Can't allocate for {start_coord}. Found a None tile in the iteration coords")
        return

      column_diff,row_diff = utils.coord_diff(start_coord,current_coord)
      if(column_diff*row_diff > MIN_AREA[size]):
        #print(f"min_area {column_diff*row_diff} for {size}")
        current_resource_count = self.fpgaMatrix.calculate_region_resources(start_coord, current_coord)

        if (current_resource_count is not None):
          if (self.fpgaMatrix.is_region_border_static(start_coord,current_coord) and utils.is_resource_count_sufficient(current_resource_count,size_info)):
            self.logger.info(f"Succesfully found an available region with {current_resource_count} at [{start_coord};{current_coord}]")
            print(f'{column_diff*row_diff}')
            return [start_coord, current_coord,current_resource_count]

    self.logger.debug(f"No allocation found for {start_coord} that satisfies {size_info}")
    return None

  def allocate_region(self,start_coords,end_coords,region_resource_count):
    start_coords,end_coords = utils.sort_coords(start_coords,end_coords)
    start_column, start_row = start_coords
    end_column, end_row = end_coords

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
    self.partitionInfo[self.partitionCount] = {
      'coords': [(start_column,start_row),(end_column,end_row)],
      'resources': region_resource_count
    }
    self.partitionCount+=1

  def full_board_allocation(self,sizes):
    full_loop = False
    
    while (full_loop == False):
      random_coords = utils.generate_random_fpga_coord(self)
      direction = random.randrange(2)
      size = sizes[ random.randrange(len(sizes)) ]
      allocation_coords = self.fpgaMatrix.create_matrix_loop(random_coords,direction = direction, excludeStatic=True,
                                                                  excludeAllocated=True)
      self.logger.info(f'Attempting new allocation of {size=}')
      for i, coords in enumerate(allocation_coords):
        self.logger.debug(f'Attempt number {i} at {coords}')
        allocation_region_test = self.find_allocation_region(coords, size)

        if (allocation_region_test is not None):
          self.allocate_region(allocation_region_test[0], allocation_region_test[1], allocation_region_test[2])
          break

      if(i + 1 == len(allocation_coords)):
        sizes.remove(size)

      full_loop = (len(sizes) == 0)

    return

  def get_complete_partition_resource_report(self):
    output = {}

    for partition,info in self.partitionInfo.items():
      output[f'Part{partition-1}'] = info['resources']

    json_output = json.dumps(output,indent = 4)
    return json_output

  def save_allocated_to_file(self,path):
    json_output = self.partitionInfo
    json_output = json.dumps(json_output, indent=4)
    utils.save_json_file(json_output,path)

    return

  def load_allocated_from_file(self,path):
    json_data = utils.load_json_config_file(path)
    for partition,partition_data in json_data.items():
        self.allocate_region(partition_data['coords'][0],partition_data['coords'][1],partition_data['resources'])

    return


