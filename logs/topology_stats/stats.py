import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
from urllib.request import urlopen
from statistics import mean,median
import os
import json
import random
import numpy as np
import seaborn as sns

plt.rcParams['figure.dpi'] = 300
stats_df = pd.read_csv('results_n10.csv',sep = ';',decimal =',')
pop_gen_df = stats_df[['generation','population','maxScore']]
pop_resize_dict= defaultdict(list)
pop_gen_dict = defaultdict(list)
mutation_dict= defaultdict(list)
elite_gen_dict=defaultdict(list)
elite_pop_dict=defaultdict(list)

filter = False
if(filter):
    extrafilename = "_filtered_median"
    extratitle = "Para realloc >0.4 (mediana)"
else:
    extrafilename = ""
    extratitle = ""


for index,row in stats_df.iterrows():
    if(row['realloc_rate'] in [0.05,0.35,0.45,0.55,0.65,0.75,0.95]):
        continue

    if(filter and row['resize_rate'] < 0.4):
        continue

    pop_resize_dict[(row['resize_rate'],row['population'])].append(row['maxScore'])
    pop_gen_dict[(row['generation'],row['population'])].append(row['maxScore'])
    mutation_dict[(row['realloc_rate'],row['resize_rate'])].append(row['maxScore'])
    elite_gen_dict[(round(row['elite']/row['population'],2),row['generation'])].append(row['maxScore'])
    elite_pop_dict[(round(row['elite']/row['population'],2),row['population'])].append(row['maxScore'])

pop_gen_df = pd.DataFrame(columns=['generation','population','score'])
mutation_df = pd.DataFrame(columns=['realloc_rate','resize_rate','score'])
elite_gen_df = pd.DataFrame(columns=['elite','generation','score'])
elite_pop_df = pd.DataFrame(columns=['elite','population','score'])
for key,values in pop_gen_dict.items():
    pop_gen_dict[key] = mean(values)
    temp_df = pd.DataFrame({'generation': int(key[0]),'population':int(key[1]),'score': mean(values)},index = [0])
    pop_gen_df = pd.concat([pop_gen_df,temp_df])

for key,values in mutation_dict.items():
    if(key[0] in [0.05,0.35,0.45,0.55,0.65,0.75,0.95]):
        continue
    temp_df = pd.DataFrame({'realloc_rate': key[0],'resize_rate':key[1],'score': mean(values)},index = [0])
    mutation_df = pd.concat([mutation_df,temp_df])

for key,values in elite_gen_dict.items():
    if(key[0] > 0.2):
        continue

    elite_gen_dict[key] = mean(values)
    temp_df = pd.DataFrame({'generation': int(key[1]),'elite':key[0],'score': mean(values)},index = [0])
    elite_gen_df = pd.concat([elite_gen_df,temp_df])

for key,values in elite_pop_dict.items():
    if(key[0] > 0.2):
        continue

    elite_pop_dict[key] = mean(values)
    temp_df = pd.DataFrame({'population': int(key[1]),'elite':key[0],'score': mean(values)},index = [0])
    elite_pop_df = pd.concat([elite_pop_df,temp_df])

elite_gen_df_pivot = elite_gen_df.pivot(index = 'elite',columns = 'generation',values='score')
ax = sns.heatmap(elite_gen_df_pivot, cmap='coolwarm')
ax.invert_yaxis()
ax.set_title(f"Tamanho relativo do grupo de elite x número de gerações \n{extratitle}")
plt.savefig(f"elite_gen{extrafilename}.png")
plt.clf()
plt.cla()
plt.close()

plt.scatter(stats_df['generation'],stats_df['maxScore'])
plt.title("Geração x MaxScore")
plt.savefig(f"gen{extrafilename}.png")
plt.clf()
plt.cla()
plt.close()

plt.scatter(stats_df['population'],stats_df['maxScore'])
plt.title("População x MaxScore")
plt.savefig(f"Pop{extrafilename}.png")
plt.clf()
plt.cla()
plt.close()


elite_pop_df_pivot = elite_pop_df.pivot(index = 'elite',columns = 'population',values='score')
ax = sns.heatmap(elite_pop_df_pivot, cmap='coolwarm')
ax.set_title(f"Tamanho relativo do grupo de elite x tamanho da população\n{extratitle}")
ax.invert_yaxis()
plt.savefig(f"elite_pop{extrafilename}.png")
plt.clf()
plt.cla()
plt.close()



#print(pop_gen_df)
pop_gen_df_pivot = pop_gen_df.pivot(index = 'generation',columns = 'population',values='score')
ax = sns.heatmap(pop_gen_df_pivot, cmap='coolwarm')
ax.invert_yaxis()
ax.set_title(f"Número de gerações e população\n{extratitle}")
plt.savefig(f"pop_gen{extrafilename}.png")
plt.clf()
plt.cla()
plt.close()


mutation_df_pivot = mutation_df.pivot(index = 'resize_rate',columns = 'realloc_rate',values='score')
ax = sns.heatmap(mutation_df_pivot, cmap='coolwarm')
ax.set_title(f"Relação entre valores de mutação\n{extratitle}")
ax.invert_yaxis()
plt.savefig(f"mutation{extrafilename}.png")
plt.clf()
plt.cla()
plt.close()




