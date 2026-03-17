rm(list=ls())

library(ggplot2)
library(ggrepel)

setwd("~/Google Drive/Working Papers/00 Groundwater Commons Game (NATURE)/WVS6")
load("~/Google Drive/Working Papers/00 Groundwater Commons Game (NATURE)/WVS6/R_WVS6.rdata")
min_max_scale<-read.csv(file="~/Google Drive/Working Papers/00 Groundwater Commons Game (NATURE)/WVS6/min_max_scale.csv")

# grid_questions <- c("V9","V45","V164","V21","V58","V69","V152","V203","V203A","V204","V205","V79","V201","V200","V77")
# group_questions <- c("V4","V5","V24","V56","V71","V8","V68","V97","V98","V20","V12","V74","V78","V216","V213")

grid_questions <- c("V9","V164","V21","V69","V152","V203","V203A","V204","V200","V77")
group_questions <- c("V4","V5","V24","V71","V98","V20","V74","V78","V216","V213")

all_country_codes <- read.csv("WVS_country_codes.csv")

a<-unique(WV6_Data_R[2])
a$name <- match(a$V2,all_country_codes$code)
a[2] <- apply(a[2],2,function(x) all_country_codes[x,2])
WVS6_countries=a
rm(a)
all_names<-WVS6_countries$name
all_codes<-WVS6_countries$V2

#store results in this dataframe
country_scores <- data.frame()

for (i in 1:length(all_names))
{
  #CHOOSE COUNTRY;EXTRACT GRID/GROUP DATAFRAMES  
  this_country<-all_names[i]
  this_code <- all_codes[i]
  df_grid <- subset(x=WV6_Data_R, subset = (V2 == this_code), select = grid_questions)
  df_group <- subset(x=WV6_Data_R, subset = (V2 == this_code), select = group_questions)
  
  #REMOVE NON-RESPONSES
  df_grid[df_grid < 0] <- NA
  df_group[df_group < 0] <- NA
  
  ###CALCULATE GRID SCORES
  for(i in 1:ncol(df_grid))
  {
    header <- colnames(df_grid[i])
    min <- as.numeric(subset(min_max_scale,var == header,select  = c("min")))
    max <- as.numeric(subset(min_max_scale,var == header,select  = c("max")))
    invert <- as.numeric(subset(min_max_scale,var == header,select  = c("invert")))
    df_grid[i] <- (df_grid[i]-min)/(max-min)
    if(invert == 1){df_grid[i]=(1-df_grid[i])}
  }
  
  tmp_grid <- do.call(data.frame, 
                      list(
                        mean = apply(df_grid, 2, function(x){mean(x,na.rm=TRUE)}),
                        sd = apply(df_grid, 2, function(x){sd(x,na.rm=TRUE)}),
                        min = apply(df_grid, 2, function(x){min(x,na.rm=TRUE)}),
                        max = apply(df_grid, 2, function(x){max(x,na.rm=TRUE)}),
                        n = apply(df_grid, 2, function(x){sum(!is.na(x))})
                      )
  )
  
  
  ###CALCULATE GROUP SCORES
  for(i in 1:ncol(df_group))
  {
    header <- colnames(df_group[i])
    min <- as.numeric(subset(min_max_scale,var == header,select  = c("min")))
    max <- as.numeric(subset(min_max_scale,var == header,select  = c("max")))
    invert <- as.numeric(subset(min_max_scale,var == header,select  = c("invert")))
    df_group[i] <- (df_group[i]-min)/(max-min)
    if(invert == 1){df_group[i]=(1-df_group[i])}
  }
  
  tmp_group <- do.call(data.frame, 
                       list(
                         mean = apply(df_group, 2, function(x){mean(x,na.rm=TRUE)}),
                         sd = apply(df_group, 2, function(x){sd(x,na.rm=TRUE)}),
                         min = apply(df_group, 2, function(x){min(x,na.rm=TRUE)}),
                         max = apply(df_group, 2, function(x){max(x,na.rm=TRUE)}),
                         n = apply(df_group, 2, function(x){sum(!is.na(x))})
                       )
  )
  
  tmp_grid <- tmp_grid[complete.cases(tmp_grid), ]
  tmp_group <- tmp_group[complete.cases(tmp_group), ]
  
  newrow<-data.frame(
    grid_mean=as.numeric(apply(tmp_grid[1],2,mean)),
    grid_sd=as.numeric(apply(tmp_grid[1],2,sd)),
    group_mean=as.numeric(apply(tmp_group[1],2,mean)),
    group_sd=as.numeric(apply(tmp_group[1],2,sd)),
    N=nrow(df_grid)
  )
  
  row.names(newrow)<-this_country
  country_scores <- rbind(country_scores,newrow)
}

