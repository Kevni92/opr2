# opr2

opr2 ist der unabhängige Neuaufbau eines modernen Handelsspiels in C++20 und
CMake für Windows und Linux. Das Repository enthält derzeit nur einen
Entwicklungs-Bootstrap; es ist noch kein spielbarer Ersatz und belegt keine
vollständige Funktionsparität mit Port Royale 2.

## Mitmachen

Die Entwicklung läuft über GitHub Issues mit begrenztem Umfang und überprüfbaren
Abnahmekriterien. Lies zuerst [docs/workflow.md](docs/workflow.md) und
[docs/validation.md](docs/validation.md). Die Regeln für alle Mitwirkenden
stehen in [AGENTS.md](AGENTS.md).

Die lokale Orchestrierung ist der maßgebliche Ablauf. Sie kann Codex, Claude
Code oder einen anderen Adapter verwenden; Anbieter und Modell sind
Konfiguration. Native `.codex/`- und `.claude/`-Dateien sind optionale
Einstiegspunkte. Die [Teilnahmeanleitung](CONTRIBUTING.md) erklärt die Einrichtung.
Analysen verwenden [REA MCP mit Ghidra](docs/rea-workflow.md).
Die nächsten Schritte stehen in der [Roadmap](docs/roadmap.md).

Der [Rekonstruktionsworkflow](docs/reconstruction-workflow.md) definiert
begrenzte Pakete vom Funktionsinventar bis zum geprüften C++20-Vertrag.
GPT-6 Sol koordiniert; spezialisierte GPT-6-Luna-Agenten bearbeiten und prüfen
die Pakete. Die konkreten Aufträge stehen in
[GitHub Issue #22 und seinen Folgeissues](https://github.com/Kevni92/opr2/issues/22).
Die bestehende Automation verarbeitet einzelne Issues. Queue, Wiederaufnahme
und automatischer Rollendispatch sind spezifizierte Luna-Folgeaufgaben.

## Originaldaten

Die frische GOG-Installation von Port Royale 2 liegt im Repository unter
`pr2/`. Sie ist nur eine lokale Referenz: niemals Dateien darin ändern,
umbenennen, löschen oder Programme daraus starten. Rohdaten, Screenshots,
Manifeste, Anbieter-Transkripte und lokale Validierungsergebnisse gehören nach
`analysis/`; diese Inhalte dürfen nicht in Commits, Issues, Pull Requests,
Actions-Protokollen oder Artefakten erscheinen.

Laufzeitpakete enthalten nur von diesem Projekt gebaute Dateien und unsere
Anweisungen. Nutzer stellen erforderliche Original-Spieldaten später selbst
neben die ausführbare Datei. Engine- und Asset-Unterstützung sind Arbeitsplan,
keine bereits abgeschlossene Funktion. Eine Projektlizenz wurde noch nicht
gewählt.
