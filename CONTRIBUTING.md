# Beiträge zu opr2

Für native Untersuchungen gilt zusätzlich die Anleitung
[REA MCP und Ghidra](docs/rea-workflow.md). Die REA-Fähigkeit ist bei Codex und
Claude ausdrücklich aktivierbar; die lokale Konfiguration bleibt in `local/`.

Die verbindlichen Regeln stehen in [AGENTS.md](AGENTS.md),
[docs/workflow.md](docs/workflow.md) und [docs/validation.md](docs/validation.md).
Alle Mitwirkenden und Anbieter müssen denselben Issue-Vertrag, dieselben
Schutzregeln und dieselben Abnahmekriterien verwenden.

## Einrichtung

Klone das Repository und wechsle in den Arbeitsordner:

```text
git clone https://github.com/Kevni92/opr2.git
cd opr2
```

Installiere Git, CMake, Python 3.11 und eine C++20-Toolchain. Unter Windows
benötigst du Visual Studio Build Tools 2022 mit C++; unter Linux GCC oder Clang
sowie Ninja. Installiere außerdem GitHub CLI (`gh`) und mindestens einen
unterstützten Provider-CLI (`codex` oder `claude`). Der Orchestrator installiert
keine Provider und wählt kein Modell stillschweigend aus.

Authentifiziere GitHub CLI lokal und prüfe den Zugriff:

```text
gh auth login
gh auth status
```

Installiere mindestens einen Provider und schließe dessen lokalen
Anmeldevorgang ab. Für Codex:

```text
codex --version
codex login
```

Für Claude Code:

```text
claude --version
claude
```

Beim Start von Claude Code schließe die Anmeldung mit `/login` ab. Prüfe die
aktuelle Login-Anleitung und Optionen der jeweiligen Provider-CLI; diese
Dokumentation bestätigt keine Live-Authentifizierung oder Ende-zu-Ende-Ausführung
beider Anbieter. Zugangsdaten und Rohprotokolle bleiben lokal; GitHub Actions
erhält keine Provider- oder Modellzugänge.

Lege eine lokale Orchestrator-Konfiguration an, die nicht eingecheckt wird:

```text
python -c "import pathlib; pathlib.Path('local').mkdir(exist_ok=True); pathlib.Path('local/orchestrator.json').write_bytes(pathlib.Path('automation/config.json').read_bytes())"
```

Führe vor der ersten Aufgabe die lokale Validierung aus:

```text
python tools/validate.py --build-dir build/validation
```

Passe `local/orchestrator.json` an und übergib sie mit `--config`. Die
Beispielkonfiguration verwendet Codex als Worker und Reviewer. Andere Provider
und Modelle lassen sich je Rolle wählen:

```text
python tools/orchestrator.py plan --issue N --config local/orchestrator.json
python tools/orchestrator.py run --issue N --config local/orchestrator.json --provider claude --model sonnet --review-provider codex --review-model gpt-6-luna
```

Die ausdrücklich ausgewählte Codex-Koordinatorrolle verwendet GPT-6 Sol mit
geringem Reasoning-Aufwand. Worker und der separate Reviewer verwenden GPT-6
Luna. Der deterministische Runner ist ein Python-Programm und benötigt kein
zusätzliches Koordinatormodell. Die Rollen und ihre Übergaben stehen im
[Rekonstruktionsworkflow](docs/reconstruction-workflow.md). Andere teurere
Modelle werden nur ausdrücklich ausgewählt.

Die neue Konfiguration spezifiziert Queue, Wiederaufnahme und Spezialrollen.
Ihre ausführbare Einbindung wird in den GitHub-Folgeissues umgesetzt; bis dahin
sind ausschließlich die bestehenden Befehle `plan` und `run` verfügbar. Die
Einrichtung hat keine neuen Arbeitspakete auf `agent:ready` gesetzt.

Der Codex-Adapter benötigt eine CLI mit benannten Berechtigungsprofilen. Er
setzt für Worker `:workspace`, für Reviewer `:read-only` und übernimmt kein
Full-Access-Profil des aufrufenden Prozesses. Er lädt die globale
`config.toml` nicht, damit zusätzliche MCP-Server nicht unbeabsichtigt starten.
Unter Windows trage deshalb die bereits eingerichtete Sandbox im lokalen
Codex-Provider ein, zum Beispiel:

```json
"windows_sandbox": "elevated"
```

Unterstützte Werte sind `mxc`, `elevated` und `unelevated`; wähle die auf
deinem Rechner eingerichtete und erlaubte Variante. Der Runner richtet keine
Sandbox ein, ändert keine Host-Richtlinien und weicht bei Fehlern nicht auf
Full Access aus. Die Optionen folgen der offiziellen Dokumentation zu
[Berechtigungsprofilen](https://learn.chatgpt.com/docs/permissions) und zur
[Windows-Sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox).

Ein eigener CLI-Adapter kann unter `providers` mit `"kind": "command"`
eingetragen werden. `command` ist ein argv-Array; der Orchestrator startet es
ohne Shell. Die Platzhalter `{model}`, `{role}`, `{workspace}`, `{schema}`,
`{output}` und `{analysis}` werden in Argumenten ersetzt. `{analysis}` ist beim
Worker der absolute private Rohdatenordner dieses Laufs; beim Reviewer ist der
Platzhalter leer. Der Prompt wird über stdin übergeben; der Adapter muss die zum
Worker- oder Reviewer-Schema passende JSON-Antwort in die Datei `{output}`
schreiben. Die Schemas stehen in `automation/worker-result.schema.json` und
`automation/review-result.schema.json`. Beispiel für den Inhalt eines Provider-
Eintrags:

```json
{
  "kind": "command",
  "command": ["my-adapter", "--model", "{model}", "--role", "{role}", "--workspace", "{workspace}", "--schema", "{schema}", "--output", "{output}", "--analysis", "{analysis}"],
  "models": {"worker": "model-a", "reviewer": "model-b"}
}
```

## Ablauf in Kürze

1. Erstelle ein GitHub Issue mit dem Task-JSON-Vertrag aus
   [docs/workflow.md](docs/workflow.md). Nur `small`-Aufgaben sind
   automatisierbar; zerlege größere Aufgaben vorher. Ein Maintainer prüft
   Umfang und Kriterien und setzt anschließend `agent:ready`.
2. Prüfe, dass alle Abhängigkeiten geschlossen sind. Wenn `pr2/` existiert,
   erstelle vor `run` das Referenzmanifest. Ersetze es bei einer Abweichung
   niemals, um Änderungen zu verbergen.
3. Führe `plan --issue N --config local/orchestrator.json` aus und prüfe den
   Plan. Starte danach `run --issue N --config local/orchestrator.json`.
4. Der Worker bearbeitet Dateien. Der Orchestrator prüft Umfang und Guards und
   erstellt lokal einen Commit `#N Implement bounded issue task`. Eine
   unabhängige Review erfolgt vor der Ausführung des geänderten Codes und vor
   der automatischen Validierung.
5. Erst nach Review-Freigabe laufen lokale Validierung und Tests. Nach Erfolg
   pusht der Orchestrator den Commit und erstellt den Pull Request.
6. Automerge erfordert für `main` GitHub Branch Protection mit required status
   checks, `strict: true` und dem Check `validation-required`. Der Bootstrap
   richtet den Schutz ein; der Runner prüft ihn vor und nach dem PR-Lauf. Die
   PR-Basis muss weiterhin dem zuvor gelesenen `baseRefOid` entsprechen.

Der aktuelle Windows-Build mit statischer MSVC-Laufzeit besteht die lokalen
C++-Tests. Wenn Windows AppControl einen künftigen Build blockiert, darf diese
Schutzrichtlinie nicht umgangen werden; ohne erfolgreiche lokale Tests kein
Automerge. CI ersetzt die erfolgreiche lokale Validierung nicht. `--no-merge`
lässt den Pull Request offen; ein Resume-Befehl ist derzeit nicht vorhanden.

## Lokale Hooks

Hooks sind optional und gelten nur für dieses Repository. Installiere sie mit
`python tools/install_hooks.py`; der Befehl setzt `core.hooksPath` lokal auf
`.githooks/`. Er installiert nichts global. Die Hooks sind zusätzliche
Frühwarnungen und ersetzen weder CI noch die Prüfung des Orchestrators.

## Sprache und Lizenz

Contributor-Dokumentation ist deutsch, Quellcode und Kommentare im Code sind
englisch. Eine Projektlizenz wurde noch nicht ausgewählt; füge keine Lizenz
implizit hinzu.