###########################################
########### PLOT ALL COUNTRIES ############
###########################################

###GRID-GROUP MEAN VALUES
group_mean<-colMeans(country_scores)[3]
grid_mean<-colMeans(country_scores)[1]

###ISOLATE COUNTRIES WITH MAJOR AQUIFERS
aquifer_country_names <- c("Argentina","Spain","South Africa","United States","India","Pakistan","China","Mexico","Egypt","Algeria","Tunisia","Libya","Romania","Australia","Algeria","Morocco","Colombia", "Uruguay", "Brazil")
rows.to.keep<-which(rownames(country_scores) %in% aquifer_country_names)
aquifer_country_scores <- country_scores[rows.to.keep,]

### PLOT — ALL COUNTRIES, NO ERROR BARS, ZOOMED
plot(country_scores$group_mean,country_scores$grid_mean, col="red", ylab='', xlab='', pch=19)
points(aquifer_country_scores$group_mean,aquifer_country_scores$grid_mean, col="blue",ylab='', xlab='',pch=19)
text(country_scores$group_mean, country_scores$grid_mean, labels=rownames(country_scores), cex=0.7, pos=1)
text(aquifer_country_scores$group_mean, aquifer_country_scores$grid_mean, labels=rownames(aquifer_country_scores), cex=0.7, pos=1)
title(main="WVS6 grid-group analysis (all countries)", ylab="Group (reputation)", xlab="Grid (altruistic)")
abline(h=grid_mean, v=group_mean)
text(0.465,0.4, labels="INDIVIDUALIST", cex=1)
text(0.6,0.8, labels="HIERARCHIST", cex=1)
text(0.6,0.4, labels="EGALITARIAN", cex=1)
text(0.465,0.8, labels="FATALIST", cex=1)

### PLOT — ALL COUNTRIES, ERROR BARS, NOT ZOOMED
plot(country_scores$group_mean,country_scores$grid_mean, col="red", ylab='', xlab='', pch=19,,xlim=c(0,1), ylim=c(0,1))
points(aquifer_country_scores$group_mean,aquifer_country_scores$grid_mean, col="blue",ylab='', xlab='',pch=19)
text(country_scores$group_mean, country_scores$grid_mean, labels=rownames(country_scores), cex=0.7, pos=1)
text(aquifer_country_scores$group_mean, aquifer_country_scores$grid_mean, labels=rownames(aquifer_country_scores), cex=0.7, pos=1)
title(main="WVS6 grid-group analysis (all countries)", xlab="Group (altruistic values)", ylab="Grid (reputational values)")
abline(h=grid_mean, v=group_mean)
arrows(country_scores$group_mean, country_scores$grid_mean-country_scores$grid_sd, country_scores$group_mean, country_scores$grid_mean+country_scores$grid_sd, length=0.05, angle=90, code=3)
arrows(country_scores$group_mean-country_scores$group_sd, country_scores$grid_mean, country_scores$group_mean+country_scores$group_sd, country_scores$grid_mean, length=0.05, angle=90, code=3)


##########################################
########### NORMALIZED SCORES ############
##########################################

min_group <- min(country_scores$group_mean)
max_group <- max(country_scores$group_mean)
min_grid <- min(country_scores$grid_mean)
max_grid <- max(country_scores$grid_mean)

grid_norm <- data.frame(apply(country_scores[1],2,function(x) (x-min_grid)/(max_grid-min_grid)))
group_norm <- data.frame(apply(country_scores[3],2,function(x) (x-min_group)/(max_group-min_group)))
country_scores_norm <- cbind(grid_norm,group_norm)

