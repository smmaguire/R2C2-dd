#!/bin/bash

find . -type f -name '*_alignment_stats.txt' |
    while IFS= read file_name; do
        cat "$file_name" >> "barcode2_alignment_stats.txt"
    done

find . -type f -name '*_rotated_consensus_seq.fasta' |
    while IFS= read file_name; do
        cat "$file_name" >> "barcode2_rotated_consensus_seqs.txt"
    done