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

setwd("<hier werden die R-Pakete abgelegt>")
install.packages(pkgs=c("miceadds", "car", "Hmisc", "foreign", "pastecs", "tidyverse", "questionr", "knitr", "+ Zip-Ordner aller Dependencies"), type = "source", repos = NULL)


# KDFV-Nutzung: 

install.packages(pkgs=c("miceadds", "car", "Hmisc", "foreign", "pastecs", "tidyverse", "questionr", "knitr" ,"Bitte weitere gewünschte Packages angeben"), dependencies=TRUE)

# Zu verwendende Packages laden

library(miceadds)
library(car)
library(Hmisc)
library(pastecs)
library(foreign)
library(tidyverse)
library(questionr)
library(knitr)


# -------------------------------------------------------------------------------------------------------------------
#	1. Datenaufbereitung
#	-------------------------------------------------------------------------------------------------------------------


#	a.  Datensatz einlesen
#	    Speicher- und laufzeiteffizient die Auswahl der benötigten Variablen und Fälle direkt vornehmen.

#	    Bevölkerung in Privathaushalten (EF31 = 1) am Ort der Hauptwohnung (EF30 < 3)

Daten <- subset(load.Rdata2(paste(dateiname, ".Rdata", sep=""), path=datenpfad), EF31 == 1 & EF30 < 3, select=c(EF1:EF5,EF25,EF30,EF31,EF44,EF46,EF49,EF310,EF952))

# Alternative mit Pipes

Daten <- load.Rdata2(paste0(dateiname, ".Rda"), path = datenpfad) %>%
  select(EF1:EF5,EF25,EF30,EF31,EF44,EF46,EF49,EF310,EF952) %>%
  filter(EF31 == 1 & EF30 < 3)

# Alternativ können auch CSV-Dateien eingeladen werden und nicht benötigte Variablen können separat gelöscht werden:

Daten <- read.csv(file.path(datenpfad, paste(dateiname,  ".csv",  sep="")), header = T, sep=";")
Daten <- subset(Daten, select= -c(EF2:EF4, EF6:EF20))

# temporären Arbeitsdatensatz erstellen

save(Daten, file=paste0(neudatenpfad,"Temp1.rdata")) 
# Dieser Datensatz wird nach der Analyse nicht mehr benötigt und kann am Ende gelöscht werden.
# Besser als löschen: Temporäre Arbeitsdatensätze gar nicht erst abspeichern


# b.  Generierung dichotome Variable verh, die angibt, ob Person verheiratet ist.  

Daten$verh <- 0
Daten$verh[Daten$EF49==2] <- 1 

# Alternative mit Pipes

Daten <- Daten %>%
  mutate(verh2 = ifelse(EF49 == 2, 1, 0))


# c.  Generierung Haushalts- und Familiennummer aus EF1, EF2, EF3, EF4, EF5, EF25
#     persnr: EF1 bis EF5
#     hh: EF1 bis EF4
#	    famnr: EF1 bis EF4 + EF25

Daten$persnr <- as.numeric(Daten$EF1)*10000000000 + as.numeric(Daten$EF2)*1000000000 + as.numeric(Daten$EF3)*100000 + as.numeric(Daten$EF4)*1000 + as.numeric(Daten$EF5)*10
Daten$hhnr <- as.numeric(Daten$EF1)*10000000000 + as.numeric(Daten$EF2)*1000000000 + as.numeric(Daten$EF3)*100000 + as.numeric(Daten$EF4)*1000 + 1
Daten$famnr <- as.numeric(Daten$EF1)*10000000000 + as.numeric(Daten$EF2)*1000000000 + as.numeric(Daten$EF3)*100000 + as.numeric(Daten$EF4)*1000 + as.numeric(Daten$EF25)*1

# Alternative mit Pipes

Daten <- Daten %>%
  mutate(persnr = as.numeric(Daten$EF1)*10000000000 + as.numeric(Daten$EF2)*1000000000 + as.numeric(Daten$EF3)*100000 + as.numeric(Daten$EF4)*1000 + as.numeric(Daten$EF5)*10,
         hhnr = as.numeric(Daten$EF1)*10000000000 + as.numeric(Daten$EF2)*1000000000 + as.numeric(Daten$EF3)*100000 + as.numeric(Daten$EF4)*1000 + 1,
         as.numeric(Daten$EF1)*10000000000 + as.numeric(Daten$EF2)*1000000000 + as.numeric(Daten$EF3)*100000 + as.numeric(Daten$EF4)*1000 + as.numeric(Daten$EF25)*1)