###GRID-GROUP MEAN VALUES
group_mean_norm<-colMeans(country_scores_norm)[2]
grid_mean_norm<-colMeans(country_scores_norm)[1]

###ISOLATE COUNTRIES WITH MAJOR AQUIFERS
aquifer_country_names <- c("Argentina","Spain","South Africa","United States","India","Pakistan","China","Mexico","Egypt","Algeria","Tunisia","Libya","Romania","Australia","Algeria","Morocco","Colombia", "Uruguay", "Brazil")
rows.to.keep<-which(rownames(country_scores_norm) %in% aquifer_country_names)
aquifer_country_scores_norm <- country_scores_norm[rows.to.keep,]

### PLOT — ALL COUNTRIES, NO ERROR BARS, ZOOMED
plot(country_scores_norm$group_mean,country_scores_norm$grid_mean, col="red", ylab='', xlab='', pch=19)
points(aquifer_country_scores_norm$group_mean,aquifer_country_scores_norm$grid_mean, col="blue",ylab='', xlab='',pch=19)
text(country_scores_norm$group_mean, country_scores_norm$grid_mean, labels=rownames(country_scores_norm), cex=0.8, pos=1)
text(aquifer_country_scores_norm$group_mean, aquifer_country_scores_norm$grid_mean, labels=rownames(aquifer_country_scores_norm), cex=0.8, pos=1)
title(main="WVS6 grid-group analysis (all countries)  — normalised scores", ylab="Group (reputation)", xlab="Grid (altruistic)")
abline(h=grid_mean, v=group_mean)
text(0.1,0, labels="INDIVIDUALIST", cex=1)
text(0.9,1, labels="HIERARCHIST", cex=1)
text(0.9,0, labels="EGALITARIAN", cex=1)
text(0.1,1, labels="FATALIST", cex=1)

### PLOT — COUNTRIES WITH MAJOR AQUIFERS, NO ERROR BARS, ZOOMED
plot(aquifer_country_scores_norm$group_mean,aquifer_country_scores_norm$grid_mean, col="blue",ylab='', xlab='',pch=19, xlim = c(0,1),ylim=c(0,1))
text(aquifer_country_scores_norm$group_mean, aquifer_country_scores_norm$grid_mean, labels=rownames(aquifer_country_scores_norm), cex=0.8, pos=1)
title(main="WVS6 grid-group statistics — normalised scores", xlab="Group", ylab="Grid")
abline(h=grid_mean, v=group_mean)
abline(h=0.5, v=0.5, lty=3)
text(0.1,0, labels="INDIVIDUALIST", cex=1)
text(0.9,1, labels="HIERARCHIST", cex=1)
text(0.9,0, labels="EGALITARIAN", cex=1)
text(0.1,1, labels="FATALIST", cex=1)

##########################################
########### CALCULATE F VALUES ###########
##########################################

df_grid <- subset(x=WV6_Data_R, select = c("V2",grid_questions))
df_group <- subset(x=WV6_Data_R, select = c("V2",group_questions))

# ADD NAs WHERE NEEDED
df_grid[df_grid < 0] <- NA
df_group[df_group < 0] <- NA

### NORMALISE GRID SCORES
for(i in 2:ncol(df_grid))
{
  header <- colnames(df_grid[i])
  min <- as.numeric(subset(min_max_scale,var == header,select  = c("min")))
  max <- as.numeric(subset(min_max_scale,var == header,select  = c("max")))
  invert <- as.numeric(subset(min_max_scale,var == header,select  = c("invert")))
  df_grid[i] <- (df_grid[i]-min)/(max-min)
  if(invert == 1){df_grid[i]=(1-df_grid[i])}
}

### NORMALISE GROUP SCORES
for(i in 2:ncol(df_group))
{
  header <- colnames(df_group[i])
  min <- as.numeric(subset(min_max_scale,var == header,select  = c("min")))
  max <- as.numeric(subset(min_max_scale,var == header,select  = c("max")))
  invert <- as.numeric(subset(min_max_scale,var == header,select  = c("invert")))
  df_group[i] <- (df_group[i]-min)/(max-min)
  if(invert == 1){df_group[i]=(1-df_group[i])}
}

column_means_grid <- colMeans(df_grid, na.rm = TRUE)
column_means_group <- colMeans(df_group, na.rm = TRUE)

