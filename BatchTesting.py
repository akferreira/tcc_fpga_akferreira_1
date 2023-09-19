import os,subprocess

TOPOLOGY_DIR = "topology"
MUTATION_PARAMS = [[0.25,0.5],[0.4,0.8],[0.5,0.5],[0.8,0.4],[0.5,0.25],[0.1,0.2],[0.2,0.8]]
POP_SIZE = 200
ELITE_SIZES = [20,40]
count = 0
files = ["topologia_N10L12_0.json","topologia_N10L12_6.json"]

file = "topologia_N10L12_4.json"

subprocess.run(['python', 'main.py', '--recreate', f'{POP_SIZE}', '--cpu', '3', '--topology-dir', 'topology',
                    '--topology-filename', file])  # --topology-filename {file}
for params in MUTATION_PARAMS:
    realloc_rate, resize_rate = params[0], params[1]
    for elite in ELITE_SIZES:
        subprocess.run(['python', 'main.py', '--ga', '--cpu', '3', '--realloc-rate', f'{realloc_rate}', '--resize-rate',
                        f'{resize_rate}',
                        '--elite', f'{elite}', '--iterations', '30', '--topology-dir', 'topology',
                        '--topology-filename', f'{file}'])

for file in files:
    print(file)
    subprocess.run(['python', 'main.py', '--recreate', f'{POP_SIZE}', '--cpu', '3', '--topology-dir', 'topology',
                    '--topology-filename', file])  # --topology-filename {file}

    for params in MUTATION_PARAMS:
        realloc_rate, resize_rate = params[0],params[1]
        for elite in ELITE_SIZES:
            subprocess.run(['python','main.py','--ga','--cpu','3', '--realloc-rate',f'{realloc_rate}', '--resize-rate' ,f'{resize_rate}',
                             '--elite', f'{elite}' ,'--iterations', '30', '--topology-dir', 'topology' , '--topology-filename',f'{file}'])

