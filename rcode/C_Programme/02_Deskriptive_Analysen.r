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

# setwd("<hier werden die R-Pakete abgelegt>")
# install.packages(pkgs=c("tidyverse", "readxl"), type = "source", repos = NULL)


# KDFV-Nutzung: 

# install.packages(pkgs=c("tidyverse", "readxl"), dependencies=TRUE)

# Zu verwendende Packages laden

library(tidyverse)
library(readxl)
library(Hmisc)

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
  "EF39", # filtering
  "EF44", "EF46", # demographics
  "EF114", "EF114UG1", "EF114UG2", "EF114UG3", "EF114UG4", # occupation
  "EF137", "EF137UG1", # industry
  "EF172", "EF175", # workplace characteristics
  "EF188", "EF189", "EF195", "EF564", # place of work
  "EF436", "EF442", # income
  "EF517", "EF540", "EF564", # education
  "EF951", "EF952", "EF953" # projection factors
)

# filtering criteria
age_min <- 15
age_max <- 67
# -----------------------------------------------------------------------------
# read data
dfr <- read.csv(file.path(datenpfad, paste(dateiname,  ".CSV",  sep="")), header = T, sep=";", dec = ",", strip.white = TRUE, colClasses = colClasses)


# extract reduced df based on core variables
dff <- dfr %>%
  select(all_of(vars))

# replace all values < 0 with NA ("Not applicable" cases). Apparently not needed for GWAP file, but needed for Datenstrukturfile
if (FDZ == 0){
  dff[dff < 0] = NA
}

# manually code nan values due to non-responses (9 - 99999) for selected variables
dff <- dff %>%
  mutate(
    EF114 = replace(EF114, EF114 %in% non_response_codes, NA),
    EF114UG1 = replace(EF114UG1, EF114UG1 %in% non_response_codes, NA),
    EF114UG1 = replace(EF114UG1, EF114UG1 %in% non_response_codes, NA),
    EF114UG2 = replace(EF114UG2, EF114UG2 %in% non_response_codes, NA),
    EF114UG3 = replace(EF114UG3, EF114UG3 %in% non_response_codes, NA),
    EF137 = replace(EF137, EF137 %in% non_response_codes, NA),
    EF172 = replace(EF172, EF172 %in% non_response_codes, NA),
    EF175 = replace(EF175, EF175 %in% non_response_codes, NA),
    EF188 = replace(EF188, EF188 %in% c(99), NA),
    EF189 = replace(EF189, EF189 %in% non_response_codes, NA),
    # EF196 = replace(EF196, EF196 %in% non_response_codes, NA), # not available in KDFV file
    EF436 = replace(EF436, EF436 %in% c(90, 99), NA),
    EF442 = replace(EF442, EF442 %in% c(99), NA),
    EF517 = replace(EF517, EF517 %in% c(999), NA),
    EF540 = replace(EF540, EF442 %in% c(99), NA),
  )
# -----------------------------------------------------------------------------
# filter for active, domestic labour force
dff <- dff %>%
  filter(EF39 == 1) %>% # working against payment
  filter(EF44 >= age_min & EF44 <= age_max) %>% # age restriction
  filter(EF195 == 1) # filter out people working abroad

# drop rows where data on occupation, industry or region are missing
dff <- dff %>%
  drop_na(EF114) %>%
  drop_na(EF137) %>%
  drop_na(EF564)

# add column to count number of observations (ungewichtete fallzahl) when grouping
dff$n_obs = 1

# -----------------------------------------------------------------------------
# 1.1 Attachment of external data (with dummy data for now)
# -----------------------------------------------------------------------------

# specify version of green/brown list (!!!)
# versions: 
occ_list_versions <- c(
  "full_list", 
  "long_list_green", "long_list_brown", 
  "short_list_green", "short_list_brown",
  "short_list_green_tobi", "short_list_brown_tobi"
  )

