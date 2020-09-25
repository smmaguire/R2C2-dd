library(readr)
library(Biostrings)
library(stringr)
library(dplyr)

aln_stats<-function(alignment,reference){
  ref_len<-str_length(reference)
  edits<-nedit(alignment)
  matches<-nmatch(alignment)
  mismatches<-nmismatch(alignment)
  per_id<-round(((ref_len-edits)/ref_len)*100,2)
  aln_score<-round(score(alignment),2)
  paste(matches,mismatches,edits,aln_score,per_id,sep="\t")
}

#arg1 = path to blast output file
#arg2 = path to fasta file
#arg3 = name of output file

reference<-DNAString("AAAATCCGTTGACCTTAAACGGTCGTGTGGGTTCAAGTCCCTCCACCCCCACGCCGGAAACGCAATAGCCGAAAAACAAAAAACAAAAAAACCCCCCTCTCCCTCCCCCCCTAACGTTACTGGCCGAAGCCGCTTGGAATAAGGCCGGTGTGCGTTTGTCTATATGTTATTTTCCACCATATTGCCGTCTTTTGGCAATGTGAGGGCCCGGAAACCTGGCCCTGTCTTCTTGACGAGCATTCCTAGGGGTCTTTCCCCTCTCGCCAAAGGAATGCAAGGTCTGTTGAATGTCGTGAAGGAAGCAGTTCCTCTGGAAGCTTCTTGAAGACAAACAACGTCTGTAGCGACCCTTTGCAGGCAGCGGAACCCCCCACCTGGCGACAGGTGCCTCTGCGGCCAAAAGCCACGTGTATAAGATACACCTGCAAAGGCGGCACAACCCCAGTGCCACGTTGTGAGTTGGATAGTTGTGGAAAGAGTCAAATGGCTCTCCTCAAGCGTATTCAACAAGGGGCTGAAGGATGCCCAGAAGGTACCCCATTGTATGGGATCTGATCTGGGGCCTCGGTGCACATGCTTTACATGTGTTTAGTCGAGGTTAAAAAACGTCTAGGCCCCCCGAACCACGGGGACGTGGTTTTCCTTTGAAAAACACGATGATAATATGGCCACAACCATGGGAGTCAAAGTTCTGTTTGCCCTGATCTGCATCGCTGTGGCCGAGGCCAAGCCCACCGAGAACAACGAAGACTTCAACATCGTGGCCGTGGCCAGCAACTTCGCGACCACGGATCTCGATGCTGACCGCGGGAAGTTGCCCGGCAAGAAGCTGCCGCTGGAGGTGCTCAAAGAGATGGAAGCCAATGCCCGGAAAGCTGGCTGCACCAGGGGCTGTCTGATCTGCCTGTCCCACATCAAGTGCACGCCCAAGATGAAGAAGTTCATCCCAGGACGCTGCCACACCTACGAAGGCGACAAAGAGTCCGCACAGGGCGGCATAGGCGAGGCGATCGTCGACATTCCTGAGATTCCTGGGTTCAAGGACTTGGAGCCCATGGAGCAGTTCATCGCACAGGTCGATCTGTGTGTGGACTGCACAACTGGCTGCCTCAAAGGGCTTGCCAACGTGCAGTGTTCTGACCTGCTCAAGAAGTGGCTGCCGCAACGCTGTGCGACCTTTGCCAGCAAGATCCAGGGCCAGGTGGACAAGATCAAGGGGGCCGGTGGTGACTAAAAAAAACAAAAAACAAAACGGCTATTATGCGTTACCGGCGAGACGCTACGGACTT")

args = commandArgs(trailingOnly=TRUE)

# read in the blast file
blast_out<-read_delim(args[1],col_names=c("qseqid","sseqid","pident","length","mismatch","gapopen",
                               "qstart","qend","sstart","send","evalue","bitscore"),
           delim="\t")

