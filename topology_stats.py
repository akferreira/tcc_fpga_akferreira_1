from src import utils,db
from src.fpgaBoard import FpgaBoard
from src import vsguerra
from multiprocessing import Lock
from pymongo import MongoClient,ReplaceOne,ASCENDING,DESCENDING
from collections import defaultdict
from random import shuffle,random
import json,os
from tqdm import tqdm
from copy import deepcopy
from config import config
from statistics import pstdev,median
import pandas as pd

args = config.argparser()
topologies_filenames = [file for file in os.listdir(args.topology_dir) if (".json" in file and (("N10" in file) or "N30" in file) )]
topologies_filenames.sort()
data = []

for topology_filename in topologies_filenames:
    topology = utils.load_topology(os.path.join(args.topology_dir, topology_filename))
    node_count = len(topology.keys())
    links = 0
    fpga_qtd = 0
    fpga_distribution = []
    for nodo_id,node_info in topology.items():
        links += len(node_info['Links'])
        fpga_qtd += len(node_info['FPGA'])
        fpga_distribution.append(len(node_info['FPGA']))

    links = int(links/2)
    fpga_avg = fpga_qtd/node_count
    fpga_stddev = pstdev(fpga_distribution)
    fpga_median = median(fpga_distribution)
    data.append({'filename' : topology_filename,'node': node_count,'avg_fpga': fpga_avg,'stdev': fpga_stddev,'median_fpga':fpga_median, 'links': links})

data.sort
topology_stats_df = pd.DataFrame(data,columns= data[0].keys())
topology_stats_df.to_csv('topology_stats.csv', sep=';', decimal=',', index=False,mode='w')
