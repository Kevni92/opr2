# Weg zur Reimplementierung

Ziel ist funktionale Gleichheit in überprüften Spielszenarien auf Windows und
Linux. Der aktuelle Stand liefert die Entwicklungsgrundlage und einen lesenden
Signaturcheck, noch kein spielbares Spiel oder vollständigen CPR-Leser.

1. [Infrastruktur und gemeinsame Regeln](https://github.com/Kevni92/opr2/issues/1):
   portable Builds, lokale Orchestrierung, unabhängige Prüfung und Dateischutz.
2. [Kleine erste Implementierungsaufgabe](https://github.com/Kevni92/opr2/issues/6):
   CLI-Version und Exitcodes über den vollständigen Ablauf prüfen.
3. [REA-Anbindung](https://github.com/Kevni92/opr2/issues/7) und
   [frische statische Analyse](https://github.com/Kevni92/opr2/issues/8):
   Zielidentität, Subsystemgrenzen und Unsicherheiten belegen.
4. [Ressourcenformate](https://github.com/Kevni92/opr2/issues/9):
   bestätigte Spezifikationen und kleine Reader-Aufgaben mit synthetischen Tests.
5. [Erste spielbare Strecke](https://github.com/Kevni92/opr2/issues/10):
   Ressourcen, Oberfläche und Simulation in klar abgegrenzte Aufgaben zerlegen.
6. [Verhaltensparität](https://github.com/Kevni92/opr2/issues/11):
   reproduzierbare Szenarien und private Referenzen vergleichen. Neue Spielsysteme
   folgen auf der bestätigten Grundlage.

Große Untersuchungen werden vom Orchestrator zuerst in prüfbare Fragen zerlegt.
Kleine Agents erhalten jeweils einen konkreten Vertrag und dürfen Unsicherheit
als Blockade melden. Fehlende Befunde gelten nicht als erfolgreiche Validierung.
