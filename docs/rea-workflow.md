# Analyse mit REA MCP und Ghidra

REA MCP ist eine ausdrücklich aktivierte lokale Analysefähigkeit. Codex und
Claude erhalten dieselbe stdio-Konfiguration; Ghidra liefert die native
statische Analyse. Eine begrenzte REA-Aufgabe kennzeichnet ihr Issue mit
`"capabilities": ["rea"]` und `"requires_original_data": true`. Normale
Implementierungsaufgaben starten keinen REA-Server.

Installiere die GOG-Version im Root-Ordner `pr2/`, erstelle einmalig das lokale
Integritätsmanifest und richte REA, Ghidra sowie ein passendes JDK ein. Kopiere
[rea-mcp.example.json](../automation/rea-mcp.example.json) nach
`local/rea.mcp.json` und passe `command`, `args`, `GHIDRA_INSTALL_DIR` und
`JAVA_HOME` an. Das Beispiel setzt `rea mcp` im PATH voraus; alternativ kann
`command` auf Node und `args` auf eine lokal installierte REA-CLI zeigen.
Rechnerpfade und Konfiguration bleiben in `local/`. Der Orchestrator akzeptiert
genau einen lokalen stdio-Server namens `rea`; Remote-Endpunkte sind gesperrt.

Vor der Analyse prüft der Orchestrator `pr2/PR2.exe` gegen das lokale Manifest
und übergibt Zielpfad, Identität und Analyseausgabepfad. Der Agent öffnet genau
dieses Ziel mit `provider_id=ghidra` und vergleicht die von REA gemeldete
Identität. Frühere Ghidra-Projekte oder Snapshots werden nicht übernommen.
Die Binärdatei wird weder ausgeführt noch als Datei in einen Prompt eingefügt.

Der Codex-Adapter lädt REA ausdrücklich mit einer Liste zulässiger statischer
Tools. Der Claude-Adapter nutzt `--strict-mcp-config` mit demselben Server und
einzelnen erlaubten MCP-Tools. Der unabhängige Reviewer erhält keinen Export-
oder Schreibauftrag. Weitere CLIs können den lokalen Kontext über den
Platzhalter `{rea_context}` beziehen; ihr Adapter muss dieselben Grenzen
umsetzen. Das ist keine Betriebssystem-Sandbox für den MCP-Server.

Der erste Ghidra-Import und die automatische Analyse koennen mehrere Minuten
dauern. Codex wartet für REA-MCP-Aufrufe bis zu 420 Sekunden. Das liegt über
der 330-Sekunden-Deadline des installierten REA-Ghidra-Providers. Für den
gesamten Agentenlauf gilt weiterhin das separate Provider-Zeitlimit. Ein
Aufruf, der trotzdem nicht rechtzeitig antwortet, wird als `blocked` erfasst;
starte denselben teuren Vollüberblick nicht ungeprüft erneut.

Die Liste in `tools/rea_workflow.py` erlaubt Zielöffnung, Metadaten, Funktionen,
Strings, Referenzen, Bytes und Funktionsanalyse. Evidenz kann lokal exportiert
werden. Runtime-Beobachtungen, Originalausführung, Annotationen,
Datenbankmutationen und Extraktion sind ausgeschlossen.

Alle behaltenen Rohbefunde, Ghidra-Ausgaben und Evidenzpakete gehören in das
absolute, im Auftrag genannte Verzeichnis unter Root `analysis/runs/`.
Öffentliche Erkenntnisse werden eigenständig formuliert und trennen
**beobachtet**, **abgeleitet** und **unbekannt**. Keine Pseudocode-, String- oder
Adress-Dumps, Screenshots oder Rohberichte in GitHub übernehmen. Aus einer
geprüften Spezifikation entstehen begrenzte Implementierungs-Issues.

Fehlende Tools, Identitätsabweichungen, ein Ghidra-Timeout oder eine durch die
Windows-Anwendungssteuerung blockierte Komponente ergeben `blocked`. Die
Richtlinie wird nicht umgangen. Im lokalen SAC-freien Lauf wurde `PR2.exe`
statisch geöffnet und Pseudocode für eine Funktion geliefert. Das belegt
weder eine vollständige Analyse des Spiels noch die Rekonstruktion des
ursprünglichen C++-Quellcodes.

Der gemeinsame Ablauf wurde synthetisch geprüft. Der Codex-CLI-Aufruf mit
REA-MCP-Konfiguration wurde zusätzlich live geprüft. Claude ist lokal
installiert, aber nicht angemeldet; eine echte Claude-REA-Sitzung ist bisher
nicht nachgewiesen.