#iterate through fasta and: 
## pull out the name, original sequence length, number of repeats from header
## pull up blast hit for the read, rotate sequence to match blast position and orientation
## align rotated read to original reference file and get alignment scores 
## output new fasta with sequences rotated and oriented. 
## output table with sequence records.  

#args<-c("/Users/smaguire/Desktop/lab notebook - one note/DD_circRNA/FAO16912_pass_barcode02_b21fa6ca_0_aln.tab",
 #       "/Users/smaguire/Desktop/lab notebook - one note/DD_circRNA/FAO16912_pass_barcode02_b21fa6ca_0_Consensus.fasta")
con  <- file(args[2], open = "r")
fileCon<-file(paste(args[3],"alignment_stats.txt",sep="_"),open = "w")
fastaCon<-file(paste(args[3],"rotated_consensus_seq.fasta",sep="_"),open = "w")
while ( TRUE ) {
  lines = readLines(con, n = 2)
  if ( length(lines[1]) == 0 ) {
    break
  }
  current.id<-str_split(lines[1],">",simplify=T)[,2]
  info_line<-paste(str_split(current.id,pattern = "_",simplify=T),collapse="\t")
  filtered.blast<-filter(blast_out,qseqid == current.id,bitscore > 50)
  if(nrow(filtered.blast) == 0){
    next
  }
  # Determine if the read is aligning forward or reverse.
  longest.alignment<-filter(filtered.blast, length == max(length))
  if(longest.alignment$send-longest.alignment$sstart > 0){
    orientation <- "fwd"
  } else{
    orientation <- "rev"
  }
  if(orientation == "fwd") {
    ## find the longest position in the send column. orient the read to that, 
    ### so that qend of that row is now the end of the sequence. 
    far.pos<-filter(filtered.blast,send == max(send))
    #just in case there is more than one alignment within it
    if(nrow(far.pos) > 1 ){
      far.pos<-far.pos[order(far.pos$bitscore,decreasing = T),][1,]
    }
    rotated.seq.p2<-str_sub(lines[2],start=far.pos$qstart,end=far.pos$qend)
    rotated.seq.p3<-str_sub(lines[2],start=far.pos$qend+1)
    rotated.seq.p1<-str_sub(lines[2],end=far.pos$qstart-1)
    rotated.seq.final<-str_c(rotated.seq.p3,rotated.seq.p1,rotated.seq.p2)
    globalAlign<-pairwiseAlignment(reference,rotated.seq.final,type="global",gapOpening=5,gapExtension=2)
    localAlign<-pairwiseAlignment(reference,rotated.seq.final,type="local",gapOpening=5,gapExtension=2)
  }
  
  if(orientation == "rev") {
    far.pos<-filter(filtered.blast,sstart == max(sstart))
    if(nrow(far.pos) > 1 ){
      far.pos<-far.pos[order(far.pos$bitscore,decreasing = T),][1,]
    }
    rotated.seq.p2<-str_sub(lines[2],start=far.pos$qstart,end=far.pos$qend)
    rotated.seq.p3<-str_sub(lines[2],start=far.pos$qend+1)
    rotated.seq.p1<-str_sub(lines[2],end=far.pos$qstart-1)
    rotated.seq.final<-str_c(rotated.seq.p2,rotated.seq.p1,rotated.seq.p3) %>%
      DNAString() %>%
      reverseComplement()
    globalAlign<-pairwiseAlignment(reference,rotated.seq.final,type="global",gapOpening=5,gapExtension=2)
    localAlign<-pairwiseAlignment(reference,rotated.seq.final,type="local",gapOpening=5,gapExtension=2)
  }
  globalAlnStats<-aln_stats(globalAlign,reference)
  localAlnStats<-aln_stats(localAlign,reference)
  write_lines(paste(info_line,globalAlnStats,localAlnStats,sep="\t"),path=fileCon,append=T)
  write_lines(lines[1],path=fastaCon,append=T)
  write_lines(as.character(rotated.seq.final),path=fastaCon,append=T)
}

close(fileCon)
close(con)


