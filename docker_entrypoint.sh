#!/bin/bash

# run phase1
python3 /phase1.py -w /temp
# run phase2
python3 /phase2.py -w /temp -e /encodings/encodings_28_Jun_20.pickle
# print /temp/data.csv output file
python3 /print_results.py