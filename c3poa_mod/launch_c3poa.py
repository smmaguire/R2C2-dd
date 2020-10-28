#!/bin/bash

### Run through read directory
### Create a temporary directory to hold files with the name of the read directory
### Send to C3POa 4 threads 1000 files per thread

### For now the file will be just be a test. Want to see how long it takes. 

data_path="/mnt/home/smaguire/work/r2c2/r2c2_dd/data/human_brain_9182020/fastq/fastq_pass/barcode01"
for i in $( ls $data_path*.fastq); do
new_name=${i#$data_path}
new_name=${new_name%.fastq}
current_dir=/mnt/home/smaguire/work/r2c2/r2c2_dd/c3poa_human_output/$new_name
mkdir -p $current_dir
echo $current_dir
echo $new_name

qsub -v reads=$i,current_d=$current_dir,name=$new_name c3poa.sh

done
