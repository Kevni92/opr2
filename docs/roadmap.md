# Weg zur Reimplementierung

Ziel ist funktionale Gleichheit in überprüften Spielszenarien auf Windows und
Linux. Der aktuelle Stand liefert die Entwicklungsgrundlage und einen lesenden
Signaturcheck, noch kein spielbares Spiel oder vollständigen CPR-Leser.

Die gemeinsame Pipeline und Rollengrenzen stehen im
[Rekonstruktionsworkflow](reconstruction-workflow.md). Konkrete Aufgaben,
Abnahmekriterien und Abhängigkeiten werden ausschließlich in GitHub Issues
gepflegt. Der Einstieg ist
[Workflow-Einrichtung #22](https://github.com/Kevni92/opr2/issues/22).

| Bereich | GitHub-Arbeitspakete |
|---|---|
| Vorhandene Basis | [Infrastruktur #1](https://github.com/Kevni92/opr2/issues/1), [REA #7](https://github.com/Kevni92/opr2/issues/7), [Zielanalyse #8](https://github.com/Kevni92/opr2/issues/8) |
| Dispatch und Queue | [Routing #23](https://github.com/Kevni92/opr2/issues/23), [Spezialrollen #24](https://github.com/Kevni92/opr2/issues/24), [Queue #25](https://github.com/Kevni92/opr2/issues/25) |
| Wiederaufnahme und Freigabe | [Checkpoints #26](https://github.com/Kevni92/opr2/issues/26), [Resume #27](https://github.com/Kevni92/opr2/issues/27), [Grants #28](https://github.com/Kevni92/opr2/issues/28), [Kind-Issues #29](https://github.com/Kevni92/opr2/issues/29), [Familienlauf #42](https://github.com/Kevni92/opr2/issues/42) |
| Analysewerkzeuge | [Katalog #30](https://github.com/Kevni92/opr2/issues/30), [Export #31](https://github.com/Kevni92/opr2/issues/31), [Paketzuordnung #32](https://github.com/Kevni92/opr2/issues/32), [Abdeckung #33](https://github.com/Kevni92/opr2/issues/33) |
| Synthetischer Workflow-Nachweis | [Zwei-Issue-Strecke #34](https://github.com/Kevni92/opr2/issues/34) |
| Erste begrenzte Originalläufe | [Inventarseite #35](https://github.com/Kevni92/opr2/issues/35), [16 Funktionen #36](https://github.com/Kevni92/opr2/issues/36) |
| Gesamten erkannten Bestand paketieren | [Inventar-/Decompilationsfamilie #43](https://github.com/Kevni92/opr2/issues/43) |
| Ressourcen als erste fachliche Strecke | [Epic #9](https://github.com/Kevni92/opr2/issues/9), Analyse-/Vertragspakete [#37](https://github.com/Kevni92/opr2/issues/37), [#38](https://github.com/Kevni92/opr2/issues/38), [#39](https://github.com/Kevni92/opr2/issues/39), [#40](https://github.com/Kevni92/opr2/issues/40), [Implementierungsplanung #41](https://github.com/Kevni92/opr2/issues/41) |
| Weitere Spielsysteme | [Spielbare Strecke #10](https://github.com/Kevni92/opr2/issues/10), [Szenarionachweise #11](https://github.com/Kevni92/opr2/issues/11) |

Die neuen Folgeissues sind zunächst nicht zur Ausführung freigegeben.
Implementierungspakete für noch unbekannte Spielsysteme entstehen erst aus
ausreichend belegten Verträgen; dabei werden dieselben Vorlagen und Luna-Rollen
verwendet. Fehlende Befunde, Fehler oder erschöpfte Budgets werden als offen oder
blockiert ausgewiesen und niemals in behauptete Parität umgedeutet.
