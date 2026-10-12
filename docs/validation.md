# Validierung und CI

Validierung prüft den Projektcode, Pakete und bei Bedarf die Unversehrtheit der
lokalen Referenzinstallation. Sie bestätigt weder Spielbarkeit noch Parität mit
Port Royale 2.

## Lokale Prüfung

Führe aus dem Repository-Root aus:

```text
python tools/validate.py --build-dir build/validation
```

Vor jedem Orchestrator-Lauf muss ein lokales Manifest vorhanden sein, wenn
`pr2/` im Repository liegt. Es wird auch dann benötigt, wenn die Aufgabe keine
Originaldaten verwendet:

```text
python tools/reference_manifest.py create --root pr2 --output analysis/reference-manifest.json
```

Bei Aufgaben mit Originaldaten wird die Installation vor und nach der lokalen
Validierung mit diesem Manifest geprüft:

```text
python tools/validate.py --build-dir build/validation --original-data pr2 --manifest analysis/reference-manifest.json
python tools/reference_manifest.py verify --root pr2 --manifest analysis/reference-manifest.json
```

Das Manifest muss ausserhalb von `pr2/` und unter `analysis/` liegen. Bei einer
Abweichung die Ursache untersuchen. Das Manifest nie neu erstellen oder
ersetzen, um eine Änderung zu verbergen. Ein fehlendes oder veraltetes
Manifest ist kein Integritaetsnachweis.

Die Guard-Werkzeuge sind Teil der Abnahme:

```text
python tools/asset_guard.py --repo . --history
python tools/package_guard.py build/validation/package
```

Für den Paket-Provenienzvergleich muss der Aufruf zusätzlich beide erwarteten
Dateien angeben. Passe den Programmpfad an dein Betriebssystem an:

```text
python tools/package_guard.py build/validation/package --built-executable build/validation/Release/opr2.exe --readme-source docs/runtime-package.txt
```

Unter Linux heißt das Programm `build/validation/opr2`. Mit beiden Optionen
vergleicht der Guard die Paketdateien byteweise mit dem Build-Programm und der
README-Quelle. Der Aufruf nur mit dem Paketverzeichnis prüft Dateiformat und
erlaubte Paketstruktur, belegt aber nicht die Herkunft der Inhalte.
`tools/validate.py` führt den Provenienzvergleich des installierten Pakets
automatisch aus.

Die Asset-Prüfung untersucht Repository und Git-Historie. Die Paketprüfung
stellt sicher, dass das Verzeichnis die erlaubte Laufzeitlieferung enthält.
Ein Paket besteht aus dem projekterstellten `opr2.exe` (Windows) oder `opr2`
(Linux) sowie einer `README.txt`; es enthält keine Originaldateien. Kompilierte
Build-Ausgaben liegen getrennt vom Paketverzeichnis.

## GitHub Actions

Der Workflow läuft bei Push auf `main`, Pull Request, `workflow_dispatch` und
`merge_group`. Feature-Branch-Pushes erzeugen keinen zusaetzlichen Status auf
dem Pull-Request-Head. Er baut mit Visual Studio 2022 auf `windows-2022` sowie mit Ninja und
GCC auf Ubuntu. Ein zusätzlicher Ubuntu-Lauf verwendet Clang mit AddressSanitizer
und UndefinedBehaviorSanitizer. Python 3.11 führt die Validierung aus.

Der Windows-Runner ist ausdrücklich gewählt, weil `windows-latest` inzwischen
Visual Studio 2026 verwendet. Die Zuordnung ist in der
[GitHub-Runner-Ankündigung](https://github.com/actions/runner-images/issues/14017)
dokumentiert; lokale VS-2022-Presets bleiben damit auch in CI überprüfbar.

Für automatischen Merge muss die Branch-Protection auf GitHub für `main`
required status checks mit `strict: true` verlangen und `validation-required`
als Check enthalten. PR-Basis und zuvor gelesener `baseRefOid` müssen beim
Merge noch übereinstimmen. Der Bootstrap richtet diese Regel ein; der Orchestrator
prüft den aktuellen Serverzustand vor der Ausführung des Worker-Laufs und
nochmals vor Merge. Eine manuelle oder spaetere Änderung, die diese Regel
entfernt oder abschwaecht, blockiert Automerge.

Der stabile Status `validation-required` fasst alle Matrix-Läufe zusammen und
ist der Status, der für Branch-Schutz oder Merge Queue erforderlich ist. Er
schlägt fehl, sobald ein Lauf fehlschlägt oder übersprungen wird. CI bekommt
nur `contents: read`; es erhält keine Originaldaten, Modellzugänge oder
API-Geheimnisse. Hochgeladen wird ausschließlich das nach erfolgreicher
Paketprüfung erzeugte Verzeichnis `build/ci/package`, niemals Build-Ordner,
Logs oder Analyse-Ausgaben.

## Integritätsgrenzen

Hooks und Guards erkennen bekannte versehentliche Datei- und Paketlecks. Sie
bilden keine Betriebssystem-Sandbox. Der Orchestrator vergleicht sichtbare
Änderungen im Worktree; ignorierte Dateien und beliebige Schreibzugriffe
ausserhalb davon können der Prüfung entgehen. Die lokale Kontrolle der
Referenzdaten erfolgt über den Manifestvergleich vor und nach der Arbeit.
GitHub Actions verwendet nur
synthetische Testdaten und prüft nicht die lokale GOG-Installation. Fehlende,
fehlgeschlagene oder veraltete Nachweise blockieren Merge.
