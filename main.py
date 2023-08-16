from urllib.request import urlopen
import json
from collections import Counter,defaultdict
import random

fpga_config_url = 'https://raw.githubusercontent.com/akferreira/tcc_fpga_akferreira_1/main/fpga.json'
coord_X = 0
coord_Y = 1
matrix_line = 0
matrix_column = 1


def circular_range(start,stop):
  return [i for i in range(start,stop)] + [i for i in range(start)]

def load_json_config(url):
  response = urlopen(url)
  config = json.loads(response.read())
  #config['static_region']['coords'] = [(tuple(coord[0]),tuple(coord[1])) for coord in config['static_region']['coords']]

  return config



#coordenadas da região estática dispostas X,Y
#mapa do fpga disposto em Y,X

class fpgaTile():
  #partição 0 = partição estática
  FpgaMap = None
  Dimensions = [0,0]
  DimensionInfo = ['Y','X']
  RowResourceInfo = None
  ResourceCount = {'BRAM': 0,'CLB': 0, 'DSP': 0, 'IO': 0}

  def __init__(self,resource,rows):
    self.resource = resource
    self.inc_resource(self.resource)
    self.partition = None
    self.static = False

  @property
  def static(self):
    return self._static

  @static.setter
  def static(self,isStatic):
    self._static = isStatic
    self.partition = 0 if isStatic else 1


  @classmethod
  def inc_resource(cls,resource):
    if(cls.RowResourceInfo is None):
      print(f"ERRO: RowResourceInfo não setado \n")
      return

    cls.ResourceCount[resource]+= cls.RowResourceInfo[resource]

  @classmethod
  def calculate_region_resources(cls,start_coords,end_coords):
    start_column,start_row = start_coords
    end_column,end_row = end_coords
    resourceCount = defaultdict(int)

    for row in range(start_row,end_row):
      for column in range(start_column,end_column+1):
        resource = cls.FpgaMap[row][column].resource
        resourceCount[resource] += cls.RowResourceInfo[resource]

    return resourceCount

  @classmethod
  def set_static_region(cls,static_subcoords):
    '''
    Recebe uma lista de coordenadas que demarcam retangulos e marca todos os blocos compreendidos dentro
    desses retângulos como pertencentes a região estática do fpga
    '''

    if fpgaTile.FpgaMap is None:
      print(f"ERRO: Mapa do fpga não setado \n")
      return

    for static_coords in static_subcoords:
      upper_left,bottom_right = static_coords

      for column in range(upper_left[0],bottom_right[0]+1):
        for line in range(upper_left[1],bottom_right[1]):
          cls.FpgaMap[line][column].static = True

    print(cls.FpgaMap[2][65].static)
    return

  @classmethod
  def iterate_through_map(cls,start_coords,direction = 0): #talvez escolher um nome melhor
    '''
    Gera uma lista de comprimento igual a quantidade de linhas da matriz fpga de lista de índices de colunas.
    Iterando sobre ela percorre-se circularmente a matriz fpga bloco por bloco.
    '''
    start_column,start_row = start_coords
    head,tail,body = [],[],[]
    if(direction == 0):
      for row in circular_range(start_row,len(cls.FpgaMap)):
        if(row == start_row):
          tail = [[(x,row) for x in range(start_column)]]
          head = [[(x,row) for x in range(start_column,cls.Dimensions[1])]]
        else:
          body.append([(x,row) for x in range(cls.Dimensions[1])])

    else:
      for column in circular_range(start_column,len(cls.FpgaMap[0])):
        if(column == start_column):
          tail = [[(column,y) for y in range(start_row)]]
          head = [[(column,y) for y in range(start_row,cls.Dimensions[0])]]
        else:
          body.append([(column,y) for y in range(cls.Dimensions[0])])

    return head + body + tail

  @classmethod
  #RIGHT = 0, DOWN = 1
  def find_static_from_coord(cls,coord,direction = 0):



    scan_coords = cls.iterate_through_map(coord,direction)

    for current_list in scan_coords:
      for current_coord in current_list:
        if(cls.FpgaMap[current_coord[1]][current_coord[0]].static == True and current_coord != coord):
          return current_coord

    return

def generate_random_fpga_coord(max_row,max_column):
  randx = random.randrange(max_column)
  randy = random.randrange(max_row)

  return (randx,randy)






fpga_config = load_json_config(fpga_config_url)
fpgaTile.RowResourceInfo = fpga_config['row_resource_info']
fpgaTile.FpgaMap = [[fpgaTile(column,fpga_config['row_count']) for column in fpga_config['columns']] for row in range(fpga_config['row_count'])] #repete a lista de colunas "linhas" vezes, criando uma
fpgaTile.set_static_region(fpga_config['static_region']['coords'])                                                                               #matriz de dimensõeslinha x coluna
fpgaTile.Dimensions = [len(fpgaTile.FpgaMap),len(fpga_config['columns'])]
print(fpgaTile.ResourceCount)

tiles = []
for column in fpgaTile.FpgaMap:
  for tile in column:
    if tile.static:
      tiles.extend([tile.resource for i in range(fpgaTile.RowResourceInfo[tile.resource])])

count = Counter(tiles)
print(count)

print(fpgaTile.find_static_from_coord((80,4),direction = 0))
print(fpgaTile.calculate_region_resources( (0,0),(181,15)))




