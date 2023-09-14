# @title FpgaBoard.py
from urllib.request import urlopen
import json
from collections import Counter,defaultdict
import random
from itertools import chain
from multiprocessing import Lock, Process, Queue, current_process,Pool
from functools import partial
import time
import queue
from . import utils
from .fpgaTile import FpgaTile
from .fpgaMatrix import FpgaMatrix

RIGHT = 0
UP = 1
MIN_ROW_DIFF = 1
MIN_COL_DIFF = 10
MIN_AREA = {'S':100, 'M': 210, 'L':500}
MAX_AREA = {'S':170, 'M': 310, 'L':800}

class FpgaBoard():
  def __init__(self,fpgaConfig,logger):
    self.dimensions = [0,0]
    self.partitionCount = 0
    self.partitionInfo = {}
    self.resourceCount = {'BRAM': 0,'CLB': 0, 'DSP': 0, 'IO': 0}
    self.freeTiles = [[],[]] #0 right, 1 up
    self.staticRegion = None
    self.config = fpgaConfig
    self.logger = logger
    self.load_config(fpgaConfig,logger)


  def getTile(self,coordinates):
    return self.fpgaMatrix.getTile(coordinates)

  def getMatrix(self):
    return self.fpgaMatrix.matrix

  def load_config(self,fpgaConfig,logger = None):
    self.fpgaMatrix = FpgaMatrix(fpgaConfig,logger)

    for row in range(self.fpgaMatrix.height):
      for column in range(self.fpgaMatrix.width):
        self.freeTiles[RIGHT].append((column,row))

    for column in range(self.fpgaMatrix.width):
      for row in range(self.fpgaMatrix.height):
        self.freeTiles[UP].append((column,row))

    self.set_static_region(fpgaConfig['static_region']['coords'])


    return

  def set_static_region(self, static_coords):
    '''
    Recebe uma lista de coordenadas que demarcam retangulos e marca todos os blocos compreendidos dentro
    desses retângulos como pertencentes a região estática do fpga
    '''
    self.staticRegion = static_coords

    for static_subcoords in static_coords:
      upper_left, bottom_right = static_subcoords
      for column in range(upper_left[0], bottom_right[0] + 1):
        for line in range(upper_left[1], bottom_right[1]+1):
          try:
            self.freeTiles[0].remove((column,line))
            self.freeTiles[1].remove((column,line))
          except ValueError:
            pass

          tile = self.getTile((column, line))
          tile.static = True
          tile.partition = 0


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
    split_index = self.freeTiles[direction].index(start_coord)
    scan_coords = self.freeTiles[direction][split_index:] + self.freeTiles[direction][:split_index]

    for current_coord in scan_coords:
      if (current_coord is None):
        self.logger.error(f"Can't allocate for {start_coord}. Found a None tile in the iteration coords")
        return

      column_diff, row_diff = abs(current_coord[0]-start_coord[0]),abs(current_coord[1]-start_coord[1])
      if(column_diff*row_diff > MIN_AREA[size]):

        current_resource_count = self.fpgaMatrix.calculate_region_resources(start_coord, current_coord,self.partitionInfo,self.staticRegion)

        if (current_resource_count is not None):
          if (self.fpgaMatrix.is_region_border_static(start_coord,current_coord,self.staticRegion) and utils.is_resource_count_sufficient(current_resource_count,size_info)):
            return [start_coord, current_coord,current_resource_count]

    self.logger.debug(f"No allocation found for {start_coord} that satisfies {size_info}")
    return None

  def allocate_region(self,start_coords,end_coords,region_resource_count,resize = False):
    start_coords,end_coords = utils.sort_coords(start_coords,end_coords)
    start_column, start_row = start_coords
    end_column, end_row = end_coords

    self.logger.verbose(f"Attempting allocation for [({start_column},{start_row});({end_column},{end_row})]")

    count = 0

    for column in range(start_column,end_column+1):
      for row in range(start_row,end_row+1):
        if(self.getTile((column,row)).isAvailableForAllocation() == False):
          self.logger.verbose(f'Unavailable tile found in region at ({column},{row}). Aborting partition {self.partitionCount} allocation')
          return
    
    for column in range(start_column,end_column+1):
      for row in range(start_row,end_row+1):
        self.freeTiles[0].remove((column,row))
        self.freeTiles[1].remove((column,row))
        tile = self.getTile((column,row))
        if(tile.static == False):
          tile.partition = self.partitionCount

    self.logger.verbose('Succesfully allocated region')
    self.partitionInfo[self.partitionCount] = {
      'coords': [(start_column,start_row),(end_column,end_row)],
      'resources': region_resource_count
    }
    if(resize == False):
      self.partitionCount+=1
    return self.partitionCount

  def full_board_allocation(self,sizes,allocation_info):
    full_loop = False
    while (full_loop == False):
      random_coords = utils.generate_random_fpga_coord(self.fpgaMatrix)
      direction = random.randrange(2)
      size = sizes[ random.randrange(len(sizes)) ]
      allocation_coords = self.fpgaMatrix.create_matrix_loop(random_coords,direction = direction,excludeAllocated=True)
      self.logger.verbose(f'Attempting new allocation of {size=}')
      for i, coords in enumerate(allocation_coords):
        if(allocation_info[coords][size] == False):
          continue
        self.logger.debug(f'Attempt number {i} at {coords}')
        allocation_region_test = self.find_allocation_region(coords, size,direction)

        if (allocation_region_test is not None):
          self.logger.verbose(f"Succesfully found an available region with {allocation_region_test[2]} at [{allocation_region_test[0]};{ allocation_region_test[1]}]")
          self.allocate_region(allocation_region_test[0], allocation_region_test[1], allocation_region_test[2])
          break
      else:
        sizes.remove(size)

      full_loop = (len(sizes) == 0)

    return

  def resize_region(self,partition, row_diff, column_diff,direction):
    try:
      current_partition = self.partitionInfo[partition]
      start_column,start_row = current_partition['coords'][0]
      end_column,end_row = current_partition['coords'][1]

      if(direction == 0):
        start_column =  max(start_column-column_diff,0)
        start_row = max(start_row-row_diff,0)

      else:
        end_column = min(end_column+column_diff,self.fpgaMatrix.width-1)
        end_row = min(end_row+row_diff,self.fpgaMatrix.height-1)

      for column in range(start_column,end_column+1):
        for row in range(start_row,end_row+1):
          tile = self.getTile((column,row))
          if(tile.isAvailableForAllocation() == False and tile.partition != partition):
            self.logger.verbose(f'Unavailable tile found in region at ({column},{row}). Aborting partition {partition} resizing')
            return

      for column in range(start_column,end_column+1):
        for row in range(start_row,end_row+1):
          if((column,row) in self.freeTiles[0]):
            self.freeTiles[0].remove((column,row))
            self.freeTiles[1].remove((column,row))
          tile = self.getTile((column,row))
          tile.partition = partition

      new_resource_count = self.fpgaMatrix.calculate_region_resources((start_column,start_row ),(end_column,end_row))

      if(current_partition['resources'] == new_resource_count):
        self.logger.verbose(f'Partition {partition} resized, but resource count unchanged')
      else:
        self.logger.verbose('Succesfully resized region')

        self.partitionInfo[partition] = {
        'coords': [(start_column,start_row),(end_column,end_row)],
        'resources': new_resource_count}

    except KeyError:
      self.logger.error(f"Partition {partition} not found. Unable to resize")

    return True

  def full_board_resize(self,max_attempts = 10, max_row_diff = 1, max_column_diff = 6):
    if(max_attempts is None):
      max_attempts = self.partitionCount*4

    for attempt in range(max_attempts):
      row_diff = random.randrange(0,max_row_diff+1)
      column_diff = random.randrange(0,max_column_diff+1)
      partition = random.randrange(1,self.partitionCount)
      direction = random.randrange(2)

      self.resize_region(partition, row_diff, column_diff,direction)

    return

  def get_db_dict(self):
    output = {'modelo': 'G','partitions': dict()}

    for partition, info in self.partitionInfo.items():
      output['partitions'][f'{partition - 1}'] = {'resources': info['resources'],'coords':info['coords']}

    return output

  def get_complete_partition_resource_report(self):
    output = {'Modelo': 'G'}

    for partition,info in self.partitionInfo.items():
      output[f'Part{partition-1}'] = info['resources']
      output[f'Part{partition-1}']['coords'] = info['coords']

    return output

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


