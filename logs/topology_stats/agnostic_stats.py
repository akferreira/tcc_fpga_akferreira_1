import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
from urllib.request import urlopen
from statistics import mean,median,pstdev
import os
import json
import random
import numpy as np
import seaborn as sns

def swap_columns(df, col1, col2):
    col_list = list(df.columns)
    x, y = col_list.index(col1), col_list.index(col2)
    col_list[y], col_list[x] = col_list[x], col_list[y]
    df = df[col_list]
    return df


plt.rcParams['figure.dpi'] = 300
stats_n10_df = pd.read_csv('agnostic_results_10.csv',sep = ';',decimal =',')
n10_dict = defaultdict(list)
stats_n30_df = pd.read_csv('agnostic_results_30.csv',sep = ';',decimal =',')
header = list(stats_n30_df)
n30_dict = defaultdict(list)

for row, entry in stats_n10_df.iterrows():
    population = int(entry['population'])
    n10_dict[(population, entry['resize_rate'], entry['elite'] / entry['population'])].append(entry['maxScore'])

for key,value in n10_dict.items():
    n10_dict[key] = {'mean':  round(mean(value),4), 'stddev': round(pstdev(value),4)}

for row, entry in stats_n30_df.iterrows():
    population = int(entry['population'])
    n30_dict[(population, entry['resize_rate'], entry['elite'] / entry['population'])].append(entry['maxScore'])

for key,value in n30_dict.items():
    n30_dict[key] = {'mean':  round(mean(value),4), 'stddev': round(pstdev(value),4)}

sorted_n10_dict = sorted(n10_dict.items(), key=lambda x:x[1]['mean'],reverse=True)
sorted_n30_dict = sorted(n30_dict.items(), key=lambda x:x[1]['mean'],reverse=True)
best_n10 = sorted_n10_dict[0]
best_n10 = {'nodes': 10,'population': best_n10[0][0],'resize_rate':  best_n10[0][1],'elite':  best_n10[0][2],'avgScore': best_n10[1]['mean'],'stdev':best_n10[1]['stddev']}
best_n30 = sorted_n30_dict[0]
best_n30 = {'nodes': 30,'population': best_n30[0][0],'resize_rate':  best_n30[0][1],'elite':  best_n30[0][2],'avgScore': best_n30[1]['mean'],'stdev':best_n30[1]['stddev']}

print(best_n10)
best_n10_df = pd.DataFrame(best_n10,columns=list(best_n10.keys()) , index = [0])
best_n30_df = pd.DataFrame(best_n30,columns=list(best_n30.keys()) , index = [0])
best_n10_df.to_csv(f'agnostic_best.csv', sep=';', decimal=',', index=False,mode='w')
best_n30_df.to_csv(f'agnostic_best.csv', sep=';', decimal=',', index=False,mode='a', header=None)