column_sd_grid <- apply(df_grid,2,sd,na.rm=TRUE)
column_sd_group <- apply(df_group,2,sd,na.rm=TRUE)

result_grid <- rbind(column_means_grid,column_sd_grid)
result_group <- rbind(column_means_group,column_sd_group)

rownames(result_grid) <- c("mean", "sd")
rownames(result_group) <- c("mean", "sd")

result_grid <- result_grid[1:2,-1]
result_group <- result_group[1:2,-1]

### DEFINE FUNCTION THAT CALCULATES F-VALUES
f <- function(df,i)
{
  df_i <- df[,c("V2",colnames(df[i]))]
  form <- as.formula(paste(colnames(df_i[2]),"~","V2"))
  results <- anova(lm(formula = form , data = df_i, na.action="na.exclude"))
  f_value <- c(results[1,4],results[1,5])
  return(f_value)
}

### F-VALUES FOR GRID QUESTIONS
F_values_grid <- data.frame(F_value=NA, significance=NA)

for(i in 2:ncol(df_grid))
{
  F_values_grid[i-1,] <- f(df_grid,i)
}

### F-VALUES FOR GROUP QUESTIONS
F_values_group <- data.frame(F_value=NA, significance=NA)

for(i in 2:ncol(df_group))
{
  F_values_group[i-1,] <- f(df_group,i)
}

result_grid <- round(rbind(result_grid,t(F_values_grid)), digits = 4)
result_group <- round(rbind(result_group,t(F_values_group)), digits = 4)

result_grid
result_group

##########################################################################
########### WVS6 GRID-GROUP ANALYSIS BOXPLOTS — ALL COUNTRIES ############
##########################################################################

temp_grid_df <- data.frame(Country=df_grid[,1], "Grid score"=rowMeans(df_grid[,-1],na.rm = TRUE))
temp_group_df <- data.frame(Country=df_group[,1], "Group score"=rowMeans(df_group[,-1],na.rm = TRUE))

matches=match(temp_grid_df$Country,all_country_codes$code)
a=all_country_codes[matches,]
temp_grid_df[1]<-a$country

matches=match(temp_group_df$Country,all_country_codes$code)
a=all_country_codes[matches,]
temp_group_df[1]<-a$country

aquifer_colour="cornflowerblue"

temp_grid_df$Country <- with(temp_grid_df, reorder(Country, Grid.score, median))
p <- ggplot(temp_grid_df,aes(x=Country,y=Grid.score, fill=Country))
p +
  geom_boxplot() +
  coord_flip() +
  theme(text=element_text(size=14),
        legend.position="none",
        axis.text.x = element_text(angle = 90, hjust = 1, vjust=0.5),
        axis.title.x = element_text(face="bold"),
        axis.title.y = element_text(face="bold"),
        plot.title = element_text(face="bold")) +
  labs(x="Country", y="GRID") +
  scale_fill_manual(values=ifelse(levels(temp_grid_df$Country)=="Argentina", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Spain", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="South Africa", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="China", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Romania", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Morocco", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Chile", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Argentina", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Egypt", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Colombia", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Uruguay", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Brazil", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Ecuador", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Peru", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Iraq", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Yemen", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Mexico", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Algeria", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Tunisia", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Libya", aquifer_colour,
                                  ifelse(levels(temp_grid_df$Country)=="Australia", "red",
                                  ifelse(levels(temp_grid_df$Country)=="India", "red",
                                  ifelse(levels(temp_grid_df$Country)=="Pakistan", "red", 
                                  ifelse(levels(temp_grid_df$Country)=="United States", "red",
                                  "white")))))))))))))))))))))))))

