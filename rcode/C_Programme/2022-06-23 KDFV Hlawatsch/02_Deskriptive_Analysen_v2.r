# Timestamp einfügen
date()

#	-------------------------------------------------------------------------------------------------------------------
#	----
#	----	Block II: Bearbeitung der Daten
#	----
#	-------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------

#   Titel des Projekts: 		    	Labour market impacts of the European green transition: The regional dimension of green skills for employment
#   Datengrundlage: 		  	      Mikrozensus 2019

#   Dateiname des Programmcodes:  02_Deskriptive_Analysen.R
#   erstellt: 						        17.06.2022
#   von: 							            Felix Zaussinger 
#   E-Mail: 					          	felix.zaussinger@gess.ethz.ch
#   Tel.: 						          	0041767229309

#   Dateiname des Output-Files: 	<outputname.log> 


#   Grundriss des Programms: 
#        Programm verknüpft Mikrozensus mit Daten welche die Emissionsintensität 
#         von Berufsgruppen beschreiben, berechnet Statistiken zur Verteilung der Emissionsintensität
#         über Industrien und Regionen, berechnet desktiptive Statistiken sowie korreliert die Masse mit demographischen Charakteristika. 


#   Verwendete Variablen (Beispieldatensatz hier: Mikrozensus 2012): 
#   Originalvariablen: 	
#    "EF39", # filtering
#    "EF44", "EF46", # demographics
#    "EF114", "EF114UG1", "EF114UG2", "EF114UG3", "EF114UG4", # occupation
#    "EF137", "EF137UG1", # industry
#    "EF172", "EF175", # workplace characteristics
#    "EF188", "EF189", "EF195", "EF564", # place of work
#    "EF436", "EF442", # income
#    "EF517", "EF540", "EF564", # education
#    "EF951", "EF952", "EF953" # projection factors


#   Neu angelegte Variablen in dieser Syntax <syntaxname.r>:  
#         verh:     dichotome Variable Verheiratet ja/nein
#         persnr:  	Personennummer
#         famnr:  	Familiennummer 
#         hhnr:   	Haushaltsnummer
#         nrdiff:  	Differenz Haushaltsnummer - Familiennummer 
#         piddiff: 	Test einmalige Personennummer>

#   Anmerkung: Falls Variablen verwendet werden, die in einer vorherigen Syntax erstellt wurden, 
#   diese bitte in separaten Blöcken auflisten.   

#   Gewichtungsvariable: 	EF952


# -------------------------------------------------------------------------------------------------------------------
#	0. Packages laden
#	-------------------------------------------------------------------------------------------------------------------

# Packages installieren 

# GWAP-Nutzung: Bitte senden Sie uns die gesamten R-Pakete samt aller Dependencies in einem gezippten Ordner per E-Mail zu 

#setwd("")
#install.packages(pkgs=c("tidyverse", "readxl"), type = "source", repos = NULL)


# KDFV-Nutzung: 
.libPaths    <- file.path(basispfad,"R-Packages")
#install.packages(pkgs=c("tidyverse", "readxl"), dependencies=TRUE)

# Zu verwendende Packages laden

library(tidyverse)
library(readxl)
library(Hmisc)
library(vtable)
library(survey)
library(ggmosaic)

# -------------------------------------------------------------------------------------------------------------------
#	0. Definition von Funktionen
#	-------------------------------------------------------------------------------------------------------------------

#' Convert categorical variables to factors based on an input codebook.
#'
#' @description
#' The function allows for converting the categorical variables of a data frame
#' to factors based on a mapping between variable names, levels and level labels
vars_to_factors <- function(df_in, codebook, var_name="var_name", var_name_level="value", var_name_label="label_en"){
  # copy input df
  df <- df_in
  
  # iterative over variables in input df
  for (n in names(df)){
    # subset codebook by variable
    subset <- filter(codebook, var_name == n)
    
    # check if there is a level-label mapping for the variable in the codebook
    if (dim(subset)[1] != 0) {
      # assign factor
      df[[n]] <- factor(df[[n]], levels = subset[[var_name_level]], labels = subset[[var_name_label]])
    }
  }
  return(df)
}


#' Calculate boxplot stats while dropping outliers.
#'
#' @description
#' Calc boxplot stats excluding outliers while adjusting y-scale automatically.
#'
#' @Source: https://stackoverflow.com/questions/25124895/no-outliers-in-ggplot-boxplot-with-facet-wrap
calc_boxplot_stat <- function(x) {
  coef <- 1.5
  n <- sum(!is.na(x))
  # calculate quantiles
  stats <- quantile(x, probs = c(0.0, 0.25, 0.5, 0.75, 1.0))
  names(stats) <- c("ymin", "lower", "middle", "upper", "ymax")
  iqr <- diff(stats[c(2, 4)])
  # set whiskers
  outliers <- x < (stats[2] - coef * iqr) | x > (stats[4] + coef * iqr)
  if (any(outliers)) {
    stats[c(1, 5)] <- range(c(stats[2:4], x[!outliers]), na.rm = TRUE)
  }
  return(stats)
}

# -------------------------------------------------------------------------------------------------------------------
#	1. Datenaufbereitung
#	-------------------------------------------------------------------------------------------------------------------

#	a.  Datensatz einlesen und Variablen auswählen

# specify data types for select cols
colClasses=c(
  "EF951"="numeric",
  "EF952"="numeric",
  "EF953"="numeric"
)

