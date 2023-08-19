# coordenadas da região estática dispostas X,Y
# mapa do fpga disposto em Y,X

class FpgaTile():
  # partição 0 = partição estática
  FpgaMatrix = None

  DimensionInfo = ['Y', 'X']
  RowResourceInfo = None
  PartitionCount = 0
  ResourceCount = {'BRAM': 0, 'CLB': 0, 'DSP': 0, 'IO': 0}

  def __init__(self, resource, rows):
    self.resource = resource
    self.partition = None
    self.static = False

  @property
  def static(self):
    return self._static

  @static.setter
  def static(self, isStatic):
    self._static = isStatic
    self.partition = 1 if isStatic else self.partition

  def isAvailableForAllocation(self):
    return (self.partition is None) or (self.partition == 0)

  def set_partition(self, partition):
    if (partition > 0):
      if (self.static == True):
        print("Bloco pertence a partição estática. Alocação inválida\n")
        return
      self.partition = partition
    else:
      print(f"Partição 0 fornecida. Para setar um bloco como pertencente a partição estática use o atributo .static")
    return