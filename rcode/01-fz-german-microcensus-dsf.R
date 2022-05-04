
# -----------------------------------------------------------------------------
# remove all objects from R workspace
rm(list=ls())

# set working directory (has to be changed at GWAP)
rootdir = "T:/Documents/Projects/04_jrc_green-skills-regional/03_data-analysis/re4gt"
setwd(rootdir)

# -----------------------------------------------------------------------------
# Load necessary packages
library(tidyverse)
library(readxl)

# set plotting theme
theme_set(theme_classic())

# -----------------------------------------------------------------------------

# load microcensus data
fpath_dsf_csv <- file.path(getwd(), "data", "raw", "lfs", "de", "DSF_MZ 2019.CSV")


# specify data types for select cols
# colClasses=c(
#   "EF951"="numeric",
#   "EF952"="numeric",
#   "EF953"="numeric"
# )

# read DSF, csv version
dsf <- read.csv(
  file=fpath_dsf_csv,
  header=TRUE,
  sep=";",
  dec=",",
  strip.white=TRUE,
  # colClasses = colClasses
)



# replace all values < 0 with NA ("Not applicable" cases) 
dsf[dsf < 0] = NA

str(dsf)

# -----------------------------------------------------------------------------
# Preprocessing
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
  # "EF174",
  "EF175",
  # place of work
  "EF189", 
  # "EF196",
  "EF195",
  "EF564",
  # "EF568",
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
    # EF174 = replace(EF174, EF174 %in% non_response_codes, NA),
    EF189 = replace(EF189, EF189 %in% non_response_codes, NA),
    # EF196 = replace(EF196, EF196 %in% non_response_codes, NA),
    EF436 = replace(EF436, EF436 %in% c(90, 99), NA),
    EF442 = replace(EF442, EF442 %in% c(99), NA),
    EF517 = replace(EF517, EF517 %in% c(999), NA),
    EF540 = replace(EF540, EF442 %in% c(99), NA),
  )

# filtering criteria
age_min <- 0
age_max <- 95

# filter based on ILO/Eurostat conditions of active labour force
dsf_filtered <- dsf_nans_coded %>%
  filter(EF39 == 1) %>% # working against payment
  filter(EF44 >= age_min & EF44 <= age_max) %>% # age restriction
  filter(EF195 == 1) # filter out people working abroad 

# convert dtypes
# dsf_final <- dsf_filtered %>%
#   mutate_if(is.integer, as.factor)

# -----------------------------------------------------------------------------
# convert integer cols to factors while specifying levels from codebook
# -----------------------------------------------------------------------------
fpath_codebook <- file.path(getwd(), "rcode", "data", "codebook_microcensus_2019.xlsx")
codebook <- read_excel(fpath_codebook)

dsf_factors <- dsf_filtered
names(dsf_factors)
cols_to_convert = c("EF114")

for (n in cols_to_convert){
  temp <- filter(codebook, var_name == n) 
  dsf_factors[[n]] <- factor(dsf_factors[[n]], levels = temp$value, labels = temp$label_en)
}

str(dsf_factors)


dsf_final <- dsf_factors
# -----------------------------------------------------------------------------
# Analysis
# -----------------------------------------------------------------------------

# Aggregation of yearly projection factors by occupation (5-digit)
dsf_final %>%
  group_by(EF114) %>%
  summarise(
    sum_workers=sum(EF952)
  )

# Aggregation of yearly projection factors by industry (3-digit)
dsf_final %>%
  group_by(EF137) %>%
  summarise(
    sum_workers=sum(EF952)
  )

# Aggregation of yearly projection factors by occupation (5-digit) and industry (3-digit)
dsf_final %>%
  group_by(EF114, EF137) %>%
  summarise(
    sum_workers=sum(EF952)
  )

# Aggregation of yearly projection factors by occupation (5-digit) and region (reg. anp.)
dsf_final %>%
  group_by(EF114, EF564) %>%
  summarise(
    sum_workers=sum(EF952)
  )
