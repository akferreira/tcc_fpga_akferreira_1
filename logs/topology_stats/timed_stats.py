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

N10_TICK = 900
N30_TICK = 1800
TICK_VALUES = {10:900, 30:1800}
TIME_TICKS = 5
pre1_types = {'nodes': 'int','population': 'int','generation':'int','elite':'int','run':'int','topology_id': 'int'}
pre3_types = pre1_types | {'time_axis': 'int','params':'int'}

plt.rcParams['figure.dpi'] = 300
stats_df = pd.read_csv('timed_results.csv',sep = ';',decimal =',')
stats_df.drop(['links','realloc_rate'], axis=1,inplace=True)

n30_df = stats_df.loc[((stats_df['nodes'] == 30) & (stats_df['generation'] == 0)) | ((stats_df['nodes'] == 30) & (stats_df['generation'] > 0) & (stats_df['time'] > N30_TICK) & (stats_df['time']%N30_TICK < N30_TICK*0.45))]
n10_df = stats_df.loc[((stats_df['nodes'] == 10) & (stats_df['generation'] == 0)) | ((stats_df['nodes'] == 10) & (stats_df['generation'] > 0) & (stats_df['time'] > N10_TICK) & (stats_df['time']%N10_TICK < N10_TICK*0.06))]
n10_df = n10_df.astype(pre1_types)
n30_df = n30_df.astype(pre1_types)

network_dfs = [n10_df,n30_df]

params_set = set()
n10_df.to_csv('n10_pre1.csv', sep=';', decimal=',', index=False,mode='w')
n30_df.to_csv('n30_pre1.csv', sep=';', decimal=',', index=False,mode='w')

for nx_df in network_dfs:
    node_count = int(nx_df.iloc[0]['nodes'])
    tick_value = TICK_VALUES[node_count]

    pre_df = pd.DataFrame()
    prev_generation = 0
    header = list(nx_df)
    data = []
    for row,entry in nx_df.iterrows():
        generation = entry['generation']
        params_set.add((entry['population'],entry['resize_rate'],entry['elite']/entry['population']))
        if(generation == 0 or prev_generation == 0 or generation - prev_generation > 1):
            data.append(entry)

        prev_generation = generation

    pre_df = pd.DataFrame(data,columns=header)
    pre_df.to_csv(f'n{node_count}_pre2.csv', sep=';', decimal=',', index=False,mode='w')

    pre_df['time_axis'] = pre_df['time'].apply(lambda time: int(time/tick_value))

    data = []
    params_list = list(params_set)
    for row,entry in pre_df.iterrows():
        param_index = params_list.index((entry['population'],entry['resize_rate'],entry['elite']/entry['population']))
        entry['params'] = int(param_index)
        data.append(entry)

    header = list(pre_df)
    header.append('params')
    pre_df = pd.DataFrame(data,columns=header)
    pre_df = pre_df.astype(pre3_types)
    pre_df = swap_columns(pre_df,'params','maxScore')
    pre_df.to_csv(f'n{node_count}_pre3.csv', sep=';', decimal=',', index=False,mode='w')

    data = []
    print(params_list)
    for params in range(len(params_list)):
        creation_time = mean(pre_df.loc[(pre_df['params'] == params) & (pre_df['time_axis'] == 0)]['time'])
        for time_tick in range(TIME_TICKS):
            sub_df = pre_df.loc[(pre_df['params'] == params) & (pre_df['time_axis'] == time_tick)]
            dev_score = round(pstdev(sub_df['maxScore']),4)
            avg_score = round(mean(sub_df['maxScore']),4)
            param_entry = params_list[params]
            entry = {'nodes': node_count, 'population' : param_entry[0],'resize_rate': param_entry[1],'elite': param_entry[2],'params':params,'time_axis':time_tick,'tick_value':tick_value,'avg_score': avg_score, 'dev_score': dev_score,'creation_time': creation_time}
            data.append(entry)


    pre_df = pd.DataFrame(data,columns=data[0].keys())
    pre_df.to_csv(f'n{node_count}_pre4.csv', sep=';', decimal=',', index=False,mode='w')

    plt.figure()
    all_avgs = []
    for param_index,params in enumerate(params_list):
        entries = pre_df.loc[pre_df['params'] == param_index]
        first_entry = entries.iloc[0]
        time_ticks = list(entries['time_axis'] * entries.iloc[0]['tick_value'])
        time_ticks[0] = first_entry['creation_time']
        avg_scores = list(entries['avg_score'])
        dev_scores = list(entries['dev_score'])
        population = int(first_entry['population'])
        elite = first_entry['elite']
        resize_rate = first_entry['resize_rate']

        plt.xticks(time_ticks)
        linestyle = {"linestyle": "solid", "linewidth": 2, "markeredgewidth": 3, "elinewidth": 3, "capsize": 3}
        plt.errorbar(time_ticks,avg_scores,yerr = dev_scores,fmt='o',label = f'P{population}.R{resize_rate}.E{elite}', **linestyle)

    plt.xlabel("Tempo(s)")
    plt.ylabel("VNFs alocadas (%)")
    plt.legend()
    plt.grid()
    plt.savefig(f'N{node_count}_params_comp.png',dpi = 800)
    if(node_count == 10):
        plt.yticks([i/100 for i in range(69,79,1)])
        plt.ylim(0.735,0.79)
    else:
        plt.yticks([i / 100 for i in range(64, 74, 1)])
        plt.ylim(0.64, 0.74)

    plt.xlim(tick_value * 2.8, tick_value * 4.2)
    plt.savefig(f'N{node_count}_params_comp2.png', dpi=800)

exit(0)