# codes for non-responses (9 - 99999)
non_response_codes <- c(9, 99, 999, 9999, 99999)

# selection of core variables
vars = c(
  "FDZ2", # filtering of implausible cases
  "EF39", # working conditions
  "EF44", "EF46", # demographics
  "EF114", "EF114UG1", "EF114UG2", "EF114UG3", "EF114UG4", # occupations (KldB)
  "EF541", "EF541UG1", "EF541UG2", "EF541UG3", # occupations (ISCO)
  "EF137", "EF137UG1", # industry
  "EF172", "EF175", # workplace characteristics
  "EF188", "EF189", "EF195", "EF564", # place of work
  "EF436", "EF442", # income
  "EF517", "EF540", "EF564", # education
  "EF951", "EF952", "EF953" # projection factors
)

# filtering criteria
# age_min <- 15
# age_max <- 67
# -----------------------------------------------------------------------------

# specify csv format
sep <- ","
dec <- "."

if (FDZ == 0){
  sep = ";"
  dec = ","
}

# read data
dfr <- read.csv(file.path(datenpfad, paste(dateiname,  ".CSV",  sep="")), header = T, sep=sep, dec = dec, strip.white = TRUE, colClasses = colClasses)

# read codebook for converting categorical vectors to factors 
codebook <- read_excel(file.path(metadatenpfad, "codebook_microcensus_2019.xlsx"))

# extract reduced df based on core variables
dfs <- dfr %>%
  select(all_of(vars))

# replace all values < 0 with NA ("Not applicable" cases). Apparently not needed for GWAP file, but needed for Datenstrukturfile
if (FDZ == 0){
  dfs[dfs < 0] = NA
}

# manually code nan values due to non-responses (9 - 99999) for selected variables
dfs <- dfs %>%
  mutate(
    EF114 = replace(EF114, EF114 %in% c(99999), NA),
    EF114UG1 = replace(EF114UG1, EF114UG1 %in% c(9999), NA),
    EF114UG2 = replace(EF114UG2, EF114UG2 %in% c(999), NA),
    EF114UG3 = replace(EF114UG3, EF114UG3 %in% c(99), NA),
    EF137 = replace(EF137, EF137 %in% c(999), NA),
    EF172 = replace(EF172, EF172 %in% non_response_codes, NA),
    EF175 = replace(EF175, EF175 %in% non_response_codes, NA),
    EF188 = replace(EF188, EF188 %in% c(99), NA),
    EF189 = replace(EF189, EF189 %in% non_response_codes, NA),
    # EF196 = replace(EF196, EF196 %in% non_response_codes, NA), # not available in KDFV file
    EF436 = replace(EF436, EF436 %in% c(90, 99), NA),
    EF442 = replace(EF442, EF442 %in% c(99), NA),
    EF517 = replace(EF517, EF517 %in% c(999), NA),
    EF540 = replace(EF540, EF540 %in% c(99), NA),
    EF541 = replace(EF541, EF541 %in% c(9999), NA),
    EF541UG1 = replace(EF541UG1, EF541UG1 %in% c(999), NA),
    EF541UG2 = replace(EF541UG2, EF541UG2 %in% c(99), NA),
    EF541UG3 = replace(EF541UG3, EF541UG3 %in% c(9), NA),
  )

# convert income variable to numeric
income_cats <- data.frame(
  codes = c(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,50),
  values = c(150,225,400,600,800,1000,1200,1400,1600,1850,2150,2450,2750,3050,3400,3800,4250,4750,5250,5750,6750,8750,14000,18000, NA)
)
vec_income_cats <- income_cats %>% pull(values, codes)

dfs <- dfs %>%
  mutate(EF442_num = recode(EF442, !!!vec_income_cats)) %>%
  mutate(EF436_num = recode(EF436, !!!vec_income_cats)) %>%
  # bin age variable (for descriptive stats)
  mutate(EF44_bin10 = cut_width(EF44, width=10, boundary=0))

# convert integer dtypes to factors based on codebook (for descriptive stats)
dfs_factors <- vars_to_factors(dfs, codebook = codebook)

# -----------------------------------------------------------------------------
# filter for active, domestic labour force
dff2 <- dfs %>%
  # EF39 Erwerbsstatus nach Eurostat-Abgrenzung:
  #   1: Gegen Bezahlung gearbeitet
  #   2: Verfügte über eine Erwerbstätigkeit, arbeitete aber nicht
  filter(EF39 %in% c(1, 2)) %>% # working against payment
  # EF44: post-hoc correction of variable, resulting in 103 observations of 14-
  #   year-olds being counted as 15-year-olds
  filter(FDZ2 %nin% c(2, 3))

# convert integer dtypes to factors based on codebook
dff2 <- vars_to_factors(dff2, codebook = codebook)

# drop rows where data on occupation are missing
dff <- dff2 %>%
  drop_na(EF114) #%>%
  #drop_na(EF137) %>%
  #drop_na(EF564)

# add column to count number of observations (ungewichtete fallzahl) when grouping
dff$n_obs = 1


# -----------------------------------------------------------------------------
# ---> BLOCK COMMENT START
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
#	1.1 Deskriptive Statistiken (Vergleich zw. Rohdaten und reduzierten Sample)
#	-----------------------------------------------------------------------------