temp_group_df$Country <- with(temp_group_df, reorder(Country, Group.score, median))
p <- ggplot(temp_group_df,aes(x=Country,y=Group.score,fill=Country))
p +
  geom_boxplot() +
  coord_flip() +
  theme(text=element_text(size=14),
        legend.position="none",
        axis.text.x = element_text(angle = 90, hjust = 1, vjust=0.5),
        axis.title.x = element_text(face="bold"),
        axis.title.y = element_text(face="bold"),
        plot.title = element_text(face="bold")) +
  labs(y="GROUP", x="Country") +
  scale_fill_manual(values=ifelse(levels(temp_group_df$Country)=="Argentina", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Spain", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="South Africa", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="China", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Romania", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Morocco", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Chile", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Argentina", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Egypt", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Colombia", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Uruguay", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Brazil", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Ecuador", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Peru", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Iraq", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Yemen", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Mexico", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Algeria", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Tunisia", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Libya", aquifer_colour,
                                  ifelse(levels(temp_group_df$Country)=="Australia", "red",
                                  ifelse(levels(temp_group_df$Country)=="India", "red",
                                  ifelse(levels(temp_group_df$Country)=="Pakistan", "red", 
                                  ifelse(levels(temp_group_df$Country)=="United States", "red",
                                  "white")))))))))))))))))))))))))

# 
# ###########################################################################
# ########### WVS6 GRID-GROUP ANALYSIS BOXPLOTS — MAJOR AQUIFERS ############
# ###########################################################################
# 
temp_grid_df <- data.frame(Country=df_grid[,1], "Grid score"=rowMeans(df_grid[,-1],na.rm = TRUE))
temp_group_df <- data.frame(Country=df_group[,1], "Group score"=rowMeans(df_group[,-1],na.rm = TRUE))

matches=match(temp_grid_df$Country,all_country_codes$code)
a=all_country_codes[matches,]
temp_grid_df[1]<-a$country

matches=match(temp_group_df$Country,all_country_codes$code)
a=all_country_codes[matches,]
temp_group_df[1]<-a$country

###ISOLATE COUNTRIES WITH MAJOR AQUIFERS
aquifer_country_names <- c("Argentina","Spain","South Africa","United States","India","Pakistan","China","Mexico","Egypt","Algeria","Tunisia","Libya","Romania","Australia","Algeria","Morocco","Colombia", "Uruguay", "Brazil")
rows.to.keep<-which(temp_grid_df$Country %in% aquifer_country_names)
temp_grid_df <- temp_grid_df[rows.to.keep,]
temp_group_df <- temp_group_df[rows.to.keep,]

temp_grid_df$Country <- with(temp_grid_df, reorder(Country, Grid.score, median))
p <- ggplot(temp_grid_df,aes(x=Country,y=Grid.score,fill=Country))
p +
  geom_boxplot() +
  theme(text=element_text(size=18),
        axis.text.x = element_text(angle = 90, hjust = 1, vjust=0.5),
        axis.title.x = element_text(face="bold"),
        axis.title.y = element_text(face="bold"),
        plot.title = element_text(face="bold")) +
  labs(title = "GRID SCORES — Countries with Major Aquifers", x="GRID SCORE", y="COUNTRY") +
  scale_fill_grey()

