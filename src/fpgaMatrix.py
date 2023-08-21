class fpgaMatrix:
    def __init__(self,matrix):
        self.matrix = matrix
        self.height = len(matrix)
        self.width = len(matrix[0])