# START OF LOOP
for (occ_list_version in occ_list_versions) {
  print(occ_list_version)

  # occupational greenness and brownness shares at KldB 5-digit level
  # Note: the current dataset is composed of dummy data and will be copied to a 
  # separate excel/csv file that contains the actual values after the GWAP days
  occupation_metadata <- read_excel(
    path = file.path(metadatenpfad, "occ_metadata_en_kldb2010_final_v2_v3_merged.xlsx"),
    sheet = occ_list_version
  )
  
  # replace NAs with 0
  occupation_metadata[is.na(occupation_metadata)] <- 0
  
  # rename
  occupation_metadata <- occupation_metadata %>%
    rename(
      EF114 = kldb2010_code, 
      EF114_name_en = kldb2010_name_en,
      EF114_name_de = kldb2010_name_de
    )
  # -----------------------------------------------------------------------------
  # code-name mappings of sectoral classification (wz-2008)
  ind_class <- read_excel(
    path = file.path(metadatenpfad, "klassifikation-wz-2008-englisch.xls"),
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
  # -----------------------------------------------------------------------------
  # join occupation metadata based on 5-digit kldb codes
  dfm <- left_join(
    x=dff,
    y=occupation_metadata,
    by="EF114"
  )
  
  # join industry sector names
  dfm <- left_join(
    x=dfm,
    y=ind_class_ef137,
    by="EF137"
  )
  
  dfm <- left_join(
    x=dfm,
    y=ind_class_ef137ug1,
    by="EF137UG1"
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
  
  # comparison of sum of country-wide projection numbers between raw and filtered data set
  sum(dfr$EF952)
  sum(dfm$EF952)
  
  # distribution of age
  hist(dfm$EF44)
  
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
  EF952_by_EF114_abs <- dfm %>%
    group_by(EF114, EF114_name_en) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      EF952_share_green_esco = sum(EF952 * share_green_esco),
      EF952_share_brown_esco = sum(EF952 * share_brown_esco),
      EF952_share_green_esco_ess = sum(EF952 * share_green_esco_ess),
      EF952_share_brown_esco_ess = sum(EF952 * share_brown_esco_ess),
      EF952_share_green_gtp = sum(EF952 * share_green_gtp),
      EF952_share_green_vona2018 = sum(EF952 * share_green_vona2018),
      EF952_share_green_jrc = sum(EF952 * share_green_jrc),
      EF952_share_brown_vona2018 = sum(EF952 * share_brown_vona2018),
    ) %>%
    # no need to see those occupations with a very low count
    filter(n_obs >= 3)
  
  write_csv2(EF952_by_EF114_abs, file=file.path(outputpfad, occ_list_version, "EF952_by_EF114_abs.csv"))
  
  # -----------------------------------------------------------------------------
  # 2.3) Grouping of occupational shares by region
  # -----------------------------------------------------------------------------
  
  # EF952 by EF189 (Region der Arbeitsstätte, NUTS II)
  # -----------------------------------------------------------------------------
  
  # relative values
  EF952_by_EF189_rel <- dfm %>%
    group_by(EF189) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      EF952_share_green_esco = sum(EF952 * share_green_esco) / sum(EF952),
      EF952_share_brown_esco = sum(EF952 * share_brown_esco) / sum(EF952),
      EF952_share_green_esco_ess = sum(EF952 * share_green_esco_ess) / sum(EF952),
      EF952_share_brown_esco_ess = sum(EF952 * share_brown_esco_ess) / sum(EF952),
      EF952_share_green_gtp = sum(EF952 * share_green_gtp) / sum(EF952),
      EF952_share_green_vona2018 = sum(EF952 * share_green_vona2018) / sum(EF952),
      EF952_share_green_jrc = sum(EF952 * share_green_jrc) / sum(EF952),
      EF952_share_brown_vona2018 = sum(EF952 * share_brown_vona2018) / sum(EF952),
    )
  
  write_csv2(EF952_by_EF189_rel, file=file.path(outputpfad, occ_list_version, "EF952_by_EF189_rel.csv"))
  
  
  # absolute values
  EF952_by_EF189_abs <- dfm %>%
    group_by(EF189) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      EF952_share_green_esco = sum(EF952 * share_green_esco),
      EF952_share_brown_esco = sum(EF952 * share_brown_esco),
      EF952_share_green_esco_ess = sum(EF952 * share_green_esco_ess),
      EF952_share_brown_esco_ess = sum(EF952 * share_brown_esco_ess),
      EF952_share_green_gtp = sum(EF952 * share_green_gtp),
      EF952_share_green_vona2018 = sum(EF952 * share_green_vona2018),
      EF952_share_green_jrc = sum(EF952 * share_green_jrc),
      EF952_share_brown_vona2018 = sum(EF952 * share_brown_vona2018),
    )
  
  write_csv2(EF952_by_EF189_abs, file=file.path(outputpfad, occ_list_version, "EF952_by_EF189_abs.csv"))
  
  
  # EF952 by EF564 (Regionale Anpassungsschicht, zwischen NUTS II und III)
  # -----------------------------------------------------------------------------
  
  # relative values
  EF952_by_EF564_rel <- dfm %>%
    group_by(EF564) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      EF952_share_green_esco = sum(EF952 * share_green_esco) / sum(EF952),
      EF952_share_brown_esco = sum(EF952 * share_brown_esco) / sum(EF952),
      EF952_share_green_esco_ess = sum(EF952 * share_green_esco_ess) / sum(EF952),
      EF952_share_brown_esco_ess = sum(EF952 * share_brown_esco_ess) / sum(EF952),
      EF952_share_green_gtp = sum(EF952 * share_green_gtp) / sum(EF952),
      EF952_share_green_vona2018 = sum(EF952 * share_green_vona2018) / sum(EF952),
      EF952_share_green_jrc = sum(EF952 * share_green_jrc) / sum(EF952),
      EF952_share_brown_vona2018 = sum(EF952 * share_brown_vona2018) / sum(EF952),
    )
  
  write_csv2(EF952_by_EF564_rel, file=file.path(outputpfad, occ_list_version, "EF952_by_EF564_rel.csv"))
  
  # absolute values
  EF952_by_EF564_abs <- dfm %>%
    group_by(EF564) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      EF952_share_green_esco = sum(EF952 * share_green_esco),
      EF952_share_brown_esco = sum(EF952 * share_brown_esco),
      EF952_share_green_esco_ess = sum(EF952 * share_green_esco_ess),
      EF952_share_brown_esco_ess = sum(EF952 * share_brown_esco_ess),
      EF952_share_green_gtp = sum(EF952 * share_green_gtp),
      EF952_share_green_vona2018 = sum(EF952 * share_green_vona2018),
      EF952_share_green_jrc = sum(EF952 * share_green_jrc),
      EF952_share_brown_vona2018 = sum(EF952 * share_brown_vona2018),
    )
  
  write_csv2(EF952_by_EF564_abs, file=file.path(outputpfad, occ_list_version, "EF952_by_EF564_abs.csv"))
  
  # -----------------------------------------------------------------------------
  # 2.4) Grouping of occupational shares by industry
  # -----------------------------------------------------------------------------
  
  # EF952 by EF137 (3-digit)
  # -----------------------------------------------------------------------------
  
  # relative values
  EF952_by_EF137_rel <- dfm %>%
    group_by(EF137, EF137_name) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      EF952_share_green_esco = sum(EF952 * share_green_esco) / sum(EF952),
      EF952_share_brown_esco = sum(EF952 * share_brown_esco) / sum(EF952),
      EF952_share_green_esco_ess = sum(EF952 * share_green_esco_ess) / sum(EF952),
      EF952_share_brown_esco_ess = sum(EF952 * share_brown_esco_ess) / sum(EF952),
      EF952_share_green_gtp = sum(EF952 * share_green_gtp) / sum(EF952),
      EF952_share_green_vona2018 = sum(EF952 * share_green_vona2018) / sum(EF952),
      EF952_share_green_jrc = sum(EF952 * share_green_jrc) / sum(EF952),
      EF952_share_brown_vona2018 = sum(EF952 * share_brown_vona2018) / sum(EF952),
    )
  
  write_csv2(EF952_by_EF137_rel, file=file.path(outputpfad, occ_list_version, "EF952_by_EF137_rel.csv"))
  
  # absolute values
  EF952_by_EF137_abs <- dfm %>%
    group_by(EF137, EF137_name) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      EF952_share_green_esco = sum(EF952 * share_green_esco),
      EF952_share_brown_esco = sum(EF952 * share_brown_esco),
      EF952_share_green_esco_ess = sum(EF952 * share_green_esco_ess),
      EF952_share_brown_esco_ess = sum(EF952 * share_brown_esco_ess),
      EF952_share_green_gtp = sum(EF952 * share_green_gtp),
      EF952_share_green_vona2018 = sum(EF952 * share_green_vona2018),
      EF952_share_green_jrc = sum(EF952 * share_green_jrc),
      EF952_share_brown_vona2018 = sum(EF952 * share_brown_vona2018),
    )
  
  write_csv2(EF952_by_EF137_abs, file=file.path(outputpfad, occ_list_version, "EF952_by_EF137_abs.csv"))
  
  # EF952 by EF137UG1 (2-digit)
  # -----------------------------------------------------------------------------
  
  # relative values
  EF952_by_EF137UG1_rel <- dfm %>%
    group_by(EF137UG1, EF137UG1_name) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      EF952_share_green_esco = sum(EF952 * share_green_esco) / sum(EF952),
      EF952_share_brown_esco = sum(EF952 * share_brown_esco) / sum(EF952),
      EF952_share_green_esco_ess = sum(EF952 * share_green_esco_ess) / sum(EF952),
      EF952_share_brown_esco_ess = sum(EF952 * share_brown_esco_ess) / sum(EF952),
      EF952_share_green_gtp = sum(EF952 * share_green_gtp) / sum(EF952),
      EF952_share_green_vona2018 = sum(EF952 * share_green_vona2018) / sum(EF952),
      EF952_share_green_jrc = sum(EF952 * share_green_jrc) / sum(EF952),
      EF952_share_brown_vona2018 = sum(EF952 * share_brown_vona2018) / sum(EF952),
    )
  
  write_csv2(EF952_by_EF137UG1_rel, file=file.path(outputpfad, occ_list_version, "EF952_by_EF137UG1_rel.csv"))
  
  # absolute values
  EF952_by_EF137UG1_abs <- dfm %>%
    group_by(EF137UG1, EF137UG1_name) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      EF952_share_green_esco = sum(EF952 * share_green_esco),
      EF952_share_brown_esco = sum(EF952 * share_brown_esco),
      EF952_share_green_esco_ess = sum(EF952 * share_green_esco_ess),
      EF952_share_brown_esco_ess = sum(EF952 * share_brown_esco_ess),
      EF952_share_green_gtp = sum(EF952 * share_green_gtp),
      EF952_share_green_vona2018 = sum(EF952 * share_green_vona2018),
      EF952_share_green_jrc = sum(EF952 * share_green_jrc),
      EF952_share_brown_vona2018 = sum(EF952 * share_brown_vona2018),
    )
  
  write_csv2(EF952_by_EF137UG1_abs, file=file.path(outputpfad, occ_list_version, "EF952_by_EF137UG1_abs.csv"))
  
  
  # -----------------------------------------------------------------------------
  # 3) Correlation and distributions of occupational shares with/across demographic characteristics
  
  # point-biserial correlation
  # -----------------------------------------------------------------------------
  
  # convert integer dtypes to factors
  #dfm <- dfm %>%
  #  mutate_if(is.integer, as.factor)
  
  dfm_long <- pivot_longer(dfm, starts_with("share"), names_to = "share_type", values_to = "share_value")
  
  # with age
  cor.test(x = dfm$EF44, y = dfm$share_green_esco)
  
  # bin age variable
  dfm_long$EF44_binned <- cut_width(dfm_long$EF44, width=5, boundary=0)
  
  ggplot(dfm_long, aes(x = as.factor(EF44_binned), y = share_value)) +
    geom_boxplot() +
    geom_jitter(width=0.1, alpha=0.2) +
    facet_wrap(~share_type)
  
  ggsave(
    "shares_by_EF44.pdf", 
    path=file.path(outputpfad, occ_list_version),
    height=5,
    width = 20
  )
  
  # output für prüfung: number of obs per bin
  dfm_long %>%
    group_by(share_type, EF44_binned) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      mean=mean(share_value, na.rm = TRUE),
      mean_weighted=wtd.mean(share_value, EF952, na.rm=TRUE),
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
  cor.test(x = dfm$EF46, y = dfm$share_green_esco)
  
  ggplot(dfm_long, aes(x = as.factor(EF46), y = share_value)) +
    geom_boxplot() +
    geom_jitter(width=0.1, alpha=0.2) +
    facet_wrap(~share_type)
  
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
      mean_weighted=wtd.mean(share_value, EF952, na.rm=TRUE),
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
  cor.test(x = dfm$EF436, y = dfm$share_green_esco)
  cor.test(x = dfm$EF442, y = dfm$share_green_esco)
  
  ggplot(dfm_long, aes(x = as.factor(EF436), y = share_value)) +
    geom_boxplot() +
    geom_jitter(width=0.1, alpha=0.2) +
    facet_wrap(~share_type)
  
  ggsave(
    "shares_by_EF436.pdf", 
    path=file.path(outputpfad, occ_list_version),
    height=5,
    width = 20
  )
  
  # output für prüfung: number of obs per bin
  dfm_long %>%
    group_by(share_type, EF436) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      mean=mean(share_value, na.rm = TRUE),
      mean_weighted=wtd.mean(share_value, EF952, na.rm=TRUE),
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
  
  
  ggplot(dfm_long, aes(x = as.factor(EF442), y = share_value)) +
    geom_boxplot() +
    geom_jitter(width=0.1, alpha=0.2) +
    facet_wrap(~share_type)
  
  ggsave(
    "shares_by_EF442.pdf", 
    path=file.path(outputpfad, occ_list_version),
    height=5,
    width = 20
  )
  
  # output für prüfung: number of obs per bin
  dfm_long %>%
    group_by(share_type, EF442) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      mean=mean(share_value, na.rm = TRUE),
      mean_weighted=wtd.mean(share_value, EF952, na.rm=TRUE),
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
  
  
  # with education level
  cor.test(x = dfm$EF517, y = dfm$share_green_esco)
  cor.test(x = dfm$EF540, y = dfm$share_green_esco)
  
  ggplot(dfm_long, aes(x = as.factor(EF517), y = share_value)) +
    geom_boxplot() +
    geom_jitter(width=0.1, alpha=0.2) +
    facet_wrap(~share_type)
  
  ggsave(
    "shares_by_EF517.pdf", 
    path=file.path(outputpfad, occ_list_version),
    height=5,
    width = 20
  )
  
  # output für prüfung: number of obs per bin
  dfm_long %>%
    group_by(share_type, EF517) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      mean=mean(share_value, na.rm = TRUE),
      mean_weighted=wtd.mean(share_value, EF952, na.rm=TRUE),
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
  
  
  ggplot(dfm_long, aes(x = as.factor(EF540), y = share_value)) +
    geom_boxplot() +
    geom_jitter(width=0.1, alpha=0.2) +
    facet_wrap(~share_type)
  
  ggsave(
    "shares_by_EF540.pdf", 
    path=file.path(outputpfad, occ_list_version),
    height=5,
    width = 20
  )
  
  # output für prüfung: number of obs per bin
  dfm_long %>%
    group_by(share_type, EF540) %>%
    summarise(
      n_obs=sum(n_obs),
      EF952_sum=sum(EF952),
      mean=mean(share_value, na.rm = TRUE),
      mean_weighted=wtd.mean(share_value, EF952, na.rm=TRUE),
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
  
} # END OF LOOP

#	-------------------------------------------------------------------------------------------------------------------
#	H I N W E I S:

# Die vorliegende Mustersyntax stellt ein Beispiel für eine Erstsyntax dar. Wenn in den folgenden Syntaxen 
# Auswertungen gemacht werden, die einen inhaltlichen Bezug zu bereits erstellten Ergebnissen haben, sind die 
# Bezüge zu den entsprechenden vorherigen Syntaxen sowohl bei der Datenaufbereitung als auch bei der Auswertung in 
# einem Kommentar kenntlich zu machen.
#	-------------------------------------------------------------------------------------------------------------------