temp_group_df$Country <- with(temp_group_df, reorder(Country, Group.score, median))
p <- ggplot(temp_group_df,aes(x=Country,y=Group.score,fill=Country))
  p +
  geom_boxplot() +
  coord_flip() +
  theme(text=element_text(size=18),
        axis.text.x = element_text(angle = 90, hjust = 1, vjust=0.5),
        axis.title.x = element_text(face="bold"),
        axis.title.y = element_text(face="bold"),
        plot.title = element_text(face="bold")) +
  labs(title = "GROUP SCORES — Countries with Major Aquifers", y="GROUP SCORE", x="COUNTRY") +
  scale_fill_grey()

  ###################################################################
  ############### GROUP SIZE PLOTS — BASIC R PLOT  ##################
  ###################################################################
  
  # r <- read.csv("~/Google Drive/Papers/02 GNG/World Bank & FAO stats/average_area_per_holding.csv")
  # r[r=="..."]=NA
  # r <- r[complete.cases(r),]
  # r[2] <- sapply(r[2],as.character)
  # r[2] <- sapply(r[2],as.numeric)
  # r[1] <- sapply(r[1],as.character)
  # 
  # ### ADD MEXICO MANUALLY (ca. 5-50 hectares depending on state)
  # newrow <- c("Mexico",20)
  # r <- rbind(r,newrow)
  # 
  # ### EXTRACT AND BIND AVERAGE LAND AREA FOR COUNTRIES WITH MAJOR AQUIFERS
  # indices <- match(rownames(aquifer_country_scores),r$Country)
  # aquifer_country_scores <- cbind(aquifer_country_scores,r[indices,][2])
  # 
  # ### PREPARE CEX VECTOR TO PLOT DOT SIZES
  # min_area <- min(as.numeric(aquifer_country_scores$area))
  # max_area <- max(as.numeric(aquifer_country_scores$area))
  # area_norm <- (as.numeric(aquifer_country_scores$area)-min_area)/(max_area-min_area)
  # circle_sizes <-1/as.numeric(aquifer_country_scores$area)^(1/2)*10
  # 
  # ### PLOT — COUNTRIES WITH MAJOR AQUIFERS, NO ERROR BARS, ZOOMED
  # plot(aquifer_country_scores_norm$group_mean,aquifer_country_scores_norm$grid_mean, cex=circle_sizes, col="black",ylab='', xlab='',pch=21, bg=0,xlim = c(0,1),ylim=c(0,1))
  # text(aquifer_country_scores_norm$group_mean, aquifer_country_scores_norm$grid_mean, labels=rownames(aquifer_country_scores_norm), cex=0.8, pos=3)
  # title(main="WVS6 grid-group analysis (countries with major aquifers) — normalised scores", xlab="Group (altruistic values)", ylab="Grid (reputational values)")
  # abline(h=grid_mean, v=group_mean)
  # abline(h=0.5, v=0.5, lty=3)
  # text(0.1,0, labels="INDIVIDUALIST", cex=1)
  # text(0.9,1, labels="HIERARCHIST", cex=1)
  # text(0.9,0, labels="EGALITARIAN", cex=1)
  # text(0.1,1, labels="FATALIST", cex=1)
  
  ##################################################################
  ############### GROUP SIZE PLOTS — GGPLOT2  ######################
  ##################################################################
  
  ###ISOLATE COUNTRIES WITH MAJOR AQUIFERS
  aquifer_country_names <- c("Spain","South Africa", "China","Romania","Morocco","Chile","Argentina","Mexico","Egypt","Algeria","Tunisia","Libya","Algeria","Colombia", "Uruguay", "Brazil","Ecuador","Peru", "Iraq", "Yemen", "Tunisia","United States","India","Australia","Pakistan")
  #aquifer_country_names <- c("Argentina","Spain","South Africa","United States","India","Pakistan","China","Mexico","Egypt","Algeria","Tunisia","Libya","Romania","Australia","Algeria","Morocco","Colombia", "Uruguay", "Brazil")
  rows.to.keep<-which(rownames(country_scores_norm) %in% aquifer_country_names)
  aquifer_country_scores <- country_scores_norm[rows.to.keep,]

  r <- read.csv("~/Google Drive/Working Papers/00 Groundwater Commons Game (NATURE)/World Bank & FAO stats/average_area_per_holding.csv")
  r[r=="..."]=NA
  r <- r[complete.cases(r),]
  r[2] <- sapply(r[2],as.character)
  r[2] <- sapply(r[2],as.numeric)
  r[1] <- sapply(r[1],as.character)

  ### ADD MEXICO MANUALLY (ca. 5-50 hectares depending on state)
  newrow <- c("Mexico",20)
  r <- rbind(r,newrow)

  ### EXTRACT AND BIND AVERAGE LAND AREA FOR COUNTRIES WITH MAJOR AQUIFERS
  indices <- match(rownames(aquifer_country_scores),r$Country)
  aquifer_country_scores <- cbind(aquifer_country_scores,r[indices,][2])
  aquifer_country_scores <- aquifer_country_scores[complete.cases(aquifer_country_scores),]

  ### PREPARE CEX VECTOR TO PLOT DOT SIZES
    circle_sizes <-round(100000/as.numeric(aquifer_country_scores$area),digits = -1)

  ### PLOT
  p <- ggplot(aquifer_country_scores,aes(x=group_mean,y=grid_mean,label = rownames(aquifer_country_scores)))
  p  +
    geom_point(aes(colour=circle_sizes,size=circle_sizes),alpha = 0.7) +
    scale_colour_gradient("average # of land holdings per 1000 km2",breaks=c(0,30,30000,60000,90000,140000)) +
    scale_size("average # of land holdings per 1000 km2",range = c(1, 60),breaks=c(0,30,30000,60000,90000,140000)) +
    guides(color=guide_legend(title.position = "top",title.hjust = 0.5), size=guide_legend(title.position = "top",title.hjust = 0.5)) +
    geom_label_repel(size = 5, force = 25, nudge_x=-0.07) +
    ylab("GRID") + xlab("GROUP") +
    theme(axis.title.x = element_text(face="bold", size=20),
      axis.title.y = element_text(face="bold", size=20),
      axis.text.x = element_text(face="bold", size=14),
      axis.text.y = element_text(face="bold", size=14),
      legend.title=element_text(face="bold",size = 18),
      legend.position="bottom",
      legend.text=element_text(size = 14),
      legend.key=element_rect(fill=NA, colour = NA),
      legend.key.size=unit(0.1,"mm"),
      legend.key.height=unit(0.1,"mm"),
      legend.background = element_rect(fill = "white"),
      panel.border = element_rect(colour = "black",fill = NA)) +
    scale_x_continuous(limits = c(0,1)) +
    scale_y_continuous(limits = c(0,1)) +
    coord_fixed() 
  
