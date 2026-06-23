# Community guide

NĀSADĪYA LIGHTCONE is an open research-visualisation project. Contributions are welcome when they improve scientific traceability, software reliability, accessibility, or the clarity of a survey-native view of the Universe.

## Where to begin

1. Read the [scientific scope](docs/scientific-scope.md) and [data policy](DATA_POLICY.md).
2. Follow [Getting started](docs/getting-started.md) to run the browser locally.
3. Open an issue before proposing a substantial new survey layer, visual interpretation, or data-hosting change.
4. Use the issue templates for bugs and catalogue/source proposals.

## Good first contributions

- Improve keyboard, touch, contrast, and screen-reader support.
- Strengthen ingestion validation for a published survey release.
- Add tests for source-column mapping, unit handling, or manifest provenance.
- Improve a documentation diagram, quickstart command, or scientific caveat.
- Propose a survey layer with a stable source URL, documented licence, citation, selection criteria, and uncertainty treatment.

## Data contribution standard

A new catalogue adapter must state:

- the release, source table, and stable retrieval location;
- the coordinate system and units;
- the redshift measurement type and uncertainty field;
- selection and quality cuts;
- the distance transform used only for visual navigation;
- how source footprint/masking is communicated;
- the required citation and acknowledgement text.

Observed rows, derived density fields, mock catalogues, and hand-authored annotations must always remain distinct layers.

## Discussion principles

Be constructive, evidence-led, and respectful. The [Code of Conduct](CODE_OF_CONDUCT.md) applies to all project spaces. Security concerns should follow [SECURITY.md](SECURITY.md), not public issues.