# variables for summary statistics
vars_summary <- c("EF952", "EF46", "EF44", "EF44_bin10", "EF517", "EF540", "EF436", "EF436_num", "EF442", "EF442_num", "EF114UG4", "EF114UG3", "EF137UG1")
summ <- c('notNA(x)', 'mean(x)',   'sd(x)', 'min(x)', 'pctile(x)[25]', 'pctile(x)[75]', 'max(x)', 'sum(x)')
summ.names <- c("N", "Mean", "Std. Dev.",	"Min",	"Pctl. 25",	"Pctl. 75",	"Max", "Sum")

# summary tables (+ export)
sumtable(dfs_factors, vars=vars_summary, summ=summ, summ.names=summ.names, digits = 3, out = "csv", file = file.path(outputpfad, "summary_statistics_raw.csv")) # unfiltered
sumtable(dff2, vars=vars_summary, summ=summ, summ.names=summ.names, digits = 3, out = "csv", file = file.path(outputpfad, "summary_statistics_active_employment.csv")) # filtered for active employment status
sumtable(dff, vars=vars_summary, summ=summ, summ.names=summ.names, digits = 3, out = "csv", file = file.path(outputpfad, "summary_statistics_active_employment_nans_dropped.csv")) # observations with missing occ code dropped

# Ausgabe der Restpopulation [OUTPUT AUSSCHLIESSLICH FÜR PRÜFZWECKE]
# -----------------------------------------------------------------------------

# reversed filters
dff2_rest <- dfs %>%
  filter(EF39 %nin% c(1, 2) | FDZ2 %in% c(2, 3))

dff_rest <- dff2_rest %>%
  drop_na(EF114)

sumtable(dff2_rest, vars=vars_summary, summ=summ, summ.names=summ.names, digits = 3, out = "csv", file = file.path(outputpfad, "summary_statistics_active_employment_rest.csv")) # filtered for active employment status
sumtable(dff_rest, vars=vars_summary, summ=summ, summ.names=summ.names, digits = 3, out = "csv", file = file.path(outputpfad, "summary_statistics_active_employment_nans_dropped_rest.csv")) # observations with missing occ code dropped

# -----------------------------------------------------------------------------
# 1.2 Attachment of external data
# -----------------------------------------------------------------------------

# specify version of green/brown list (!!!)
# versions:
occ_list_versions <- c(
  "short_list", "short_list_tobi"
  )

