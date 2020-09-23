#!/bin/bash

### Run through read directory
### Create a temporary directory to hold files with the name of the read directory
### Send to C3POa 4 threads 1000 files per thread

### For now the file will be just be a test. Want to see how long it takes. 

data_path=/mnt/home/smaguire/work/r2c2/r2c2_dd/data/DD_aug_7_blue_noblue/20200807_1510_X5_FAO16912_6c0acd68/fastq_pass/barcode01/
for i in $( ls $data_path/*.fastq); do
new_name=${file#$data_path}
new_name=${new_name%.fastq}
current_dir=/mnt/home/smaguire/work/r2c2/r2c2_dd/c3poa_output/$new_name
mkdir -p $current_dir

qsub -v reads=$file,current_d=$current_dir,name=$new_name c3poa.sh

done
