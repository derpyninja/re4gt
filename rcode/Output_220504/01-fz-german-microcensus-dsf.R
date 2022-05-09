# -----------------------------------------------------------------------------
# SYNTAXKOPF
# -----------------------------------------------------------------------------
# Projekt: Titel, Nummer -> TODO
# Kontaktdaten: Felix Zaussinger
# Syntaxbeschreibung: TODO
# FDZ-Produkte: TODO
# Variablenliste: TODO
#   
# Makros: TODO
# -----------------------------------------------------------------------------
# PREPARATION
# -----------------------------------------------------------------------------
# remove all objects from R workspace
rm(list=ls())
# -----------------------------------------------------------------------------
# Load necessary packages
library(tidyverse)
library(readxl)

# set plotting theme
theme_set(theme_classic())
# -----------------------------------------------------------------------------
# set directories & file paths
# -----------------------------------------------------------------------------

# root directory
root_dir = file.path("Z:", "SMS", "GWA92_4561_FZ")

# path to microcensus data 
fpath_data_csv = file.path(root_dir, "A_Mikrodaten", "MZ 2019 (mit Labels BY_Pseudo).csv")

# dir with metadata
metadata_dir = file.path(root_dir, "B_Metadaten")

# dir with results
analysis_date = "2022-05-02"
results_dir = file.path(root_dir, "D_Ergebnisse", analysis_date)

# set working directory
setwd(root_dir)
# -----------------------------------------------------------------------------
# specify data types for select cols
colClasses=c(
  "EF951"="numeric",
  "EF952"="numeric",
  "EF953"="numeric"
)

# read DSF, csv version
dsf <- read.csv(
  file=fpath_data_csv,
  header=TRUE,
  sep=",",
  # dec=".",
  strip.white=TRUE,
  colClasses = colClasses
)

# replace all values < 0 with NA ("Not applicable" cases). apparently not 
# needed for GWAP file, but needed for KDFV file.
# dsf[dsf < 0] = NA

# -----------------------------------------------------------------------------
# Preprocessing of final data set
# -----------------------------------------------------------------------------
# 1) Variable selection
# 2) Coding of non-responses
# 3) Filtering for active, domestic labour force
# 4) Conversion of dtypes
# -----------------------------------------------------------------------------

# selection of core variables
# NOTE: uncomment commented lines when working with real data at GWAP
vars = c(
  # filtering
  "EF39",
  # demographics
  "EF44", 
  "EF46",
  # occupation
  "EF114", 
  "EF114UG1", 
  "EF114UG2", 
  "EF114UG3", 
  "EF114UG4",
  # industry
  "EF137",
  "EF137UG1", 
  # workplace characteristics
  "EF172",
  #"EF174",   # not available in KDFV & GWAP file
  "EF175",
  # place of work
  "EF188",
  "EF189", 
  "EF195",
  "EF196",   # not available in KDFV file
  #"560UG2",  # not available in KDFV & GWAP file
  #"560UG3",  # not available in KDFV & GWAP file
  "EF564",
  "EF568",  # not available in KDFV file
  # income
  "EF436",
  "EF442",
  # education
  "EF517",
  "EF540",
  "EF564",
  # projection factors
  "EF951",
  "EF952",
  "EF953"
)

# extract reduced df based on core variables
dsf_reduced <- dsf %>%
  select(all_of(vars))

# codes for non-responses (9 - 99999)
non_response_codes <- c(9, 99, 999, 9999, 99999)

# Code nan values due to non-responses (9 - 99999) for selected variables
dsf_nans_coded <- dsf_reduced %>%
  mutate(
    EF114 = replace(EF114, EF114 %in% non_response_codes, NA),
    EF114UG1 = replace(EF114UG1, EF114UG1 %in% non_response_codes, NA),
    EF114UG1 = replace(EF114UG1, EF114UG1 %in% non_response_codes, NA),
    EF114UG2 = replace(EF114UG2, EF114UG2 %in% non_response_codes, NA),
    EF114UG3 = replace(EF114UG3, EF114UG3 %in% non_response_codes, NA),
    EF137 = replace(EF137, EF137 %in% non_response_codes, NA),
    EF172 = replace(EF172, EF172 %in% non_response_codes, NA),
    # EF174 = replace(EF174, EF174 %in% non_response_codes, NA), # not available in KDFV & GWAP file --> dropped
    EF175 = replace(EF175, EF175 %in% non_response_codes, NA),
    EF188 = replace(EF188, EF188 %in% c(99), NA),
    EF189 = replace(EF189, EF189 %in% non_response_codes, NA),
    EF196 = replace(EF196, EF196 %in% non_response_codes, NA), # not available in KDFV file
    EF436 = replace(EF436, EF436 %in% c(90, 99), NA),
    EF442 = replace(EF442, EF442 %in% c(99), NA),
    EF517 = replace(EF517, EF517 %in% c(999), NA),
    EF540 = replace(EF540, EF442 %in% c(99), NA),
  )