# START OF LOOP
for (occ_list_version in occ_list_versions) {
  print(occ_list_version)

  # occupational greenness and brownness shares at KldB 5-digit level
  occupation_metadata <-
    # read
    read_excel(
    path = file.path(metadatenpfad, "occ_metadata_en_kldb2010_final_merged_gbn_clsf_updated_imputed.xlsx"),
    sheet = occ_list_version) %>%
    # rename
    rename(
      EF114 = kldb2010_code,
      EF114_name_en = kldb2010_name_en,
      EF114_name_de = kldb2010_name_de
    ) %>%
    # convert to factors
    vars_to_factors(., codebook)

  # join occupation metadata based on 5-digit kldb codes
  dfm <- left_join(
    x=dff,
    y=occupation_metadata,
    by="EF114"
  )

  # sort columns alphabetically
  dfm <- dfm[, order(colnames(dfm))]

  #	-------------------------------------------------------------------------------------------------------------------
  # 2. Datenauswertung
  # -------------------------------------------------------------------------------------------------------------------

  # create output folder for list version
  dir.create(file.path(outputpfad, occ_list_version))

  # -----------------------------------------------------------------------------
  # 2.1) Inspection of variables
  # -----------------------------------------------------------------------------

  # unique categories across occupations, industries and regions
  print(paste("Unique occupations (5 digit): ", length(unique(dfm$EF114))))
  print(paste("Unique industries (3 digit): ", length(unique(dfm$EF137))))
  print(paste("Unique industries (2 digit): ", length(unique(dfm$EF137UG1))))
  print(paste("Unique regions (reg. anp.): ", length(unique(dfm$EF564))))
  print(paste("Unique regions (nuts II): ", length(unique(dfm$EF189))))

  # -----------------------------------------------------------------------------
  # 2.2) Aggregation of occupational Greenness shares by occupation
  # -----------------------------------------------------------------------------
  
  # This is solely to understand how workers are distributed across the top
  # occupations. No further analysis is envisioned.
  
  # EF952 by occupation (5-digit)
  # -------------------------------------------------------------
  # absolute values
  EF952_by_EF114 <- dfm %>%
    group_by(EF114, EF114_name_en) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      EF952_share_green_abs = sum(EF952 * share_green),
      EF952_share_brown_abs = sum(EF952 * share_brown),
      EF952_share_neutral_abs = sum(EF952 * share_neutral),
      EF952_share_green_rel = sum(EF952 * share_green) / sum(EF952),
      EF952_share_brown_rel = sum(EF952 * share_brown) / sum(EF952),
      EF952_share_neutral_rel = sum(EF952 * share_neutral) / sum(EF952),
    )
  
  write_csv(EF952_by_EF114, file=file.path(outputpfad, occ_list_version, "EF952_by_EF114.csv"))
  
  # -----------------------------------------------------------------------------
  # 2.3) Grouping of occupational shares by region
  # -----------------------------------------------------------------------------
  
  # EF952 by EF189 (Region der Arbeitsstätte, NUTS II)
  # -----------------------------------------------------------------------------
  
  # relative values
  EF952_by_EF189 <- dfm %>%
    group_by(EF189) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      EF952_share_green_abs = sum(EF952 * share_green),
      EF952_share_brown_abs = sum(EF952 * share_brown),
      EF952_share_neutral_abs = sum(EF952 * share_neutral),
      EF952_share_green_rel = sum(EF952 * share_green) / sum(EF952),
      EF952_share_brown_rel = sum(EF952 * share_brown) / sum(EF952),
      EF952_share_neutral_rel = sum(EF952 * share_neutral) / sum(EF952),
    )
  
  write_csv(EF952_by_EF189, file=file.path(outputpfad, occ_list_version, "EF952_by_EF189.csv"))
  
  
  # EF952 by EF564 (Regionale Anpassungsschicht, zwischen NUTS II und III)
  # -----------------------------------------------------------------------------
  
  # relative values
  EF952_by_EF564 <- dfm %>%
    group_by(EF564) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      EF952_share_green_abs = sum(EF952 * share_green),
      EF952_share_brown_abs = sum(EF952 * share_brown),
      EF952_share_neutral_abs = sum(EF952 * share_neutral),
      EF952_share_green_rel = sum(EF952 * share_green) / sum(EF952),
      EF952_share_brown_rel = sum(EF952 * share_brown) / sum(EF952),
      EF952_share_neutral_rel = sum(EF952 * share_neutral) / sum(EF952),
    )
  
  write_csv(EF952_by_EF564, file=file.path(outputpfad, occ_list_version, "EF952_by_EF564.csv"))
  
  # -----------------------------------------------------------------------------
  # 2.4) Grouping of occupational shares by industry
  # -----------------------------------------------------------------------------
  
  # EF952 by EF137 (3-digit)
  # -----------------------------------------------------------------------------
  
  # relative values
  EF952_by_EF137 <- dfm %>%
    group_by(EF137) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      EF952_share_green_abs = sum(EF952 * share_green),
      EF952_share_brown_abs = sum(EF952 * share_brown),
      EF952_share_neutral_abs = sum(EF952 * share_neutral),
      EF952_share_green_rel = sum(EF952 * share_green) / sum(EF952),
      EF952_share_brown_rel = sum(EF952 * share_brown) / sum(EF952),
      EF952_share_neutral_rel = sum(EF952 * share_neutral) / sum(EF952),
    )
  
  write_csv(EF952_by_EF137, file=file.path(outputpfad, occ_list_version, "EF952_by_EF137.csv"))
  
  # EF952 by EF137UG1 (2-digit)
  # -----------------------------------------------------------------------------
  
  # relative values
  EF952_by_EF137UG1 <- dfm %>%
    group_by(EF137UG1) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      EF952_share_green_abs = sum(EF952 * share_green),
      EF952_share_brown_abs = sum(EF952 * share_brown),
      EF952_share_neutral_abs = sum(EF952 * share_neutral),
      EF952_share_green_rel = sum(EF952 * share_green) / sum(EF952),
      EF952_share_brown_rel = sum(EF952 * share_brown) / sum(EF952),
      EF952_share_neutral_rel = sum(EF952 * share_neutral) / sum(EF952),
    )
  
  write_csv(EF952_by_EF137UG1, file=file.path(outputpfad, occ_list_version, "EF952_by_EF137UG1.csv"))
  
  # -----------------------------------------------------------------------------
  # 3) Correlation and distributions of occupational shares with/across demographic characteristics
  # -----------------------------------------------------------------------------
  
  # convert integer dtypes to factors based on codebook
  # dfm_factors <- vars_to_factors(dfm, codebook = codebook)
  
  # -----------------------------------------------------------------------------
  
  # pivot to long format
  dfm_long <- pivot_longer(dfm, starts_with("share"), names_to = "share_type", values_to = "share_value")
  
  # with age
  cor.test(x = dfm$EF44, y = dfm$share_green)
  
  # bin age variable
  dfm_long$EF44_bin5 <- cut_width(dfm_long$EF44, width=5, boundary=0)
  
  ggplot(dfm_long, aes(x = as.factor(EF44_bin5), y = share_value)) +
    stat_summary(fun.data = calc_boxplot_stat, geom="boxplot") +
    facet_wrap(~share_type, scales = "free_y") +
    theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1))
  
  ggsave(
    "shares_by_EF44.pdf",
    path=file.path(outputpfad, occ_list_version),
    height=5,
    width = 20
  )
  
  # output für prüfung: number of obs per bin
  dfm_long %>%
    group_by(share_type, EF44_bin5) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      mean=mean(share_value, na.rm = TRUE),
      mean_weighted=wtd.mean(share_value, EF952, na.rm=TRUE, normwt=TRUE),
      sd=sd(share_value, na.rm = TRUE),
      sd_weighted=sqrt(wtd.var(share_value, EF952, na.rm=TRUE, normwt=TRUE)),
      median=median(share_value, na.rm = TRUE),
      q25=quantile(share_value, na.rm = TRUE, probs=c(.25)),
      q75=quantile(share_value, na.rm = TRUE, probs=c(.75)),
      median_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.5), normwt=TRUE),
      q25_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.25), normwt=TRUE),
      q75_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.75), normwt=TRUE),
    ) %>%
    write.csv(file.path(outputpfad, occ_list_version, "shares_by_EF44.csv"))
  
  # with sex
  cor.test(x = as.integer(dfm$EF46), y = dfm$share_green)
  
  ggplot(dfm_long, aes(x = EF46, y = share_value)) +
    stat_summary(fun.data = calc_boxplot_stat, geom="boxplot") +
    facet_wrap(~share_type, scales = "free_y") +
    theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1))
  
  ggsave(
    "shares_by_EF46.pdf",
    path=file.path(outputpfad, occ_list_version),
    height=5,
    width = 20
  )
  
  # output für prüfung: number of obs per bin
  dfm_long %>%
    group_by(share_type, EF46) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      mean=mean(share_value, na.rm = TRUE),
      mean_weighted=wtd.mean(share_value, EF952, na.rm=TRUE, normwt=TRUE),
      sd=sd(share_value, na.rm = TRUE),
      sd_weighted=sqrt(wtd.var(share_value, EF952, na.rm=TRUE, normwt=TRUE)),
      median=median(share_value, na.rm = TRUE),
      q25=quantile(share_value, na.rm = TRUE, probs=c(.25)),
      q75=quantile(share_value, na.rm = TRUE, probs=c(.75)),
      median_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.5), normwt=TRUE),
      q25_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.25), normwt=TRUE),
      q75_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.75), normwt=TRUE),
    ) %>%
    write.csv(file.path(outputpfad, occ_list_version, "shares_by_EF46.csv"))
  
  # with income
  cor.test(x = as.integer(dfm$EF436), y = dfm$share_green)
  cor.test(x = as.integer(dfm$EF442), y = dfm$share_green)
  
  ggplot(dfm_long, aes(x = EF436, y = share_value)) +
    stat_summary(fun.data = calc_boxplot_stat, geom="boxplot") +
    facet_wrap(~share_type, scales = "free_y") +
    theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1))
  
  ggsave(
    "shares_by_EF436.pdf",
    path=file.path(outputpfad, occ_list_version),
    height=5,
    width = 20
  )
  
  # note: error is thrown by HMISC wtd functions if only NAN values in a group slice
  try({
    dfm_long %>%
      group_by(share_type, EF436) %>%
      summarise(
        n_obs=sum(n_obs),
        EF952_sum=sum(EF952),
        mean=mean(share_value, na.rm = TRUE),
        mean_weighted=wtd.mean(share_value, EF952, na.rm=TRUE, normwt=TRUE),
        sd=sd(share_value, na.rm = TRUE),
        sd_weighted=sqrt(wtd.var(share_value, EF952, na.rm=TRUE, normwt=TRUE)),
        median=median(share_value, na.rm = TRUE),
        q25=quantile(share_value, na.rm = TRUE, probs=c(.25)),
        q75=quantile(share_value, na.rm = TRUE, probs=c(.75)),
        median_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.5), normwt=TRUE),
        q25_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.25), normwt=TRUE),
        q75_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.75), normwt=TRUE),
      ) %>%
      write.csv(file.path(outputpfad, occ_list_version, "shares_by_EF436.csv"))
  })
  
  ggplot(dfm_long, aes(x = EF442, y = share_value)) +
    stat_summary(fun.data = calc_boxplot_stat, geom="boxplot") +
    facet_wrap(~share_type, scales = "free_y") +
    theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1))
  
  
  ggsave(
    "shares_by_EF442.pdf",
    path=file.path(outputpfad, occ_list_version),
    height=5,
    width = 20
  )
  
  # note: error is thrown by HMISC wtd functions if only NAN values in a group slice
  try({
    dfm_long %>%
      group_by(share_type, EF442) %>%
      summarise(
        n_obs=sum(n_obs),
        EF952_sum=sum(EF952),
        mean=mean(share_value, na.rm = TRUE),
        mean_weighted=wtd.mean(share_value, EF952, na.rm=TRUE, normwt=TRUE),
        sd=sd(share_value, na.rm = TRUE),
        sd_weighted=sqrt(wtd.var(share_value, EF952, na.rm=TRUE, normwt=TRUE)),
        median=median(share_value, na.rm = TRUE),
        q25=quantile(share_value, na.rm = TRUE, probs=c(.25)),
        q75=quantile(share_value, na.rm = TRUE, probs=c(.75)),
        median_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.5), normwt=TRUE),
        q25_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.25), normwt=TRUE),
        q75_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.75), normwt=TRUE),
      ) %>%
      write.csv(file.path(outputpfad, occ_list_version, "shares_by_EF442.csv"))
  })
  
  # with education level
  cor.test(x = as.integer(dfm$EF517), y = dfm$share_green)
  cor.test(x = as.integer(dfm$EF540), y = dfm$share_green)
  
  ggplot(dfm_long, aes(x = EF517, y = share_value)) +
    stat_summary(fun.data = calc_boxplot_stat, geom="boxplot") +
    facet_wrap(~share_type, scales = "free_y") +
    theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1))
  
  ggsave(
    "shares_by_EF517.pdf",
    path=file.path(outputpfad, occ_list_version),
    height=5,
    width = 20
  )
  
  # note: error is thrown by HMISC wtd functions if only NAN values in a group slice
  try({
    dfm_long %>%
      group_by(share_type, EF517) %>%
      summarise(
        n_obs=sum(n_obs),
        EF952_sum=sum(EF952),
        mean=mean(share_value, na.rm = TRUE),
        mean_weighted=wtd.mean(share_value, EF952, na.rm=TRUE, normwt=TRUE),
        sd=sd(share_value, na.rm = TRUE),
        sd_weighted=sqrt(wtd.var(share_value, EF952, na.rm=TRUE, normwt=TRUE)),
        median=median(share_value, na.rm = TRUE),
        q25=quantile(share_value, na.rm = TRUE, probs=c(.25)),
        q75=quantile(share_value, na.rm = TRUE, probs=c(.75)),
        median_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.5), normwt=TRUE),
        q25_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.25), normwt=TRUE),
        q75_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.75), normwt=TRUE),
      ) %>%
      write.csv(file.path(outputpfad, occ_list_version, "shares_by_EF517.csv"))
  })
  
  ggplot(dfm_long, aes(x = EF540, y = share_value)) +
    stat_summary(fun.data = calc_boxplot_stat, geom="boxplot") +
    facet_wrap(~share_type, scales = "free_y") +
    theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1))
  
  ggsave(
    "shares_by_EF540.pdf",
    path=file.path(outputpfad, occ_list_version),
    height=5,
    width = 20
  )
  
  # note: error is thrown by HMISC wtd functions if only NAN values in a group slice
  try({
    dfm_long %>%
      group_by(share_type, EF540) %>%
      summarise(
        n_obs=sum(n_obs),
        EF952_sum=sum(EF952),
        mean=mean(share_value, na.rm = TRUE),
        mean_weighted=wtd.mean(share_value, EF952, na.rm=TRUE, normwt=TRUE),
        sd=sd(share_value, na.rm = TRUE),
        sd_weighted=sqrt(wtd.var(share_value, EF952, na.rm=TRUE, normwt=TRUE)),
        median=median(share_value, na.rm = TRUE),
        q25=quantile(share_value, na.rm = TRUE, probs=c(.25)),
        q75=quantile(share_value, na.rm = TRUE, probs=c(.75)),
        median_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.5), normwt=TRUE),
        q25_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.25), normwt=TRUE),
        q75_weighted=wtd.quantile(share_value, EF952, na.rm=TRUE, probs=c(.75), normwt=TRUE),
      ) %>%
      write.csv(file.path(outputpfad, occ_list_version, "shares_by_EF540.csv"))
  })
  
  # -----------------------------------------------------------------------------
  # 4) Analysis of sociodemographics by category
  # -----------------------------------------------------------------------------
  
  # params
  vars_summary_class <- c("EF952", "EF46", "EF44", "EF44_bin10", "EF517", "EF540", "EF436", "EF436_num", "EF442", "EF442_num", "EF114UG4", "EF137UG1")
  fill_colors <- c("green" = "darkgreen", "brown" = "brown", "neutral" = "darkgrey")
  category_versions <- c("category_abs", "category_rel")
  
  for (category_version in category_versions){
    # summary tables incl. tests for significant differences btw groups
    # -------------------------------------------------------------------------
    
    sumtable(
      dfm, vars = vars_summary_class, group = category_version, group.test = TRUE, group.weights = "EF952",
      out = "csv", file = file.path(outputpfad, occ_list_version, paste0("weighted_summary_statistics_by_", category_version, ".csv")), digits = 3
    )
    
    sumtable(
      dfm, vars = vars_summary_class, group = category_version, group.test = TRUE,
      out = "csv", file = file.path(outputpfad, occ_list_version, paste0("summary_statistics_by_", category_version, ".csv")), digits = 3
    )
    
    # pairwise tests for diff between groups
    # -------------------------------------------------------------------------
    
    # age
    kruskal.test(dfm$EF44, dfm[[category_version]])
    oneway.test(EF44 ~ dfm[[category_version]], data = dfm)
    pairwise.t.test(dfm$EF44, dfm[[category_version]], p.adjust.method = "bonferroni")
    pairwise.wilcox.test(dfm$EF44, dfm[[category_version]], p.adjust.method = "holm")
    
    # gender
    chisq.test(dfm$EF46, dfm[[category_version]])
    
    # income
    kruskal.test(dfm$EF436_num, dfm[[category_version]])
    oneway.test(EF436_num ~ dfm[[category_version]], data = dfm)
    pairwise.t.test(dfm$EF436_num, dfm[[category_version]], p.adjust.method = "bonferroni")
    pairwise.wilcox.test(dfm$EF436_num, dfm[[category_version]], p.adjust.method = "holm")
    
    # education
    chisq.test(dfm$EF517, dfm[[category_version]])
    chisq.test(dfm$EF540, dfm[[category_version]])
    
    
    # barplots for GBN groups (hinweis: numerische werte sind jeweils in den summentabellen abgespeichert)
    # -------------------------------------------------------------------------
    
    # age
    ggplot(dfm, aes(x = .data[[category_version]], y=EF44)) +
      stat_summary(fun.data = calc_boxplot_stat, geom="boxplot") +
      stat_summary(fun = mean, geom = "point") +
      theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1)) +
      labs(x="Group", y="Age [yrs] (EF44)")
    
    ggsave(
      paste0(category_version, "_by_EF44.pdf"),
      path=file.path(outputpfad, occ_list_version)
    )
    
    # gender
    ggplot(dfm, aes(x = EF46, y=EF952, fill = .data[[category_version]])) +
      geom_col(position = "dodge") +
      theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1)) +
      labs(x="Gender", y="Population [-] (EF952)") +
      scale_fill_manual(values = fill_colors)
    
    ggsave(
      paste0(category_version, "_by_EF46.pdf"),
      path=file.path(outputpfad, occ_list_version)
    )
    
    # education, 1
    ggplot(dfm, aes(x = EF517, y=EF952, fill = .data[[category_version]])) +
      geom_col(position = "dodge") +
      theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1)) +
      labs(x="Education (EF517)", y="Population [-] (EF952)") +
      scale_fill_manual(values = fill_colors)
    
    ggsave(
      paste0(category_version, "_by_EF517.pdf"),
      path=file.path(outputpfad, occ_list_version),
      width = 10
    )
    
    ggplot(dfm) +
      geom_mosaic(aes(x=product(EF517, category_abs), fill=EF517, weight=EF952))
    
    ggsave(
      paste0(category_version, "_by_EF517_mosaic.pdf"),
      path=file.path(outputpfad, occ_list_version)
    )
    
    # education, 2
    ggplot(dfm, aes(x = EF540, y=EF952, fill = .data[[category_version]])) +
      geom_col(position = "dodge") +
      theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1)) +
      labs(x="Education (EF540)", y="Population [-] (EF952)") +
      scale_fill_manual(values = fill_colors)
    
    ggsave(
      paste0(category_version, "_by_EF540.pdf"),
      path=file.path(outputpfad, occ_list_version),
      width = 10
    )
    
    ggplot(dfm) +
      geom_mosaic(aes(x=product(EF540, category_abs), fill=EF540, weight=EF952))
    
    ggsave(
      paste0(category_version, "_by_EF540_mosaic.pdf"),
      path=file.path(outputpfad, occ_list_version)
    )
    
    # income, personal
    ggplot(dfm, aes(x = EF436, y=EF952, fill = .data[[category_version]])) +
      geom_col(position = "dodge") +
      theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1)) +
      labs(x="Income, personal [Euro/month] (EF436)", y="Population [-] (EF952)") +
      scale_fill_manual(values = fill_colors)
    
    ggsave(
      paste0(category_version, "_by_EF436.pdf"),
      path=file.path(outputpfad, occ_list_version),
      width = 10
    )
    
    ggplot(dfm, aes(x = .data[[category_version]], y=EF436_num)) +
      stat_summary(fun.data = calc_boxplot_stat, geom="boxplot") +
      stat_summary(fun = mean, geom = "point") +
      theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1)) +
      labs(x="Group", y="Income, personal [Euro/month] (EF436)")
    
    ggsave(
      paste0(category_version, "_by_EF436_num.pdf"),
      path=file.path(outputpfad, occ_list_version)
    )
    
    # income, average
    ggplot(dfm, aes(x = EF442, y=EF952, fill = .data[[category_version]])) +
      geom_col(position = "dodge") +
      theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1)) +
      labs(x="Income, average [Euro/month] (EF442)", y="Population [-] (EF952)") +
      scale_fill_manual(values = fill_colors)
    
    ggsave(
      paste0(category_version, "_by_EF442.pdf"),
      path=file.path(outputpfad, occ_list_version),
      width = 10
    )
      
    ggplot(dfm, aes(x = .data[[category_version]], y=EF442_num)) +
      stat_summary(fun.data = calc_boxplot_stat, geom="boxplot") +
      stat_summary(fun = mean, geom = "point") +
      theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1)) +
      labs(x="Group", y="Income, personal [Euro/month] (EF442)")
    
    ggsave(
      paste0(category_version, "_by_EF442_num.pdf"),
      path=file.path(outputpfad, occ_list_version)
    )
  }
  
}