# d.  Vorbereitung Test: Haushaltsnummer ungleich Familiennummer
#     Wenn: Familiennummer (famnr) ungleich der Haushaltsnummer (hhnr), dann: Differenz Haushaltsnummer - Familiennummer (nrdiff) gleich 1

Daten$nrdiff <- 0
Daten$nrdiff[Daten$famnr!= Daten$hhnr] <- 1

# Alternative mit Pipes

Daten <- Daten %>%
  mutate(nrdiff = ifelse(Daten$famnr!= Daten$hhnr, 1, 0))


# e.  Vorbereitung Test: mehrfache Personennummer
#     Personennummer (persnr) gleich der des Vorgängers dann Personennummertest (piddiff) gleich 1 

Daten <- Daten[order(Daten$persnr),]
Daten$piddiff <- 0
Daten$piddiff[Daten$persnr == lag(Daten$persnr,1)] <- 1

# Alternative mit Pipes

Daten <- Daten %>%
  arrange(persnr) %>%
  mutate(piddiff = case_when(Daten$persnr == lag(Daten$persnr,1) ~ 1, Daten$persnr != lag(Daten$persnr,1) ~ 0, NA ~ 0)) # erste Observation NA


# f. Beschriftung der Variablen und Werte (Hierfür kann der Befehl label aus dem Hmisc Package genutzt werden.)

label(Daten$verh) <- "Verheiratet"

label(Daten$hhnr) <- "Haushaltsnummer"
label (Daten$famnr) <- "Familiennummer"
label(Daten$persnr) <-	"Personennummer"

label(Daten$piddiff) <- "Test einmalige Personennummer"
label(Daten$nrdiff) <- "Differenz Haushaltsnummer - Familiennummer"

levels(Daten$verh)[1] <- "ja" 
levels(Daten$verh)[0] <- "nein"

levels(Daten$nrdiff)[1] <- "Haushaltsnummer und Familiennummer unterschiedlich"
levels(Daten$nrdiff)[0] <- "Haushaltsnummer und Familiennummer gleich"

levels(Daten$piddiff)[1] <- "Personennummer mehrfach"
levels(Daten$piddiff)[0] <- "Personennummer einfach"


# g. Erstellen eines neuen Datensatzes mit Filterung nach verh = 1

Daten_verh <- Daten[which(Daten$verh==1),]
# oder:
Daten_verh <- subset(Daten, Daten$verh==1)
# oder:
Daten_verh <- Daten %>%
  filter(verh == 1)


# h. Erstellen eines temporären Arbeitsdatensatzes mit Filterung nach verh = 1 (Bitte löschen sie diesen, sollte er nach der Analyse nicht mehr benötigt werden!)

# als CSV:
write.table(Daten, paste0(neudatenpfad,"Temp2.csv"), sep=";")
# oder im sparsameren R-Datenformat:
save(Daten, file=paste0(neudatenpfad,"Temp2.rdata"))


#	-------------------------------------------------------------------------------------------------------------------
# 2. Datenauswertung
# -------------------------------------------------------------------------------------------------------------------

# Für jedes erzeugte Ergebnis muss angegeben werden, ob es auf Geheimhaltung geprüft und freigegeben werden soll 
# oder ob es lediglich den Prüfprozessen der FDZ dient. Diese Angabe kann pauschal in einem Kommentar erfolgen, 
# beispielweise "Alle erzeugten Auswertungen werden benötigt." oder "Es werden ausschließlich gewichtete 
# Auswertungen benötigt.", solange die Formulierung eindeutig ist.

# Hinweis für das FDZ: die unter Punkt 2 erstellten Ergebnisse sollen nicht geprüft werden.


# Datenauswertung Gesamtdatensatz:

# Output Nr. 2.1: Haushaltsnummer ungleich Familiennummer

table(Daten$nrdiff)


# Output Nr. 2.2: Test mehrfache Personennummer

table(Daten$piddiff)


# Datenauswertung nach Variable verh mit dem Datensatz Daten_verh:

# Output Nr. 2.3: Haushaltsnummer ungleich Familiennummer
table(Daten_verh$nrdiff)


# Output Nr. 2.4: Test auf mehrfache Personennummer
table(Daten_verh$piddiff)