######## -----> REVISE CSV FILE TO CORRECT AVERAGE LAND HOLDING DATA 
     
  #################################################
  ########### NORMALIZED SCORES GGPLOT ############
  #################################################
  
  ###COUNTRY GROUPS
  national_aquifers <- c("Spain","South Africa", "China","Romania","Morocco","Chile")
  rows.to.keep<-which(rownames(country_scores_norm) %in% national_aquifers) 
  national_aquifers_scores_norm <- country_scores_norm[rows.to.keep,]
  national_aquifers_scores_norm$category_group = 1
  
  transboundary_aquifers <- c("Argentina","Mexico","Egypt","Algeria","Tunisia","Libya","Algeria","Colombia", "Uruguay", "Brazil","Ecuador","Peru", "Iraq", "Yemen", "Tunisia")
  rows.to.keep<-which(rownames(country_scores_norm) %in% transboundary_aquifers) 
  transboundary_aquifers_scores_norm <- country_scores_norm[rows.to.keep,]
  transboundary_aquifers_scores_norm$category_group = 2
  
  casestudy_aquifers <- c("United States","India","Australia","Pakistan")
  rows.to.keep<-which(rownames(country_scores_norm) %in% casestudy_aquifers) 
  casestudy_aquifers_scores_norm <- country_scores_norm[rows.to.keep,]
  casestudy_aquifers_scores_norm$category_group = 3
  
  all_aquifers <- c(national_aquifers, transboundary_aquifers, casestudy_aquifers)
  rows.to.keep<-which(!rownames(country_scores_norm) %in% all_aquifers)
  other_countries_scores_norm <- country_scores_norm[rows.to.keep,]
  other_countries_scores_norm$category_group = 4
  
  ###CREATE SINGLE DATAFRAME
  scores_norm <- rbind(national_aquifers_scores_norm,transboundary_aquifers_scores_norm,casestudy_aquifers_scores_norm, other_countries_scores_norm)
  scores_norm$category_group <- as.factor(scores_norm$category_group)
  
  ###REMOVE CLUTTER COUNTRIES
  remove_countries <- c('Armenia','Palestine','Georgia')
  rows.to.keep<-which(!rownames(scores_norm) %in% remove_countries)
  scores_norm <- scores_norm[rows.to.keep,]
  
  ###PATHS TRANSBOUNDARY AQUIFERS
  nwsahara_aquifer <- c("Libya","Tunisia","Algeria")
  rows.to.keep<-which(rownames(country_scores_norm) %in% nwsahara_aquifer) 
  nwsahara_scores_norm <- country_scores_norm[rows.to.keep,]
  nwsahara_scores_norm <- rbind(nwsahara_scores_norm, head(nwsahara_scores_norm, 1))
  
  arabian_aquifer <- c("Iraq","Yemen","Algeria")
  rows.to.keep<-which(rownames(country_scores_norm) %in% arabian_aquifer) 
  arabian_scores_norm <- country_scores_norm[rows.to.keep,]

  guarani_aquifer <- c("Brazil","Argentina","Uruguay")
  rows.to.keep<-which(rownames(country_scores_norm) %in% guarani_aquifer) 
  guarani_scores_norm <- country_scores_norm[rows.to.keep,]
  guarani_scores_norm <- rbind(guarani_scores_norm, head(guarani_scores_norm, 1))
  
  indus_aquifer <- c("India","Pakistan")
  rows.to.keep<-which(rownames(country_scores_norm) %in% indus_aquifer) 
  indus_scores_norm <- country_scores_norm[rows.to.keep,]

  amazon_aquifer <- c("Brazil","Colombia", "Ecuador","Peru")
  rows.to.keep<-which(rownames(country_scores_norm) %in% amazon_aquifer) 
  amazon_scores_norm <- country_scores_norm[rows.to.keep,]
  amazon_scores_norm <- rbind(amazon_scores_norm, head(amazon_scores_norm, 1))
  
  nubian_aquifer <- c("Libya", "Egypt")
  rows.to.keep<-which(rownames(country_scores_norm) %in% nubian_aquifer) 
  nubian_scores_norm <- country_scores_norm[rows.to.keep,]

  colorado_aquifer <- c("Mexico", "United States")
  rows.to.keep<-which(rownames(country_scores_norm) %in% colorado_aquifer) 
  colorado_scores_norm <- country_scores_norm[rows.to.keep,]

  ###GGPLOT
  legend_text=c("national aquifer","transboundary aquifers","GCG case studies","other countries")
  
  ggplot(data=scores_norm,aes(x=group_mean, y=grid_mean)) +
    annotate("rect",xmin=0.775,xmax=0.925,ymin=0.14,ymax=0.38,fill='red',alpha=0.1, color='red') +
    annotate("rect",xmin=0.45,xmax=0.61,ymin=0.31,ymax=0.55,fill='red',alpha=0.1, color='red') +
    annotate("rect",xmin=0.575,xmax=0.745,ymin=0.745,ymax=0.895,fill='red',alpha=0.1, color='red') +
    annotate("rect",xmin=0.26,xmax=0.40,ymin=0.735,ymax=0.865,fill='red',alpha=0.1, color='red') +
    geom_path(data=guarani_scores_norm, aes(x=group_mean,y=grid_mean),color='gold4', linetype = 2) +
    geom_path(data=indus_scores_norm, aes(x=group_mean,y=grid_mean),color='gold4', linetype = 2) +
    geom_path(data=amazon_scores_norm, aes(x=group_mean,y=grid_mean),color='gold4', linetype = 2) +
    geom_path(data=nubian_scores_norm, aes(x=group_mean,y=grid_mean),color='gold4', linetype = 2) +
    geom_path(data=colorado_scores_norm, aes(x=group_mean,y=grid_mean),color='gold4', linetype = 2) +
    geom_path(data=nwsahara_scores_norm, aes(x=group_mean,y=grid_mean),color='gold4', linetype = 2) +
    geom_path(data=arabian_scores_norm, aes(x=group_mean,y=grid_mean),color='gold4', linetype = 2) +
    geom_point(aes(shape=factor(category_group,labels = legend_text), color=factor(category_group,labels = legend_text), size=factor(category_group,labels = legend_text), group=category_group)) +
    scale_shape_manual(values = c(16,16,15,16), guide = guide_legend(title = NULL)) +
    scale_color_manual(values = c('darkblue','blue','red','grey'), guide = guide_legend(title = NULL)) +
    scale_size_manual(values = c(4,4,7,3), guide = guide_legend(title = NULL)) +
    geom_vline(xintercept = 0.52) + geom_hline(yintercept = 0.63) +
    labs(x = "GROUP", y = "GRID", color="", size="", shape="") +
    theme(axis.text = element_text(size = 14), axis.title=element_text(size=20,face="bold"),legend.position=c(.135, .4)) +
    coord_fixed() +
    geom_text_repel(data=scores_norm,aes(x=group_mean,y=grid_mean,label = rownames(scores_norm)), box.padding = unit(0.45, "lines"), size=4.5)
    
   


  
  

  
 
  
  