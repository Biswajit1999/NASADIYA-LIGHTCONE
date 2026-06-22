# Contributing

1. Open an issue before adding a substantial data layer or visual interpretation.
2. Keep raw survey files out of Git unless their licence and size make that explicitly appropriate.
3. Include source release, source table, citation, selection criteria, and coordinate convention for every submitted catalogue adapter.
4. Preserve an observed-versus-derived distinction in the browser layer.
5. Run `pytest -q`, `ruff check pipeline scripts tests`, and `npm run check:modules` before opening a pull request.
