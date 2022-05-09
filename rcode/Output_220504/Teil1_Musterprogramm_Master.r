#	-------------------------------M U S T E R P R O G R A M M   R ---------------------------------------------------

# Hinweis: Das Musterprogramm dient Ihnen zur Orientierung bei der Erstellung Ihres Programmcodes.            	
# Das Ziel ist, Ihre Outputfiles bestmöglich für die Geheimhaltungsprüfung aufzubereiten.                     	
# Bitte beachten Sie: Dieses Musterprogramm enthält keine statistikspezifischen Hilfestellungen zur           	
# Aufbereitung und Auswertung der von Ihnen beantragten Daten.                                                	

# Vorab einige grundlegende Punkte zur Arbeit mit R im FDZ-Kontext:

# - Bitte löschen Sie nicht mehr benötigte Temp- und/oder Arbeitsdateien am Ende Ihres Programmes.					

# - Bitte legen Sie analog zum Musterprogramm eine Masterdatei an (Teil 1 des Musterprogramms) und 
#   erstellen Sie separate Dateien für Ihre Auswertungssyntaxen (Teil 2 des Musterprogramms).
#   
# - Bitte definieren Sie in der Masterdatei Ihre Arbeitsumgebung (z.B. GWAP oder KDFV) und führen 
#   Sie Ihre (ggf. unterschiedlichen) Datensätze ein.	

# - Bitte berücksichtigen Sie bei all Ihren Auswertungen die "Basisanforderungen an die Syntax" sowie die
#   "Kriterien zur Zulassung von Output", die Sie in unserer Broschüre finden!

# Bitte beachten Sie auch, dass der online-Abruf von R-Paketen über die FDZ nicht möglich ist. Wenn Sie
# R-Pakete nutzen möchten, stellen Sie uns diese bitte als lokal abzuspeichernde Datei bereit. R-Pakete
# werden nur nach vorheriger Prüfung zugelassen.

#	-------------------------------------------------------------------------------------------------------------------
# ----
#	----	Grundeinstellungen
#	----
#	-------------------------------------------------------------------------------------------------------------------

# Speicher leeren

rm(list=ls()) 

# ggf. weiterführende Grundeinstellungen 



#	-------------------------------------------------------------------------------------------------------------------
#	----
#	----	Block I: Arbeitsumgebung definieren
# ----
#	-------------------------------------------------------------------------------------------------------------------

# Im FDZ unterscheiden wir grundsätzlich drei Arbeitsumgebungen: 
# 0. eigene Arbeitsumgebung im Büro/zu Hause
# 1. kontrollierte Datenfernverarbeitung (KDFV)
# 2. Gastwissenschaftsarbeitsplatz (GWAP)

# Es gibt FDZ-Projekte, die ausschließlich in einer Arbeitsumgebung laufen, z.B. reine GWAP-Projekte.
# Es gibt jedoch auch FDZ-Projekte, die in mehreren Arbeitsumgebungen laufen. So können z.B. ausgewählte Datensätze nicht 
# im kompletten Umfang an den GWAP gestellt werden (Wirtschaftsdaten, Steuerdaten). Nutzende haben am GWAP lediglich 
# eingeschränkten Zugang auf die Daten, können aber Auswertungsprogramme am GWAP erstellen. Diese werden dann von 
# FDZ-Mitarbeiter/-innen über die KDFV auf den Originaldaten laufen gelassen. Dazu ist eine Anpassung der Pfadangaben 
# notwendig.

# Um diese Grundeinstellungen übersichtlich vorzunehmen, bitten wir Sie, Ihre Arbeitsumgebungen zu definieren und die
# entsprechenden Pfade anzulegen. 

# Bitte unterscheiden Sie zwischen den folgenden drei Arbeitsumgebungen und passen Sie für alle relevanten
# Arbeitsumgebungen die Pfade an. 
# Bitte löschen Sie nicht benötigte Pfade und ergänzen fehlende.

#	0: eigener Arbeitsplatz (z.B. Datenstrukturfile)
#	1: KDFV (Originaldatensatz)
#	2: GWAP (pseudonymisierte Originaldaten, ggf. ohne Bayern)

# Arbeitsumgebung bestimmen (siehe oben)

FDZ=1 


# Anmerkung zur Definition der Arbeitsumgebung: 
# Bitte ändern Sie die Namen der globals für die Zuweisung der Zielordner nicht. Benötigen Sie mehrere Zielordner
# für einen Ergebnistyp, benennen Sie diese bitte nach folgendem Schema: global outputpfad-1, global outputpfad-2, ...


#	Arbeitsumgebung 0: Pfadangaben für die Arbeit am eigenen Arbeitsplatz (z.B. Datenstrukturfile)
#	-------------------------------------------------------------------------------------------------------------------

