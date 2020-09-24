#!/bin/bash
#
#$ -cwd
#$ -j y
#$ -S /bin/bash
#$ -pe smp 4
#$ -m e

source activate C3POa

# Run python
# python C3POa.py \
# -r ${reads} \
# -p ${current_d} \
# -m /mnt/home/smaguire/work/r2c2/r2c2_dd/c3poa_mod/resources/C3POa/NUC.4.4.mat \
# -d 1000 \
# -l 1500 \
# -c /mnt/home/smaguire/work/r2c2/r2c2_dd/c3poa_mod/config.txt \
# -n 4 \
# -g 1000 \
# -s ${name}

# blast the output
cd ${current_d}

makeblastdb -in ${name}_Consensus.fasta -parse_seqids -dbtype 'nucl'

########## Blast the adapter sequence against the blast database
blastn \
-query /mnt/home/smaguire/work/r2c2/r2c2_dd/c3poa_mod/reference.fasta \
-subject ${name}_Consensus.fasta \
-task "blastn-short" \
-word_size 10 \
-gapopen 5 \
-gapextend 2 \
-outfmt 6 \
-evalue 1000 \
-penalty -3 \
-reward 1 \
-num_alignments 10 \
> ${name}"_aln.tab"

