# Entwicklungsablauf

opr2 ist ein unabhängiger C++20/CMake-Neuaufbau für Windows und Linux. Der
aktuelle Bootstrap ist nicht spielbar. Diese Anleitung beschreibt den gesamten
Beitragsablauf, nicht eine fertige Spielversion.

Der [Rekonstruktionsworkflow](reconstruction-workflow.md) ergänzt diese Regeln
um Stufen, Sol-/Luna-Rollen, begrenzte Pakete und private Übergaben. GitHub Issues
sind die maßgebliche Paketdokumentation. Queue, Resume, Familienfreigaben und
automatischer Spezialrollendispatch werden erst in den dort verlinkten
Implementierungsissues ergänzt. Diese Anleitung erfindet keine neuen
Runner-Befehle.

## Issue-Vertrag

Jede Arbeit beginnt mit einem GitHub Issue, das einen abgegrenzten Umfang und
konkrete Abnahmekriterien enthält. Lege im Issue einen JSON-Block mit genau
diesem Vertrag an:

```json
{
  "version": 1,
  "complexity": "small",
  "allowed_paths": ["src/example.cpp", "tests/example/"],
  "dependencies": [],
  "requires_original_data": false,
  "acceptance": ["The example behavior is documented and validated."]
}
```

`version` ist die Version des Task-Schemas und derzeit `1`; sie ändert sich
nicht bei normalen Änderungen an einer Aufgabe. `complexity` ist `small` oder
`large`. Nur `small`-Aufgaben können automatisiert verarbeitet werden. Zerlege
große oder mehrdeutige Aufgaben in begrenzte, eigenständig prüfbare Issues,
bevor sie für den Agenten freigegeben werden.
`allowed_paths` nennt Repository-relative Pfade, die der Worker bearbeiten
darf; Änderungen außerhalb davon blockieren die Integration. `dependencies`
ist eine Liste abhängiger Issue-Nummern. `requires_original_data` ist ein
Boolean und kennzeichnet, ob lokale Originaldaten-Nachweise notwendig sind.
`acceptance` enthält nichtleere, prüfbare Abnahmesätze. Änderungen am Auftrag
brauchen eine ausdrücklich dokumentierte Auftragsrevision und neue Freigabe;
Review und Validierung des alten Auftrags gelten danach nicht als Nachweis.
Die Schemafassung `version: 1` bleibt bestehen, solange das Schema unverändert
ist. Routing-Metadaten stehen außerhalb des JSON; sie erweitern keine Rechte
und werden vom bisherigen Runner noch nicht ausgewertet.

## Planen und Ausführen

Die lokale Orchestrierung ist der maßgebliche Ablauf. `plan` prüft den
Issue-Vertrag und geschlossene Abhängigkeiten. Vor `run` muss ein Maintainer
das genehmigte Issue mit `agent:ready` markieren. Wenn `pr2/` existiert, muss
vor `run` das unveränderte lokale Referenzmanifest vorhanden sein, auch wenn
das Issue keine Originaldaten benötigt:

```text
python tools/reference_manifest.py create --root pr2 --output analysis/reference-manifest.json
```

Bei Abweichungen die Ursache untersuchen. Das Manifest niemals neu erstellen
oder ersetzen, um Änderungen zu verbergen.

Zuerst den Plan lesen:

```text
python tools/orchestrator.py plan --issue 6 --config local/orchestrator.json
```

Danach ausführen:

```text
python tools/orchestrator.py run --issue 6 --config local/orchestrator.json
```

Worker und Reviewer lassen sich unabhängig konfigurieren:

```text
python tools/orchestrator.py run --issue 6 --config local/orchestrator.json --provider claude --model sonnet --review-provider codex --review-model gpt-6-luna
```

Der Worker aendert die freigegebenen Dateien und gibt seinen Diff zurueck. Der
Orchestrator prüft Umfang und Guards, erstellt lokal einen Commit mit der
Nachricht `#6 Implement bounded issue task` und laesst genau diesen Commit
unabhängig reviewen. Erst nach Review-Freigabe werden geänderter Code und
Tests ausgeführt. Bei erfolgreicher lokaler Validierung werden der Commit
gepusht und ein Pull Request erstellt. Review vor Ausführung des geänderten
Codes ist ein bewusstes Sicherheitsgate.

Vor automatischer Verarbeitung und nochmals vor Merge prüft der Orchestrator
die Branch-Protection-Einstellungen auf dem GitHub-Server. Für `main` müssen
required status checks aktiviert sein, `strict` muss `true` sein und
`validation-required` muss zu den erforderlichen Checks gehören. Der Bootstrap
richtet diese Schutzregel ein. Fehlt sie oder ist sie verändert, findet kein
Automerge statt. Der PR muss weiterhin auf genau den zuvor gelesenen
`baseRefOid` zeigen; bewegt sich `main`, blockiert der Lauf, bis gegen den
neuen Stand erneut geprüft und validiert wurde.