# filtering criteria
age_min <- 15
age_max <- 67

# filter for active, domestic labour force
dsf_filtered <- dsf_nans_coded %>%
  filter(EF39 == 1) %>% # working against payment
  filter(EF44 >= age_min & EF44 <= age_max) %>% # age restriction
  filter(EF195 == 1) # filter out people working abroad

# drop rows where data on occupation, industry or region are missing
dsf_clean <- dsf_filtered %>%
  drop_na(EF114) %>%
  drop_na(EF137) %>%
  drop_na(EF564)

# add column to count number of observations (ungewichtete fallzahl) when grouping
dsf_clean$n_obs = 1

# convert integer dtypes to factors
#dsf_final <- dsf_clean %>%
#  mutate_if(is.integer, as.factor)

# -----------------------------------------------------------------------------
# Attachment of external data (with dummy data for now)
# -----------------------------------------------------------------------------

# occupational greenness and brownness shares at KldB 5-digit level
# Note: the current dataset is composed of dummy data and will be copied to a 
# separate excel/csv file that contains the actual values after the GWAP days
occupation_metadata <- read_excel(
  path = file.path(metadata_dir, "Kldb2010-Englisch.xls"),
  sheet = "OccupationMetadata"
)

# rename
occupation_metadata <- occupation_metadata %>%
  rename(
    EF114 = kldb2010_code, 
    EF114_name_en = kldb2010_name_en,
    EF114_name_de = kldb2010_name_de
  )

# code-name mappings of sectoral classification (wz-2008)
ind_class <- read_excel(
  path = file.path(metadata_dir, "klassifikation-wz-2008-englisch.xls"),
  sheet = "WZ 2008 Formatted",
  trim_ws = TRUE
)

# EF137 (Groups)
ind_class_ef137 <- ind_class %>% 
  filter(wz2008_levels == "Groups") %>%
  mutate(wz2008_code = as.numeric(wz2008_code)) %>%
  select("wz2008_code", "wz2008_name") %>%
  rename(EF137 = wz2008_code, EF137_name = wz2008_name)

# EF137UG1 (Divisions)
ind_class_ef137ug1 <- ind_class %>% 
  filter(wz2008_levels == "Divisions") %>%
  mutate(wz2008_code = as.numeric(wz2008_code)) %>%
  select("wz2008_code", "wz2008_name") %>%
  rename(EF137UG1 = wz2008_code, EF137UG1_name = wz2008_name)


# prepare join: remove dots from codes for join
#industry_classification <- industry_classification %>%
#  mutate(wz2008_code = str_replace_all(wz2008_code, pattern = "[.]", replacement = ""))

# join occupation metadata based on 5-digit kldb codes
dsf_merged <- left_join(
  x=dsf_clean,
  y=occupation_metadata,
  by="EF114"
)

# join industry sector names
dsf_merged <- left_join(
  x=dsf_merged,
  y=ind_class_ef137,
  by="EF137"
)

dsf_merged <- left_join(
  x=dsf_merged,
  y=ind_class_ef137ug1,
  by="EF137UG1"
)

# sort columns alphabetically
dsf_merged <- dsf_merged[, order(colnames(dsf_merged))]

# -----------------------------------------------------------------------------
# Analysis
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 1) Inspection of variables
# -----------------------------------------------------------------------------

# comparison of sum of country-wide projection numbers between raw and filtered data set
sum(dsf$EF952)
sum(dsf_merged$EF952)

# distribution of age
hist(dsf_merged$EF44)

# unique categories across occupations, industries and regions
print(paste("Unique occupations (5 digit): ", length(unique(dsf_merged$EF114))))
print(paste("Unique industries (3 digit): ", length(unique(dsf_merged$EF137))))
print(paste("Unique industries (2 digit): ", length(unique(dsf_merged$EF137UG1))))
print(paste("Unique regions (reg. anp.): ", length(unique(dsf_merged$EF564))))
print(paste("Unique regions (nuts II): ", length(unique(dsf_merged$EF189))))

# -----------------------------------------------------------------------------
# 2) Aggregation of occupational Greenness shares by industry and region
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 2.1) Grouping of occupational shares
# -----------------------------------------------------------------------------
# This is solely to understand how workers are distributed across the top
# occupations. No further analysis is envisioned.

