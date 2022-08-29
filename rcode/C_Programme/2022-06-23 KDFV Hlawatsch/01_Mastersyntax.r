#	-------------------------------M U S T E R P R O G R A M M   R ---------------------------------------------------

# Hinweis: Das Musterprogramm dient Ihnen zur Orientierung bei der Erstellung Ihres Programmcodes.            	
# Das Ziel ist, Ihre Outputfiles bestm?glich f?r die Geheimhaltungspr?fung aufzubereiten.                     	
# Bitte beachten Sie: Dieses Musterprogramm enth?lt keine statistikspezifischen Hilfestellungen zur           	
# Aufbereitung und Auswertung der von Ihnen beantragten Daten.                                                	

# Vorab einige grundlegende Punkte zur Arbeit mit R im FDZ-Kontext:

# - Bitte l?schen Sie nicht mehr ben?tigte Temp- und/oder Arbeitsdateien am Ende Ihres Programmes.					

# - Bitte legen Sie analog zum Musterprogramm eine Masterdatei an (Teil 1 des Musterprogramms) und 
#   erstellen Sie separate Dateien f?r Ihre Auswertungssyntaxen (Teil 2 des Musterprogramms).
#   
# - Bitte definieren Sie in der Masterdatei Ihre Arbeitsumgebung (z.B. GWAP oder KDFV) und f?hren 
#   Sie Ihre (ggf. unterschiedlichen) Datens?tze ein.	

# - Bitte ber?cksichtigen Sie bei all Ihren Auswertungen die "Basisanforderungen an die Syntax" sowie die
#   "Kriterien zur Zulassung von Output", die Sie in unserer Brosch?re finden!

# Bitte beachten Sie auch, dass der online-Abruf von R-Paketen ?ber die FDZ nicht m?glich ist. Wenn Sie
# R-Pakete nutzen m?chten, stellen Sie uns diese bitte als lokal abzuspeichernde Datei bereit. R-Pakete
# werden nur nach vorheriger Pr?fung zugelassen.

#	-------------------------------------------------------------------------------------------------------------------
# ----
#	----	Grundeinstellungen
#	----
#	-------------------------------------------------------------------------------------------------------------------

# Speicher leeren

rm(list=ls()) 

# ggf. weiterf?hrende Grundeinstellungen 



#	-------------------------------------------------------------------------------------------------------------------
#	----
#	----	Block I: Arbeitsumgebung definieren
# ----
#	-------------------------------------------------------------------------------------------------------------------

# Im FDZ unterscheiden wir grunds?tzlich drei Arbeitsumgebungen: 
# 0. eigene Arbeitsumgebung im B?ro/zu Hause
# 1. kontrollierte Datenfernverarbeitung (KDFV)
# 2. Gastwissenschaftsarbeitsplatz (GWAP)

# Es gibt FDZ-Projekte, die ausschlie?lich in einer Arbeitsumgebung laufen, z.B. reine GWAP-Projekte.
# Es gibt jedoch auch FDZ-Projekte, die in mehreren Arbeitsumgebungen laufen. So k?nnen z.B. ausgew?hlte Datens?tze nicht 
# im kompletten Umfang an den GWAP gestellt werden (Wirtschaftsdaten, Steuerdaten). Nutzende haben am GWAP lediglich 
# eingeschr?nkten Zugang auf die Daten, k?nnen aber Auswertungsprogramme am GWAP erstellen. Diese werden dann von 
# FDZ-Mitarbeiter/-innen ?ber die KDFV auf den Originaldaten laufen gelassen. Dazu ist eine Anpassung der Pfadangaben 
# notwendig.

# Um diese Grundeinstellungen ?bersichtlich vorzunehmen, bitten wir Sie, Ihre Arbeitsumgebungen zu definieren und die
# entsprechenden Pfade anzulegen. 

# Bitte unterscheiden Sie zwischen den folgenden drei Arbeitsumgebungen und passen Sie f?r alle relevanten
# Arbeitsumgebungen die Pfade an. 
# Bitte l?schen Sie nicht ben?tigte Pfade und erg?nzen fehlende.

#	0: eigener Arbeitsplatz (z.B. Datenstrukturfile)
#	1: KDFV (Originaldatensatz)
#	2: GWAP (pseudonymisierte Originaldaten, ggf. ohne Bayern)

# Arbeitsumgebung bestimmen (siehe oben)

FDZ=0


# Anmerkung zur Definition der Arbeitsumgebung: 
# Bitte ?ndern Sie die Namen der globals f?r die Zuweisung der Zielordner nicht. Ben?tigen Sie mehrere Zielordner
# f?r einen Ergebnistyp, benennen Sie diese bitte nach folgendem Schema: global outputpfad-1, global outputpfad-2, ...


#	Arbeitsumgebung 0: Pfadangaben f?r die Arbeit am eigenen Arbeitsplatz (z.B. Datenstrukturfile)
#	-------------------------------------------------------------------------------------------------------------------