#	-------------------------------------------------------------------------------------------------------------------
#	3. gewichtete Auswertungen
#	-------------------------------------------------------------------------------------------------------------------

# Für die Geheimhaltungsprüfung ist es erforderlich, bei gewichteten Ausgaben zusätzlich auch 
# das ungewichtete Ergebnis mit ausgeben zu lassen (vgl. Broschüre 2.7 Ausgabe der zugrundeliegenden Fallzahlen
# und Kennzeichnung der Bezüge).


# Output Nr. 3.1: ungewichtete Häufigkeit des Bundeslandes

table(Daten$EF1)
# oder:
kable(table(Daten$EF1))


# Output Nr. 3.2: gewichtete Häufigkeit des Bundeslandes

wtd.table(Daten$EF1, weights=as.numeric(Daten$EF952))


# Output Nr. 3.3: ungewichtete Regression mit der abhängigen Variablen Alter (EF44) und 
# den beiden unabhängigen Variablen Geschlecht (EF46) und Verheiratet (verh)

summary(lm(Daten$EF44 ~ Daten$EF46 + Daten$verh, Daten))


# Output Nr. 3.4: gewichtete Regression mit der abhängigen Variablen Alter (EF44) und 
# den beiden unabhängigen Variablen Geschlecht (EF46) und Verheiratet (verh)

summary(lm(Daten$EF44 ~ Daten$EF46 + Daten$verh, Daten ,weights=(as.numeric(Daten$EF952))))                


#	-------------------------------------------------------------------------------------------------------------------
#	4. Auswertungen mit Filterbedingungen
#	-------------------------------------------------------------------------------------------------------------------

# Restgrößen, die sich als Differenz zu "Insgesamt" erschließen, sind zu vermeiden.
# Beispiel: Sie erzeugen eine "Insgesamt"-Tabelle und eine Tabelle "Männlich".
# Die Restgröße/Differenz ist "Weiblich" und muss mit ausgegeben werden (vgl. Broschüre 2.9 Ausweis von Differenzgruppen 
# und Kennzeichnung der Bezüge sowie 3.2.4 Analyse von Teilpopulationen).


# Output Nr. 4.1: Häufigkeit des höchsten allgemeinen Schulabschlusses nach gesamt

table(Daten$EF310)
# oder:
kable(table(Daten$EF310))


# Output Nr. 4.2: Häufigkeit des höchsten allgemeinen Schulabschlusses nach männlich

table(Daten$EF310[Daten$EF46 == 1])


# Output Nr. 4.3: Häufigkeit des höchsten allgemeinen Schulabschlusses nach weiblich

table(Daten$EF310[Daten$EF46 == 2]) 

# Hinweis: Alternativ kann für diese Art der Auswertung auch eine Kreuztabelle ohne vorherige Fallauswahl 
# verwendet werden. Durch die Verwendung einer Kreuztabelle werden Restgrößen direkt vermieden.


#	-------------------------------------------------------------------------------------------------------------------
#	5. Ausgabe deskriptiver Kennzahlen
#	-------------------------------------------------------------------------------------------------------------------

# Aus Geheimhaltungsgründen sind Minima und Maxima metrischer Variablen zu unterdrücken (vgl. Broschüre 3.2.1
# Ausgabe von Einzelwerten). 


# Output Nr. 5.1: Anzahl, Mittelwert und Standardabweichung des Alters aller ledigen Personen (EF49==1)

# 1. Variante: 

x <- Daten$EF44[Daten$EF49==1]
c(N=length(x),Mean=mean(x),Sd=sd(x))

# Alternative mit Pipes

table_ledig <- Daten %>%
  select(EF44, EF49) %>%
  filter(EF49 == 1) %>%
  group_by(EF49) %>%
  summarise(N = n(),
            Mean = mean(EF44),
            SD = sd(EF44))
kable(table_ledig)

# Restgruppe mit ausgeben!

x <- Daten$EF44[Daten$EF49!=1]
c(N=length(x),Mean=mean(x),Sd=sd(x))

# Alternative mit Pipes

table_nicht_ledig <- Daten %>%
  select(EF44, EF49) %>%
  filter(EF49 != 1) %>%
  group_by() %>%
  summarise(N = n(),
            Mean = mean(EF44),
            SD = sd(EF44))
kable(table_nicht_ledig)