# EF952 by occupation (5-digit)
EF952_by_EF114_abs <- dsf_merged %>%
  group_by(EF114, EF114_name_en) %>%
  summarise(
    n_obs=sum(n_obs),
    EF952_sum=sum(EF952),
    EF952_share_green_jrc_narrow = sum(EF952 * share_green_jrc_narrow),
    EF952_share_green_jrc_wide = sum(EF952 * share_brown_jrc_wide),
    EF952_share_green_esco = sum(EF952 * share_green_esco),
    EF952_share_brown_esco = sum(EF952 * share_brown_esco),
    EF952_share_green_eth = sum(EF952 * share_green_eth),
    EF952_share_brown_eth = sum(EF952 * share_brown_eth),
  ) %>%
  # no need to see those occupations with a very low count
  filter(n_obs >= 3)

write_csv2(EF952_by_EF114_abs, file=file.path(results_dir, "EF952_by_EF114_abs.csv"))

# -----------------------------------------------------------------------------
# 2.1) Grouping of occupational shares by region
# -----------------------------------------------------------------------------

# EF952 by EF189 (Region der Arbeitsstätte, NUTS II)
# -----------------------------------------------------------------------------

# relative values
EF952_by_EF189_rel <- dsf_merged %>%
  group_by(EF189) %>%
  summarise(
    n_obs=sum(n_obs),
    EF952_share_green_jrc_narrow = sum(EF952 * share_green_jrc_narrow) / sum(EF952),
    EF952_share_green_jrc_wide = sum(EF952 * share_brown_jrc_wide) / sum(EF952),
    EF952_share_green_esco = sum(EF952 * share_green_esco) / sum(EF952),
    EF952_share_brown_esco = sum(EF952 * share_brown_esco) / sum(EF952),
    EF952_share_green_eth = sum(EF952 * share_green_eth) / sum(EF952),
    EF952_share_brown_eth = sum(EF952 * share_brown_eth) / sum(EF952),
  )

write_csv2(EF952_by_EF189_rel, file=file.path(results_dir, "EF952_by_EF189_rel.csv"))


# absolute values
EF952_by_EF189_abs <- dsf_merged %>%
  group_by(EF189) %>%
  summarise(
    n_obs=sum(n_obs),
    EF952_sum = sum(EF952),
    EF952_share_green_jrc_narrow = sum(EF952 * share_green_jrc_narrow),
    EF952_share_green_jrc_wide = sum(EF952 * share_brown_jrc_wide),
    EF952_share_green_esco = sum(EF952 * share_green_esco),
    EF952_share_brown_esco = sum(EF952 * share_brown_esco),
    EF952_share_green_eth = sum(EF952 * share_green_eth),
    EF952_share_brown_eth = sum(EF952 * share_brown_eth),
  )

write_csv2(EF952_by_EF189_abs, file=file.path(results_dir, "EF952_by_EF189_abs.csv"))


# EF952 by EF564 (Regionale Anpassungsschicht, zwischen NUTS II und III)
# -----------------------------------------------------------------------------

# relative values
EF952_by_EF564_rel <- dsf_merged %>%
  group_by(EF564) %>%
  summarise(
    n_obs=sum(n_obs),
    EF952_share_green_jrc_narrow = sum(EF952 * share_green_jrc_narrow) / sum(EF952),
    EF952_share_green_jrc_wide = sum(EF952 * share_brown_jrc_wide) / sum(EF952),
    EF952_share_green_esco = sum(EF952 * share_green_esco) / sum(EF952),
    EF952_share_brown_esco = sum(EF952 * share_brown_esco) / sum(EF952),
    EF952_share_green_eth = sum(EF952 * share_green_eth) / sum(EF952),
    EF952_share_brown_eth = sum(EF952 * share_brown_eth) / sum(EF952),
  )

write_csv2(EF952_by_EF564_rel, file=file.path(results_dir, "EF952_by_EF564_rel.csv"))

# absolute values
EF952_by_EF564_abs <- dsf_merged %>%
  group_by(EF564) %>%
  summarise(
    n_obs=sum(n_obs),
    EF952_sum = sum(EF952),
    EF952_share_green_jrc_narrow = sum(EF952 * share_green_jrc_narrow),
    EF952_share_green_jrc_wide = sum(EF952 * share_brown_jrc_wide),
    EF952_share_green_esco = sum(EF952 * share_green_esco),
    EF952_share_brown_esco = sum(EF952 * share_brown_esco),
    EF952_share_green_eth = sum(EF952 * share_green_eth),
    EF952_share_brown_eth = sum(EF952 * share_brown_eth),
  )