if (FDZ==0)  {
  datenpfad    <- "<eigener Arbeitsplatz Daten>" # hier liegt z.B. das Datenstrukturfile
  syntaxpfad   <- "<eigener Arbeitsplatz Programm>" # hier sollen Programme gespeichert werden
  outputpfad   <- "<eigener Arbeitsplatz Ergebnisse>" # hier sollen alle Ergebnisse (inkl. log-file) gespeichert werden
  neudatenpfad <- "<eigener Arbeitsplatz Arbeitsdateien>" # hier sollen neu erstellte Datensätze gespeichert werden

  dateiname    <- "Name des Datensatzes einfügen" # z.B. Name des Datenstrukturfiles einfügen
  outputname   <- "Name der Logdatei einfügen" # Name des log-files einfügen
  syntaxname   <- "Name der Auswertungssyntax einfügen" # Name der Auswertungssyntax einfügen, die aus dem Masterprogramm gestartet werden soll
  
  .libPaths("<eigener Arbeitsplatz R-Pakete>") # hier werden die benötigten R-Pakete lokal abgespeichert
}

#	Arbeitsumgebung 1: Pfadangaben für die Arbeit über die KDFV (Hinweis: die für Sie relevanten Pfade werden Ihnen in einer E-Mail bei Nutzungsbeginn mitgeteilt)
#	-------------------------------------------------------------------------------------------------------------------

if (FDZ==1) {
  datenpfad    <- "Q:/Projektxxxx/Daten" # hier liegen die Originaldaten	   
  syntaxpfad   <- "Q:/Projektxxxx/xxx" # hier sollen Programme gespeichert werden
  outputpfad   <- "Q:/Projektxxxx/xxx" # hier sollen alle Ergebnisse (inkl. log-file) gespeichert werden
  neudatenpfad <- "Q:/Projektxxxx/xxx" # hier sollen neu erstellte Datensätze gespeichert werden
  
  dateiname    <- "Name des Datensatzes einfügen" # Name des Originaldatensatzes einfügen (siehe E-Mail)
  outputname   <- "Name der Logdatei einfügen" # Name des log-files einfügen
  syntaxname   <- "Name der Auswertungssyntax einfügen" # Name der Auswertungssyntax einfügen, die aus dem Masterprogramm gestartet werden soll
  
  .libPaths("Q:/stata/ado") # hier werden die R-Pakete abgelegt
}

#	Arbeitsumgebung 2: Pfadangaben für die Arbeit am GWAP(_formal)
#	-------------------------------------------------------------------------------------------------------------------

if (FDZ==2) {
  datenpfad    <- "R:/Projektxxxx/Daten" # hier liegen die Originaldaten
  syntaxpfad   <- "R:/Projektxxxx/xxx" # hier sollen Programme gespeichert werden
  outputpfad   <- "R:/Projektxxxx/xxx" # hier sollen alle Ergebnisse (inkl. log-file) gespeichert werden
  neudatenpfad <- "R:/Projektxxxx/xxx" # hier sollen neu erstellte Datensätze gespeichert werden
  
  dateiname    <- "Name des Datensatzes einfügen" # Name des Originaldatensatzes einfügen (siehe E-Mail)
  outputname   <- "Name der Logdatei einfügen" # Name des log-files einfügen
  syntaxname   <- "Name der Auswertungssyntax einfügen" # Name der Auswertungssyntax einfügen, die aus dem Masterprogramm gestartet werden soll
  
  .libPaths("R:/stata/ado") # hier werden die R-Pakete abgelegt
}


# -------------------------------------------------------------------------------------------------------------------###
# Aufrufen der Auswertungssyntax und Aufzeichnung im Protokoll starten
#	-------------------------------------------------------------------------------------------------------------------

sink(paste(outputpfad, "/", logdatei, ".log", sep=""), type = c("output", "message"), split = TRUE)

source(paste(syntaxpfad, "/", syntaxname, ".R", sep=""), echo = TRUE, max.deparse.length = 99999)

sink()

#	-------------------------------------------------------------------------------------------------------------------
#	H I N W E I S:

# Die vorliegende Mustersyntax stellt ein Beispiel für eine Erstsyntax dar. Wenn in den folgenden Syntaxen 
# Auswertungen gemacht werden, die einen inhaltlichen Bezug zu bereits erstellten Ergebnissen haben, sind die 
# Bezüge zu den entsprechenden vorherigen Syntaxen sowohl bei der Datenaufbereitung als auch bei der Auswertung in 
# einem Kommentar kenntlich zu machen.
#	-------------------------------------------------------------------------------------------------------------------
