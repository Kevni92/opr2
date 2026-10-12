# Analyse mit REA MCP und Ghidra

REA MCP ist eine ausdrücklich aktivierte lokale Analysefähigkeit. Codex und
Claude erhalten dieselbe stdio-Konfiguration; Ghidra liefert die native
statische Analyse. Für eine begrenzte Analyseaufgabe enthält der Issue-Vertrag
zusätzlich `"capabilities": ["rea"]` und `"requires_original_data": true`.
Normale Implementierungsaufgaben starten keinen REA-Server.

Installiere die GOG-Version in root `pr2/`, lege einmalig das Integritätsmanifest
an und richte REA, Ghidra sowie das passende JDK lokal ein. Kopiere
[rea-mcp.example.json](../automation/rea-mcp.example.json) nach
`local/rea.mcp.json` und passe `command`, `args`, `GHIDRA_INSTALL_DIR` und
`JAVA_HOME` an. Das Beispiel setzt `rea mcp` im PATH voraus; alternativ kann
`command` auf Node und `args` auf eine lokal installierte REA-CLI zeigen.
Rechnerpfade und Konfiguration bleiben in `local/`. Es wird genau ein lokaler
stdio-Server namens `rea` akzeptiert; Remote-Endpunkte sind ausgeschlossen.

Der Orchestrator prüft `pr2/PR2.exe` gegen das lokale Manifest und übergibt
Zielpfad, Identität und Analyseausgabepfad. Der Agent öffnet genau dieses Ziel
mit `provider_id=ghidra` und vergleicht die von REA gemeldete Identität. Frühere
Ghidra-Projekte oder Snapshots werden nicht übernommen. Die Binärdatei wird
weder ausgeführt noch als Datei in einen Prompt eingefügt.

Der Codex-Adapter lädt REA ausdrücklich mit einer Liste zulässiger statischer
Tools. Der Claude-Adapter nutzt `--strict-mcp-config` mit demselben Server und
einzelnen erlaubten MCP-Tools. Der unabhängige Reviewer erhält keinen Export-
oder Schreibauftrag. Weitere CLIs können den lokalen Kontext über den
Platzhalter `{rea_context}` beziehen; ihr Adapter muss dieselben Grenzen
umsetzen. Das ist keine Betriebssystem-Sandbox für den MCP-Server.

Die Liste in `tools/rea_workflow.py` erlaubt Zielöffnung, Metadaten, Funktionen,
Strings, Referenzen, Bytes und Funktionsanalyse. Der Worker kann Evidenz lokal
exportieren. Runtime-Beobachtungen, Originalausführung, Annotationen,
Datenbankmutationen und Extraktion sind ausgeschlossen.

Alle behaltenen Rohbefunde, Ghidra-Ausgaben und Evidenzpakete gehören in das
absolute, im Auftrag genannte Verzeichnis unter root `analysis/runs/`.
Öffentliche Erkenntnisse werden eigenständig formuliert und trennen
**beobachtet**, **abgeleitet** und **unbekannt**. Keine Pseudocode-, String- oder
Adress-Dumps, Screenshots oder Rohberichte in GitHub übernehmen. Aus einer
solchen geprüften Spezifikation entstehen begrenzte Implementierungs-Issues.

Fehlende Tools, Identitätsabweichungen oder eine durch die Windows-
Anwendungssteuerung blockierte Ghidra-Komponente ergeben `blocked`. Die
Richtlinie wird nicht umgangen. Auf diesem Entwicklerrechner ist eine solche
Blockade des nativen Ghidra-Decompilers bekannt; erfolgreiche Zielidentifikation
belegt deshalb noch keine abgeschlossene tiefe Analyse.

Der gemeinsame Ablauf wurde synthetisch geprüft. Der Codex-CLI-Protokollaufruf
wurde zusätzlich live geprüft. Claude ist lokal installiert, aber nicht
angemeldet; eine echte Claude-REA-Sitzung ist bisher nicht nachgewiesen.
