#!/bin/bash
#
#$ -cwd
#$ -j y
#$ -S /bin/bash
#$ -pe smp 4
#$ -m e

python C3POa.py \
-r ${reads} \
-p ${current_d} \
-m /mnt/home/smaguire/work/r2c2/r2c2_dd/c3poa_mod/resources/C3POa/NUC.4.4.mat \
-d 1000 \
-l 1500 \
-c /mnt/home/smaguire/work/r2c2/r2c2_dd/c3poa_mod/config.txt \
-n 4 \
-g 1000