`--no-merge` laesst den Pull Request nach lokalen Gates offen und überspringt
die automatische Branch-Protection-/Merge-Prüfung. Ein Resume-Befehl wird
aktuell nicht unterstuetzt. Automerge verlangt unabhängiges Review, erfolgreiche
lokale Validierung einschliesslich Tests, erforderliche Originaldaten-Nachweise,
grüne CI und unveränderte Head- und Base-Commits. Der aktuelle Windows-Build
mit statischer MSVC-Laufzeit besteht die lokalen C++-Tests. Blockiert Windows
AppControl einen künftigen Build, diese Schutzrichtlinie niemals umgehen;
ohne erfolgreiche lokale Tests kein Automerge. CI ersetzt den lokalen Nachweis nicht.

## Rollen und Grenzen

Der Orchestrator besitzt Worktree-, Git-, Issue-, PR- und Merge-Aktionen. Ein
Worker soll ausschließlich seine freigegebenen Pfade bearbeiten; der Orchestrator
prüft den sichtbaren Diff gegen diese Liste. Provider-CLI-Prozesse laufen nicht
in einer harten Betriebssystem-Sandbox. Ignorierte Dateien und Schreibzugriffe
außerhalb des Worktrees können außerhalb dieser Prüfung liegen. Worker dürfen
nicht delegieren, committen, pushen, mergen, Issue-Zustände ändern oder
Originalprogramme starten. Der Reviewer ist eine andere Rolle und prüft den
aktuellen Commit unabhängig.

Provider und Modell sind Konfiguration. Codex und Claude Code folgen demselben
Auftragsvertrag; einfache Codex-Aufgaben verwenden standardmäßig GPT-6 Luna.
Die ausdrücklich erlaubte native Codex-Koordinatorrolle verwendet GPT-6 Sol
mit geringem Reasoning-Aufwand und delegiert begrenzte Fachaufgaben an Luna.
Native `.codex/`- und `.claude/`-Adapterdateien können ergänzende
Komfortfunktionen bereitstellen, sind aber keine alternative Autorität für
Policies.

## Originaldaten und Analyse

`pr2/` enthält die frische GOG-Port-Royale-2-Installation. Niemals darin
schreiben, patchen, löschen, umbenennen oder Programme daraus ausführen. Die
Originalinstallation wird nur zum Lesen und für den Manifest-/Hashvergleich
verwendet. Ein Worker darf Referenzdaten nur lesend untersuchen.

Wenn ein Issue den Datencheck verlangt, kopiert die lokale Validierung die
benötigten Daten in ein dediziertes, temporäres Verzeichnis unter dem
jeweiligen Lauf in `analysis/`. Das projektgebaute Programm wird ausschließlich
gegen diese Wegwerfkopie ausgeführt; die Originalinstallation bleibt
unberuehrt und wird davor und danach mit dem Ausgangsmanifest verglichen. Keine
Projektprogramme gegen `pr2/` ausführen.

REA/Ghidra-Rohdaten, extrahierte Daten, Screenshots, Referenzmanifeste,
Provider-Transkripte, lokale Validierungsergebnisse und temporaere Kopien
gehören ausschließlich unter das ignorierte `analysis/` im Repository-Root.
Der Provider-Prompt enthält den absoluten Pfad zum privaten Analyseordner des
konkreten Laufs. Diese Inhalte nie in Commits, Issues, Pull Requests,
Actions-Protokollen oder Artefakten ablegen. Veröffentlicht werden duerfen nur
knapp formulierte, eigenständig geschriebene Erkenntnisse ohne private Rohdaten.

Git darf keine Original-Binaries, DLLs, Assets, Skripte, Fonts, Handbücher,
Spielstaende oder extrahierten bzw. konvertierten Kopien enthalten. `.gitignore`
allein ist keine Sicherheitsgrenze. Tests verwenden eigens für Tests
geschriebene synthetische Daten.

## Lieferung und Reifegrad

Pakete enthalten ausschließlich Projekt-Builds und unsere Anweisungen. Nutzer
fügen erforderliche Originaldaten später neben der ausführbaren Datei selbst
hinzu. Kein Original-DLL darf für die fertige Linux- oder Windows-Implementierung
erforderlich sein. Engine- und Asset-Unterstützung sind Roadmap, keine
behauptete Fertigstellung oder Parität. Eine Projektlizenz ist noch nicht
gewählt.