# -----------------------------------------------------------------------------
# 2.4) Occupational shares at ISCO level weighted by KldB 5-digit occupation counts
# -----------------------------------------------------------------------------

# obtain weighted occ shares within ISCO groups
df_occ_dist_4d <- dfm %>% 
  group_by(EF541) %>% 
  summarise(
    n_obs=sum(n_obs), 
    EF952=sum(EF952),
    share_green_wtd=wtd.mean(share_green, weights = EF952, normwt = TRUE),
    share_brown_wtd=wtd.mean(share_brown, weights = EF952, normwt = TRUE),
    share_neutral_wtd=wtd.mean(share_neutral, weights = EF952, normwt = TRUE)
    )

df_occ_dist_3d <- dfm %>% 
  group_by(EF541UG1) %>% 
  summarise(
    n_obs=sum(n_obs), 
    EF952=sum(EF952),
    share_green_wtd=wtd.mean(share_green, weights = EF952, normwt = TRUE),
    share_brown_wtd=wtd.mean(share_brown, weights = EF952, normwt = TRUE),
    share_neutral_wtd=wtd.mean(share_neutral, weights = EF952, normwt = TRUE)
  )

df_occ_dist_2d <- dfm %>% 
  group_by(EF541UG2) %>% 
  summarise(
    n_obs=sum(n_obs),
    EF952=sum(EF952),
    share_green_wtd=wtd.mean(share_green, weights = EF952, normwt = TRUE),
    share_brown_wtd=wtd.mean(share_brown, weights = EF952, normwt = TRUE),
    share_neutral_wtd=wtd.mean(share_neutral, weights = EF952, normwt = TRUE)
  )

