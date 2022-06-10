# Timestamp einfügen
date()

#	-------------------------------------------------------------------------------------------------------------------
#	----
#	----	Block II: Bearbeitung der Daten
#	----
#	-------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------

#   Titel des Projekts: 		    	<Frauen und Arbeit in der Bundesrepublik>
#   Datengrundlage: 		  	    	<Beispiel Mikrozensus 2012>

#   Dateiname des Programmcodes:  <syntaxname.r>
#   erstellt: 						        <Datum> 
#   von: 							            <Name> 
#   E-Mail: 					          	<E-Mail-Adresse> 
#   Tel.: 						          	<Telefonnummer> 

#   Dateiname des Output-Files: 	<outputname.log> 


#   Grundriss des Programms: 
#        <Programm zur Untersuchung von mehrfachen Personensätzen (Check der Datenbasis), 
#         deskriptive Analysen> 


#   Verwendete Variablen (Beispieldatensatz hier: Mikrozensus 2012): 
#   Originalvariablen: 	
#         EF1:   	Land der Bundesrepublik 
#         EF2:   	Regierungsbezirk 
#         EF3:  	Auswahlbezirks-Nummer 
#         EF4:  	systemfreie Lfd. Nr. d. Haushalts 
#         EF5:  	systemfreie Lfd. Nr. d. Person im Haushalt
#         EF25:  	systemfreie Lfd. Nr. d. Familie im Haushalt
#         EF30:  	Bevölkerung am Hauptwohnsitz
#         EF31:  	Bevölkerung in Privathaushalten
#         EF44:  	Alter
#         EF46:  	Geschlecht 
#         EF49:  	Familienstand
#         EF310: 	Höchster allgemeiner Schulabschluss
#         EF952: 	Standardhochrechnungsfaktor Jahr (Basis: Zensus 2011)>


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
    EF196 = replace(EF196, EF196 %in% non_response_codes, NA), # not available in KDFV file
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

# occupational greenness and brownness shares at KldB 5-digit level
# Note: the current dataset is composed of dummy data and will be copied to a 
# separate excel/csv file that contains the actual values after the GWAP days
occupation_metadata <- read_excel(
  path = file.path(metadatenpfad, "Kldb2010-Englisch.xls"),
  sheet = "OccupationMetadata"
)

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

table(dfm$EF114)

#	-------------------------------------------------------------------------------------------------------------------
#	H I N W E I S:

# Die vorliegende Mustersyntax stellt ein Beispiel für eine Erstsyntax dar. Wenn in den folgenden Syntaxen 
# Auswertungen gemacht werden, die einen inhaltlichen Bezug zu bereits erstellten Ergebnissen haben, sind die 
# Bezüge zu den entsprechenden vorherigen Syntaxen sowohl bei der Datenaufbereitung als auch bei der Auswertung in 
# einem Kommentar kenntlich zu machen.
#	-------------------------------------------------------------------------------------------------------------------