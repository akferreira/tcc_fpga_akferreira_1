# coordenadas da região estática dispostas X,Y
# mapa do fpga disposto em Y,X

class FpgaTile():
  # partição 0 = partição estática
  FpgaMatrix = None

  DimensionInfo = ['Y', 'X']
  RowResourceInfo = None
  PartitionCount = 0
  ResourceCount = {'BRAM': 0, 'CLB': 0, 'DSP': 0, 'IO': 0}

  def __init__(self, resource, column,row,logger = None):
    self.resource = resource
    self.partition = None
    self.static = False
    self.edgeStatic = None
    self.innerStatic = None
    self.column = column
    self.row = row
    self.logger = logger

  def isAvailableForAllocation(self):
    return (self.partition is None)

  """
  @property
  def static(self):
    return self._static

  @static.setter
  def static(self, isStatic):
    self._static = isStatic
    self.partition = 0 if isStatic else self.partition

  """
  """
  @property
  def partition(self):
    return self._partition

  @partition.setter
  def partition(self, partition):
    if(partition is None):
      self._partition = None

    elif (partition > 0):
      if (self.static == True):
        self.logger.error(f"Bloco pertence a partição estática. Alocação {partition=} inválida\n")
        return
      self._partition = partition
    else:
      self._partition = partition
    return
  """