df_occ_dist_1d <- dfm %>% 
  group_by(EF541UG3) %>% 
  summarise(
    n_obs=sum(n_obs),
    EF952=sum(EF952),
    share_green_wtd=wtd.mean(share_green, weights = EF952, normwt = TRUE),
    share_brown_wtd=wtd.mean(share_brown, weights = EF952, normwt = TRUE),
    share_neutral_wtd=wtd.mean(share_neutral, weights = EF952, normwt = TRUE)
  )

# save
write_csv(df_occ_dist_4d, file=file.path(outputpfad, "weighted_occ_shares_ISCO4D.csv"))
write_csv(df_occ_dist_3d, file=file.path(outputpfad, "weighted_occ_shares_ISCO3D.csv"))
write_csv(df_occ_dist_2d, file=file.path(outputpfad, "weighted_occ_shares_ISCO2D.csv"))
write_csv(df_occ_dist_1d, file=file.path(outputpfad, "weighted_occ_shares_ISCO1D.csv"))

# -----------------------------------------------------------------------------
# 2.5) Fallzahltabellen der Restpopulation
# -----------------------------------------------------------------------------

# Ausgabe der Restpopulation [OUTPUT AUSSCHLIESSLICH FÜR PRÜFZWECKE]
# -----------------------------------------------------------------------------

