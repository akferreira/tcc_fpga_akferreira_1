for population in {225..500..25};do
    python main.py --recreate "$population" --cpu 7 --topology-filename topology_N10_0.json;
    for i in {1..4};do
        python main.py --ga --iterations 30 --topology-filename topology_N10_0.json --cpu 7 --elitep 0.1;
    done
done