if (FDZ==0)  {
  basispfad    <- "T:/Documents/Projects/04_jrc_green-skills-regional/03_data-analysis/re4gt/rcode"
  datenpfad    <- file.path(basispfad, "A_Mikrodaten") # hier liegt z.B. das Datenstrukturfile
  metadatenpfad<- file.path(basispfad, "B_Metadaten")
  syntaxpfad   <- file.path(basispfad, "C_Programme", "2022-06-23 KDFV Hlawatsch") # hier sollen Programme gespeichert werden
  outputpfad   <- file.path(basispfad, "D_Ergebnisse") # hier sollen alle Ergebnisse (inkl. log-file) gespeichert werden
  neudatenpfad <- file.path(basispfad, "D_Ergebnisse") # hier sollen neu erstellte Datens?tze gespeichert werden

  dateiname    <- "DSF_MZ 2019" # z.B. Name des Datenstrukturfiles einf?gen
  outputname   <- "Name der Logdatei einf?gen" # Name des log-files einf?gen
  syntaxname   <- "02_Deskriptive_Analysen_v2" # Name der Auswertungssyntax einf?gen, die aus dem Masterprogramm gestartet werden soll
  
  #.libPaths("<eigener Arbeitsplatz R-Pakete>") # hier werden die ben?tigten R-Pakete lokal abgespeichert
}

#	Arbeitsumgebung 1: Pfadangaben f?r die Arbeit ?ber die KDFV (Hinweis: die f?r Sie relevanten Pfade werden Ihnen in einer E-Mail bei Nutzungsbeginn mitgeteilt)
#	-------------------------------------------------------------------------------------------------------------------

if (FDZ==1) {
  datenpfad    <- "Q:/Projektxxxx/Daten" # hier liegen die Originaldaten	   
  syntaxpfad   <- "Q:/Projektxxxx/xxx" # hier sollen Programme gespeichert werden
  outputpfad   <- "Q:/Projektxxxx/xxx" # hier sollen alle Ergebnisse (inkl. log-file) gespeichert werden
  neudatenpfad <- "Q:/Projektxxxx/xxx" # hier sollen neu erstellte Datens?tze gespeichert werden
  
  dateiname    <- "Name des Datensatzes einf?gen" # Name des Originaldatensatzes einf?gen (siehe E-Mail)
  outputname   <- "Name der Logdatei einf?gen" # Name des log-files einf?gen
  syntaxname   <- "Name der Auswertungssyntax einf?gen" # Name der Auswertungssyntax einf?gen, die aus dem Masterprogramm gestartet werden soll
  
  .libPaths("Q:/stata/ado") # hier werden die R-Pakete abgelegt
}

#	Arbeitsumgebung 2: Pfadangaben f?r die Arbeit am GWAP(_formal)
#	-------------------------------------------------------------------------------------------------------------------

if (FDZ==2) {
  basispfad    <- file.path("Z:","gast", "SMS", "GWA92_4561_FZ")
  datenpfad    <- file.path(basispfad, "A_Mikrodaten") # hier liegen die Originaldaten
  metadatenpfad<- file.path(basispfad, "B_Metadaten", "2022-06-21")
  syntaxpfad   <- file.path(basispfad, "C_Programme", "2022-06-21") # hier sollen Programme gespeichert werden
  outputpfad   <- file.path(basispfad, "D_Ergebnisse", "2022-06-21") # hier sollen alle Ergebnisse (inkl. log-file) gespeichert werden
  neudatenpfad <- file.path(basispfad, "D_Ergebnisse", "2022-06-21") # hier sollen neu erstellte Datens?tze gespeichert werden
  
  dateiname    <- "MZ 2019 (mit Labels BY_Pseudo)" # Name des Originaldatensatzes einf?gen (siehe E-Mail)
  outputname   <- "results" # Name des log-files einf?gen
  syntaxname   <- "02_Deskriptive_Analysen" # Name der Auswertungssyntax einf?gen, die aus dem Masterprogramm gestartet werden soll
  
  .libPaths    <- file.path(basispfad,"R-Packages") # hier werden die R-Pakete abgelegt
}


# -------------------------------------------------------------------------------------------------------------------###
# Aufrufen der Auswertungssyntax und Aufzeichnung im Protokoll starten
#	-------------------------------------------------------------------------------------------------------------------
logdatei <- "results"
sink(paste(outputpfad, "/", logdatei, ".log", sep=""), type = c("output", "message"), split = TRUE)

source(paste(syntaxpfad, "/", syntaxname, ".R", sep=""), echo = TRUE, max.deparse.length = 99999)

sink()

#	-------------------------------------------------------------------------------------------------------------------
#	H I N W E I S:

# Die vorliegende Mustersyntax stellt ein Beispiel f?r eine Erstsyntax dar. Wenn in den folgenden Syntaxen 
# Auswertungen gemacht werden, die einen inhaltlichen Bezug zu bereits erstellten Ergebnissen haben, sind die 
# Bez?ge zu den entsprechenden vorherigen Syntaxen sowohl bei der Datenaufbereitung als auch bei der Auswertung in 
# einem Kommentar kenntlich zu machen.
#	-------------------------------------------------------------------------------------------------------------------
