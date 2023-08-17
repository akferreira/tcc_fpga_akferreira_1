from urllib.request import urlopen
import json
from collections import Counter,defaultdict
import random

fpga_config_url = 'https://raw.githubusercontent.com/akferreira/tcc_fpga_akferreira_1/main/fpga.json'
partition_config_url = 'https://raw.githubusercontent.com/akferreira/tcc_fpga_akferreira_1/main/partition.json'
coord_X = 0
coord_Y = 1
matrix_line = 0
matrix_column = 1


def circular_range(start,stop):
  return [i for i in range(start,stop)] + [i for i in range(start)]

def load_json_config(url):
  response = urlopen(url)
  config = json.loads(response.read())
  return config

def generate_random_fpga_coord(max_row,max_column):
  randx = random.randrange(max_column)
  randy = random.randrange(max_row)

  return (randx,randy)

def is_resource_count_equal(resources1,resources2):
  return False

#coordenadas da região estática dispostas X,Y
#mapa do fpga disposto em Y,X

class fpgaTile():
  #partição 0 = partição estática
  FpgaMatrix = None
  
  DimensionInfo = ['Y','X']
  RowResourceInfo = None
  PartitionCount = 0
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
  def Dimensions(cls):
    return [len(cls.FpgaMatrix),len(cls.FpgaMatrix[0])]

  @classmethod
  def load_config(cls,fpga_config):
    cls.RowResourceInfo = fpga_config['row_resource_info']
    cls.FpgaMatrix = [[fpgaTile(column,fpga_config['row_count']) for column in fpga_config['columns']] for row in range(fpga_config['row_count'])] #repete a lista de colunas "linhas" vezes, criando uma
    cls.set_static_region(fpga_config['static_region']['coords'])                                                                               #matriz de dimensõeslinha x coluna
    return


  @classmethod
  def inc_resource(cls,resource):
    if(cls.RowResourceInfo is None):
      print(f"ERRO: RowResourceInfo não setado \n")
      return

    cls.ResourceCount[resource]+= cls.RowResourceInfo[resource]

  @classmethod
  def calculate_region_resources(cls,start_coords,end_coords): #A função só deve retornar um valor válido se a região dada não pega de duas ou mais regiões
    '''
    Calcula a quantidade de recursos em uma dada região retangular. 
    Entrada: start_coords -> coordenadas do canto superior esquerdo do retângulo
    end_coords -> coordenadas do canto inferior direito do retângulo
    '''
    start_column,start_row = start_coords
    end_column,end_row = end_coords
    resourceCount = defaultdict(int)

    for row in range(start_row,end_row):
      for column in range(start_column,end_column+1):
        resource = cls.FpgaMatrix[row][column].resource
        resourceCount[resource] += cls.RowResourceInfo[resource]

    return resourceCount

  @classmethod
  def set_static_region(cls,static_subcoords):
    '''
    Recebe uma lista de coordenadas que demarcam retangulos e marca todos os blocos compreendidos dentro
    desses retângulos como pertencentes a região estática do fpga
    '''

    if fpgaTile.FpgaMatrix is None:
      print(f"ERRO: Mapa do fpga não setado \n")
      return

    for static_coords in static_subcoords:
      upper_left,bottom_right = static_coords

      for column in range(upper_left[0],bottom_right[0]+1):
        for line in range(upper_left[1],bottom_right[1]):
          cls.FpgaMatrix[line][column].static = True

    print(cls.FpgaMatrix[2][65].static)
    return

  @classmethod
  def create_matrix_loop(cls,start_coords,direction = 0): 
    '''
    Gera uma matriz de coordenadas a partir da matriz do fpga, percorrendo o fpga ou horizontalmente da esquerda para direita
    ou verticalmente de baixo para cima. 
    '''
    start_column,start_row = start_coords
    head,tail,body = [],[],[]
    if(direction == 0):
      for row in circular_range(start_row,len(cls.FpgaMatrix)):
        if(row == start_row):
          tail = [[(x,row) for x in range(start_column)]]
          head = [[(x,row) for x in range(start_column,cls.Dimensions()[1])]]
        else:
          body.append([(x,row) for x in range(cls.Dimensions()[1])])

    else:
      for column in circular_range(start_column,cls.Dimensions()[1]):
        if(column == start_column):
          tail = [[(column,y) for y in range(start_row)]]
          head = [[(column,y) for y in range(start_row,cls.Dimensions()[0])]]
        else:
          body.append([(column,y) for y in range(cls.Dimensions()[0])])

    return head + body + tail

  @classmethod
  def find_static_from_coord(cls,coord,direction = 0):
    '''
    Busca o bloco da região estática mais próximo da coordenada dada. Recebe também como parâmetro em que direção essa busca será feita  
    RIGHT = 0, UP = 1
    '''
    scan_coords = cls.create_matrix_loop(coord,direction)

    for current_list in scan_coords:
      for current_coord in current_list:
        if(cls.FpgaMatrix[current_coord[1]][current_coord[0]].static == True and current_coord != coord):
          return current_coord

    return

  @classmethod
  def find_allocation_region(cls,start_coord,size_info,direction = 0):
    current_static_coord = cls.find_static_from_coord(start_coord,direction)
    if(current_static_coord):
      current_resource_count = cls.calculate_region_resources(start_coord,current_static_coord)
      #loop
      #compara e verifica se a quantidade de recursos para a região atual satisfaz o requisito do tamanho da região
      #se sim, termina o loop
      #se não, calcula a próxima coordenada para o canto inferior direito da região candidata. Se chegou no limite do espaço do fpga, ou se a região invadir outra(incluindo a estática, fim do loop)
      #vai inicio do loop



    return
  








fpga_config = load_json_config(fpga_config_url)
fpga_config.update(load_json_config(partition_config_url))
fpgaTile.load_config(fpga_config)
print(fpgaTile.ResourceCount)


static_coord = fpgaTile.find_static_from_coord((80,4),direction = 0)
print(static_coord)
print(fpgaTile.calculate_region_resources( (80,3),static_coord))
print(fpga_config["partition_size"])
print(fpgaTile.Dimensions())
