### Graphing results   

library(tidyverse)
setwd("/Users/smaguire/Desktop/lab notebook - one note/DD_circRNA/blue_noblue")

read_data<-function(aln_stats_file,treatment_name){
  read_delim(aln_stats_file,delim="\t",
           col_names=c("read_id","aux_id","full_len",
                      "rpt_num","consensus_len",
                      "global_match","global_mismatch","global_edits",
                      "global_aln_score","global_per_id",
                      "local_match","local_mismatch","local_edits",
                      "local_aln_score","local_per_id")) %>%
    mutate(treatment = treatment_name)
}

bc2<-read_data("barcode2_alignment_stats.txt","No Blue Pippen")
bc1<-read_data("barcode1_alignment_stats.txt","Blue Pippen")

full_dataset<-bind_rows(bc1,bc2)

full_dataset<-
full_dataset %>% mutate(rpt_cat = ifelse(rpt_num+1 < 15,as.character(rpt_num+1),">=15"),
               rpt_cat = factor(rpt_cat,levels=c("1","2","3","4","5",
                                                 "6","7","8","9","10",
                                                 "11","12","13","14",
                                                 ">=15")))
library(cowplot)
filter(full_dataset) %>%
ggplot(aes(x=rpt_cat, y=local_per_id))+geom_jitter(col="gray70",alpha=0.05,size=0.5)+
  geom_boxplot(outlier.alpha = 0) + theme_cowplot() +
  facet_wrap(~treatment) + ylab("Percent Identity") +
  xlab("Number of Repeats")

ggplot(bc2,aes(x=global_aln_score,y=local_aln_score))+
  geom_point()


ggplot(full_dataset,aes(x=treatment,y=full_len))+geom_violin()+
  scale_y_log10()+ylab("Original Sequence Length")

ggplot(full_dataset,aes(x=rpt_cat, y=consensus_len))+geom_jitter(col="gray70",alpha=0.1)+
  geom_boxplot(outlier.alpha = 0) + theme_cowplot() +
  facet_wrap(~treatment) + ylab("Consensus Sequence Length (log scale)")+
  xlab("Number of Repeats") + 
  scale_y_log10()

