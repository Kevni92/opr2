# Executable baseline

Scope: a bounded, static inspection of the fresh GOG installation's manifest-bound `PR2.exe`. The executable was opened read-only with Ghidra through the configured local REA server. No original program was run and no prior Ghidra project or snapshot was imported.

## Observations

- REA reported the supplied SHA-256 identity for `PR2.exe`; the opened file was identified as a PE executable for x86.
- Ghidra 12.1.2 completed its default analysis. The overview reported six mapped segments, 20,348 procedures and 6,562 strings.
- Three targeted procedure-name searches for DirectDraw, Direct3D and DirectSound returned no matches.
- Evidence type: REA's target identity and binary metadata, Ghidra's segment and analysis counts, and bounded procedure-name search results. The raw evidence bundle is retained privately under the run's `analysis/` directory.

## Inferences

- The inspected artifact is the exact manifest-bound fresh executable and is a 32-bit Windows PE. This describes the executable format and architecture only; it does not establish compatibility with any particular Windows version or hardware.
- The three empty name searches do not establish that the game lacks graphics or audio subsystems. Names may be absent, indirect, or differently represented, and no complete import or call-path study was performed.
- No subsystem boundary is established by this limited pass. The overview's counts and mapped segments are inventory metadata, not evidence of game behavior.

## Unknowns

- Which graphics, audio, input, networking, storage, or platform APIs are used, and how their responsibilities are divided.
- Whether subsystem APIs are called directly, through wrappers, or through dynamically resolved symbols.
- The behavior and coverage of individual procedures; no procedure bodies were analyzed for this note.

This note intentionally contains no binary content, pseudocode, string listings, addresses, or raw reports. It does not claim complete analysis or behavioral parity.