write_csv2(EF952_by_EF564_abs, file=file.path(results_dir, "EF952_by_EF564_abs.csv"))

# -----------------------------------------------------------------------------
# 2.2) Grouping of occupational shares by industry
# -----------------------------------------------------------------------------

# EF952 by EF137 (3-digit)
# -----------------------------------------------------------------------------

# relative values
EF952_by_EF137_rel <- dsf_merged %>%
  group_by(EF137, EF137_name) %>%
  summarise(
    n_obs=sum(n_obs),
    EF952_share_green_jrc_narrow = sum(EF952 * share_green_jrc_narrow) / sum(EF952),
    EF952_share_green_jrc_wide = sum(EF952 * share_brown_jrc_wide) / sum(EF952),
    EF952_share_green_esco = sum(EF952 * share_green_esco) / sum(EF952),
    EF952_share_brown_esco = sum(EF952 * share_brown_esco) / sum(EF952),
    EF952_share_green_eth = sum(EF952 * share_green_eth) / sum(EF952),
    EF952_share_brown_eth = sum(EF952 * share_brown_eth) / sum(EF952)
  )

write_csv2(EF952_by_EF137_rel, file=file.path(results_dir, "EF952_by_EF137_rel.csv"))

# absolute values
EF952_by_EF137_abs <- dsf_merged %>%
  group_by(EF137, EF137_name) %>%
  summarise(
    n_obs=sum(n_obs),
    EF952_sum = sum(EF952),
    EF952_share_green_jrc_narrow = sum(EF952 * share_green_jrc_narrow),
    EF952_share_green_jrc_wide = sum(EF952 * share_brown_jrc_wide),
    EF952_share_green_esco = sum(EF952 * share_green_esco),
    EF952_share_brown_esco = sum(EF952 * share_brown_esco),
    EF952_share_green_eth = sum(EF952 * share_green_eth),
    EF952_share_brown_eth = sum(EF952 * share_brown_eth),
  )

write_csv2(EF952_by_EF137_abs, file=file.path(results_dir, "EF952_by_EF137_abs.csv"))

# EF952 by EF137UG1 (2-digit)
# -----------------------------------------------------------------------------

# relative values
EF952_by_EF137UG1_rel <- dsf_merged %>%
  group_by(EF137UG1, EF137UG1_name) %>%
  summarise(
    n_obs=sum(n_obs),
    EF952_share_green_jrc_narrow = sum(EF952 * share_green_jrc_narrow) / sum(EF952),
    EF952_share_green_jrc_wide = sum(EF952 * share_brown_jrc_wide) / sum(EF952),
    EF952_share_green_esco = sum(EF952 * share_green_esco) / sum(EF952),
    EF952_share_brown_esco = sum(EF952 * share_brown_esco) / sum(EF952),
    EF952_share_green_eth = sum(EF952 * share_green_eth) / sum(EF952),
    EF952_share_brown_eth = sum(EF952 * share_brown_eth) / sum(EF952)
  )

write_csv2(EF952_by_EF137UG1_rel, file=file.path(results_dir, "EF952_by_EF137UG1_rel.csv"))

# absolute values
EF952_by_EF137UG1_abs <- dsf_merged %>%
  group_by(EF137UG1, EF137UG1_name) %>%
  summarise(
    n_obs=sum(n_obs),
    EF952_sum = sum(EF952),
    EF952_share_green_jrc_narrow = sum(EF952 * share_green_jrc_narrow),
    EF952_share_green_jrc_wide = sum(EF952 * share_brown_jrc_wide),
    EF952_share_green_esco = sum(EF952 * share_green_esco),
    EF952_share_brown_esco = sum(EF952 * share_brown_esco),
    EF952_share_green_eth = sum(EF952 * share_green_eth),
    EF952_share_brown_eth = sum(EF952 * share_brown_eth),
  )

write_csv2(EF952_by_EF137UG1_abs, file=file.path(results_dir, "EF952_by_EF137UG1_abs.csv"))

# -----------------------------------------------------------------------------
# 2.3) Grouping of occupational shares by industry and regions
# -----------------------------------------------------------------------------

# EF952 by EF137 (3-digit) and EF564 (reg. anp.)
# -----------------------------------------------------------------------------
# --> zu viele Einzelfälle, von Analyse wird abgesehen

# EF952 by EF137 (3-digit) and EF189 (NUTS II)
# -----------------------------------------------------------------------------
# --> zu viele Einzelfälle, von Analyse wird abgesehen


# EF952 by industry (2-digit) and EF189 (NUTS II)
# -----------------------------------------------------------------------------
# --> recht viele Einzelfälle (etwa 10%). möglicherweise vertretbar, sonst 
# aggregation auf 1-digit industrien?