dff_rest <- dfs %>%
  # reversed filters
  filter(EF39 %nin% c(1, 2) | FDZ2 %in% c(2, 3)) %>%
  # drop rows where data on occupation, industry or region are missing
  drop_na(EF114)

# grouping by occupation, region and industry
# -----------------------------------------------------------------------------

# by occupation
EF952_by_EF114_rest <- dff_rest %>%
  group_by(EF114) %>%
  summarise(
    n_obs=n(),
    EF952_sum=sum(EF952)
  ) %>%
  write_csv(file=file.path(outputpfad, "EF952_by_EF114_rest.csv"))

# by region
EF952_by_EF189_rest <- dff_rest %>%
  group_by(EF189) %>%
  summarise(
    n_obs=n(),
    EF952_sum=sum(EF952)
  ) %>%
  write_csv(file=file.path(outputpfad, "EF952_by_EF189_rest.csv"))

EF952_by_EF564_rest <- dff_rest %>%
  group_by(EF564) %>%
  summarise(
    n_obs=n(),
    EF952_sum=sum(EF564)
  ) %>%
  write_csv(file=file.path(outputpfad, "EF952_by_EF564_rest.csv"))

# by industry
EF952_by_EF137_rest <- dff_rest %>%
  group_by(EF137) %>%
  summarise(
    n_obs=n(),
    EF952_sum=sum(EF952)
  ) %>%
  write_csv(file=file.path(outputpfad, "EF952_by_EF137_rest.csv"))