# 2. Variante: Verwendung des by-Befehls, um die deskriptiven Ergebnisse aller Kategorien zu erhalten 
#	-------------------------------------------------------------------------------------------------------------------

by(Daten$EF44, Daten["EF49"], function(x){
  c(N=length(x), Mean=mean(x), SD=sd(x))
}) 

# Alternative mit Pipes

table_alter <- Daten %>%
  select(EF44, EF49) %>%
  group_by(EF49) %>%
  summarise(N = n(), 
            Mean = mean(EF44),
            SD = sd(EF44))
kable(table_alter)

# Hinweis: Bei wirtschaftsstatistischen Daten sind bei der Ausgabe von deskriptiven Kennzahlen für die 
# Geheimhaltungsprüfung das Maximum, der zweitgrößte Wert und die Gesamtsumme der Variablen 
# (z.B. Umsatz, Einkünfte) mit auszugeben (vgl. Broschüre 3.1.3 Dominanzregeln).

# Nicht benötigte Tabellen entfernen

rm(table_ledig)
rm(table_nicht_ledig)


#	-------------------------------------------------------------------------------------------------------------------
#	6. Auswertungen von Dummy-Variablen 
#	-------------------------------------------------------------------------------------------------------------------

# Zusätzlich zur Ausgabe Statistischer Maßzahlen ist die Häufigkeitstabelle auszugeben, da die Fallzahl der Merkmalsausprägung 
# für die Geheimhaltungsprüfung benötigt wird.


#	Output Nr. 6.1:  Anzahl, Mittelwert und Standardabweichung des Geschlechts aller über 65-Jährigen (EF44 > 65)

by(Daten$EF46, Daten["EF44"]>65, function(x){
  c(N=length(x),Mean=mean(x),SD=sd(x))
})

# Alternative mit Pipes

table_65 <- Daten %>%
  mutate(alter = case_when(EF44 <= 65 ~ 0, 
                           EF44 > 65 ~ 1)) %>%
  select(alter, EF46) %>%
  group_by(alter) %>%
  summarise(N = n(),
            Mean = mean(EF46), 
            SD = sd(EF46))
kable(table_65)


#	Output Nr. 6.2  Häufigkeitsauszählung des Geschlechts aller über 65-Jährigen (EF44 > 65)

table(Daten$EF46[Daten$EF44>65])

#	Hinweis für das FDZ: Nur für die Geheimhaltungsprüfung

table(Daten$EF46[Daten$EF44<=65])


#	-------------------------------------------------------------------------------------------------------------------
#	7. Ausgabe von Wertetabellen 
#	-------------------------------------------------------------------------------------------------------------------

# Bei der Erstellung von Wertetabellen ist stets die zugrundeliegende Fallzahl mit anzugeben.


# Erstellen einer benutzerdefinierten Tabelle mit dem Mittelwert des Alters (EF44) je Ausprägung Familienstand (EF49)

#	Output Nr. 7.1: Kreuztabelle Alter und Familienstand zur Angabe der gültigen Häufigkeit (N)

matrix(c(tapply(Daten$EF44, Daten$EF49, length), tapply(Daten$EF44, Daten$EF49, mean)), nrow=2, byrow=T,  dimnames=list (c("N", "Mean"), 1:7))

# Alternative mit Pipes (siehe Zeile 393)

kable(table_alter)


#	-------------------------------------------------------------------------------------------------------------------
#	----
#	----	Block III: Programmabschluss
#	----
#	-------------------------------------------------------------------------------------------------------------------

#	temporäre Dateien löschen

file.remove(paste0(neudatenpfad,"Temp1.rdata"))
file.remove(paste0(neudatenpfad,"Temp2.rdata"))
file.remove(paste0(neudatenpfad,"Temp2.csv"))

#	-------------------------------------------------------------------------------------------------------------------
#	H I N W E I S:

# Die vorliegende Mustersyntax stellt ein Beispiel für eine Erstsyntax dar. Wenn in den folgenden Syntaxen 
# Auswertungen gemacht werden, die einen inhaltlichen Bezug zu bereits erstellten Ergebnissen haben, sind die 
# Bezüge zu den entsprechenden vorherigen Syntaxen sowohl bei der Datenaufbereitung als auch bei der Auswertung in 
# einem Kommentar kenntlich zu machen.
#	-------------------------------------------------------------------------------------------------------------------