# absolute
EF952_by_EF137UG1_and_EF189_abs <- dsf_merged %>%
  group_by(EF189, EF137UG1, EF137UG1_name) %>%
  summarise(
    n_obs=sum(n_obs),
    EF952_sum = sum(EF952),
    EF952_share_green_jrc_narrow = sum(EF952 * share_green_jrc_narrow),
    EF952_share_green_jrc_wide = sum(EF952 * share_brown_jrc_wide),
    EF952_share_green_esco = sum(EF952 * share_green_esco),
    EF952_share_brown_esco = sum(EF952 * share_brown_esco),
    EF952_share_green_eth = sum(EF952 * share_green_eth),
    EF952_share_brown_eth = sum(EF952 * share_brown_eth),
  )

# relative
EF952_by_EF137UG1_and_EF189_rel <- dsf_merged %>%
  group_by(EF189, EF137UG1, EF137UG1_name) %>%
  summarise(
    n_obs=sum(n_obs),
    EF952_share_green_jrc_narrow = sum(EF952 * share_green_jrc_narrow) / sum(EF952),
    EF952_share_green_jrc_wide = sum(EF952 * share_brown_jrc_wide) / sum(EF952),
    EF952_share_green_esco = sum(EF952 * share_green_esco) / sum(EF952),
    EF952_share_brown_esco = sum(EF952 * share_brown_esco) / sum(EF952),
    EF952_share_green_eth = sum(EF952 * share_green_eth) / sum(EF952),
    EF952_share_brown_eth = sum(EF952 * share_brown_eth) / sum(EF952),
  )

# EF952 by industry (2-digit) and EF188 (NUTS I)
# -----------------------------------------------------------------------------
# --> recht viele Einzelwerte (etwa 10%). möglicherweise vertretbar, sonst 
# aggregation auf 1-digit industrien, oder fokus auf besser besetzte industrien.

# absolute
EF952_by_EF137UG1_and_EF188_abs <- dsf_merged %>%
  group_by(EF137UG1, EF137UG1_name, EF188) %>%
  summarise(
    n_obs=sum(n_obs),
    EF952_sum = sum(EF952),
    EF952_share_green_jrc_narrow = sum(EF952 * share_green_jrc_narrow),
    EF952_share_green_jrc_wide = sum(EF952 * share_brown_jrc_wide),
    EF952_share_green_esco = sum(EF952 * share_green_esco),
    EF952_share_brown_esco = sum(EF952 * share_brown_esco),
    EF952_share_green_eth = sum(EF952 * share_green_eth),
    EF952_share_brown_eth = sum(EF952 * share_brown_eth),
  )

write_csv2(EF952_by_EF137UG1_and_EF188_abs, file=file.path(results_dir, "EF952_by_EF137UG1_and_EF188_abs.csv"))

# relative
EF952_by_EF137UG1_and_EF188_rel <- dsf_merged %>%
  group_by(EF137UG1, EF137UG1_name, EF188) %>%
  summarise(
    n_obs=sum(n_obs),
    EF952_share_green_jrc_narrow = sum(EF952 * share_green_jrc_narrow) / sum(EF952),
    EF952_share_green_jrc_wide = sum(EF952 * share_brown_jrc_wide) / sum(EF952),
    EF952_share_green_esco = sum(EF952 * share_green_esco) / sum(EF952),
    EF952_share_brown_esco = sum(EF952 * share_brown_esco) / sum(EF952),
    EF952_share_green_eth = sum(EF952 * share_green_eth) / sum(EF952),
    EF952_share_brown_eth = sum(EF952 * share_brown_eth) / sum(EF952),
  )

write_csv2(EF952_by_EF137UG1_and_EF188_rel, file=file.path(results_dir, "EF952_by_EF137UG1_and_EF188_rel.csv"))


# -----------------------------------------------------------------------------
# 3) Correlation of occupational shares with demographic characteristics

# point-biserial correlation
# -----------------------------------------------------------------------------

# with age
cor.test(x = dsf_merged$EF44, y = dsf_merged$share_green_jrc_narrow)

# with sex
cor.test(x = dsf_merged$EF46, y = dsf_merged$share_green_jrc_narrow)

# with income
cor.test(x = dsf_merged$EF436, y = dsf_merged$share_green_jrc_narrow)
cor.test(x = dsf_merged$EF442, y = dsf_merged$share_green_jrc_narrow)

# with education level
cor.test(x = dsf_merged$EF517, y = dsf_merged$share_green_jrc_narrow)
cor.test(x = dsf_merged$EF540, y = dsf_merged$share_green_jrc_narrow)