EF952_by_EF137UG1_rest <- dff_rest %>%
  group_by(EF137UG1) %>%
  summarise(
    n_obs=n(),
    EF952_sum=sum(EF952)
  ) %>%
  write_csv(file=file.path(outputpfad, "EF952_by_EF137UG1_rest.csv"))


# grouping by sociodemographic variables
# -----------------------------------------------------------------------------

# by age
dff_rest$EF44_binned <- cut_width(dff_rest$EF44, width=5, boundary=0)
dff_rest %>%
  group_by(EF44_binned) %>%
  summarise(
    n_obs=n(),
    EF952_sum=sum(EF952)
  ) %>%
  write.csv(file.path(outputpfad, "shares_by_EF44_rest.csv"))

# by sex
dff_rest %>%
  group_by(EF46) %>%
  summarise(
    n_obs=n(),
    EF952_sum=sum(EF952)
  ) %>%
  write.csv(file.path(outputpfad, "shares_by_EF46_rest.csv"))

# by income
dff_rest %>%
  group_by(EF436) %>%
  summarise(
    n_obs=n(),
    EF952_sum=sum(EF952)
  ) %>%
  write.csv(file.path(outputpfad, "shares_by_EF436_rest.csv"))

dff_rest %>%
  group_by(EF442) %>%
  summarise(
    n_obs=n(),
    EF952_sum=sum(EF952)
  ) %>%
  write.csv(file.path(outputpfad, "shares_by_EF442_rest.csv"))

# by education
dff_rest %>%
  group_by(EF517) %>%
  summarise(
    n_obs=n(),
    EF952_sum=sum(EF952)
  ) %>%
  write.csv(file.path(outputpfad, "shares_by_EF517_rest.csv"))

dff_rest %>%
  group_by(EF540) %>%
  summarise(
    n_obs=n(),
    EF952_sum=sum(EF952)
  ) %>%
  write.csv(file.path(outputpfad, "shares_by_EF540_rest.csv"))

#	-------------------------------------------------------------------------------------------------------------------
#	H I N W E I S:

# Die vorliegende Mustersyntax stellt ein Beispiel für eine Erstsyntax dar. Wenn in den folgenden Syntaxen
# Auswertungen gemacht werden, die einen inhaltlichen Bezug zu bereits erstellten Ergebnissen haben, sind die
# Bezüge zu den entsprechenden vorherigen Syntaxen sowohl bei der Datenaufbereitung als auch bei der Auswertung in
# einem Kommentar kenntlich zu machen.
# #	-------------------------------------------------------------------------------------------------------------------