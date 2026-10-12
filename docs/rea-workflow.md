# Analyse mit REA MCP und Ghidra

REA MCP ist eine ausdr?cklich aktivierte lokale Analysef?higkeit. Codex und
Claude erhalten dieselbe stdio-Konfiguration; Ghidra liefert die native
statische Analyse. F?r eine begrenzte Analyseaufgabe enth?lt der Issue-Vertrag
zus?tzlich `"capabilities": ["rea"]` und `"requires_original_data": true`.
Normale Implementierungsaufgaben starten keinen REA-Server.

Installiere die GOG-Version in root `pr2/`, lege einmalig das Integrit?tsmanifest
an und richte REA, Ghidra sowie das passende JDK lokal ein. Kopiere
[rea-mcp.example.json](../automation/rea-mcp.example.json) nach
`local/rea.mcp.json` und passe `command`, `args`, `GHIDRA_INSTALL_DIR` und
`JAVA_HOME` an. Das Beispiel setzt `rea mcp` im PATH voraus; alternativ kann
`command` auf Node und `args` auf eine lokal installierte REA-CLI zeigen.
Rechnerpfade und Konfiguration bleiben in `local/`. Es wird genau ein lokaler
stdio-Server namens `rea` akzeptiert; Remote-Endpunkte sind ausgeschlossen.

Der Orchestrator pr?ft `pr2/PR2.exe` gegen das lokale Manifest und ?bergibt
Zielpfad, Identit?t und Analyseausgabepfad. Der Agent ?ffnet genau dieses Ziel
mit `provider_id=ghidra` und vergleicht die von REA gemeldete Identit?t. Fr?here
Ghidra-Projekte oder Snapshots werden nicht ?bernommen. Die Bin?rdatei wird
weder ausgef?hrt noch als Datei in einen Prompt eingef?gt.

Der Codex-Adapter l?dt REA ausdr?cklich mit einer Liste zul?ssiger statischer
Tools. Der Claude-Adapter nutzt `--strict-mcp-config` mit demselben Server und
einzelnen erlaubten MCP-Tools. Der unabh?ngige Reviewer erh?lt keinen Export-
oder Schreibauftrag. Weitere CLIs k?nnen den lokalen Kontext ?ber den
Platzhalter `{rea_context}` beziehen; ihr Adapter muss dieselben Grenzen
umsetzen. Das ist keine Betriebssystem-Sandbox f?r den MCP-Server.

Die Liste in `tools/rea_workflow.py` erlaubt Ziel?ffnung, Metadaten, Funktionen,
Strings, Referenzen, Bytes und Funktionsanalyse. Der Worker kann Evidenz lokal
exportieren. Runtime-Beobachtungen, Originalausf?hrung, Annotationen,
Datenbankmutationen und Extraktion sind ausgeschlossen.

Alle behaltenen Rohbefunde, Ghidra-Ausgaben und Evidenzpakete geh?ren in das
absolute, im Auftrag genannte Verzeichnis unter root `analysis/runs/`.
?ffentliche Erkenntnisse werden eigenst?ndig formuliert und trennen
**beobachtet**, **abgeleitet** und **unbekannt**. Keine Pseudocode-, String- oder
Adress-Dumps, Screenshots oder Rohberichte in GitHub ?bernehmen. Aus einer
solchen gepr?ften Spezifikation entstehen begrenzte Implementierungs-Issues.

Fehlende Tools, Identit?tsabweichungen oder eine durch die Windows-
Anwendungssteuerung blockierte Ghidra-Komponente ergeben `blocked`. Die
Richtlinie wird nicht umgangen. Auf diesem Entwicklerrechner ist eine solche
Blockade des nativen Ghidra-Decompilers bekannt; erfolgreiche Zielidentifikation
belegt deshalb noch keine abgeschlossene tiefe Analyse.

Der gemeinsame Ablauf wurde synthetisch gepr?ft. Der Codex-CLI-Protokollaufruf
wurde zus?tzlich live gepr?ft. Claude ist lokal installiert, aber nicht
angemeldet; eine echte Claude-REA-Sitzung ist bisher nicht nachgewiesen.
