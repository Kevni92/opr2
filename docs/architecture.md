# Architekturüberblick

opr2 ist als eigenständiges C++20-Spiel mit CMake für Windows und Linux
vorgesehen. Derzeit ist nur der Bootstrap vorhanden; dieses Dokument legt
Arbeitsgrenzen fest und behauptet keine implementierte Engine- oder
Inhaltsparität.

Der lokale Orchestrator steuert Issues, Worktrees, Worker, Validierung,
Commits, Pull Requests, unabhängige Reviews und Merge-Gates. Provider und
Modelle werden über `automation/config.json` sowie Rollenargumente gewählt.
Codex, Claude Code und weitere Adapter müssen denselben Task-Vertrag und die
zentralen Policies verwenden. Native `.codex/`- oder `.claude/`-Dateien sind
optionale Adapter-Komfortfunktionen.

Das Laufzeitpaket wird ausschließlich aus Projektergebnissen gebaut und
enthält das Programm sowie unsere Anweisungen. Nutzer stellen erforderliche
Original-Spieldaten selbst neben das Programm. Die fertige Implementierung
darf keine Original-DLL voraussetzen. Keine Projektlizenz wurde ausgewählt.
