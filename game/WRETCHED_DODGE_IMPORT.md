# Wretched Demesne DODGE import

This import follows DODGE v0.1.0 as defined by the Digitropolis reference implementation.

- `wretched-demesne.dodge.v0.1.json` contains only concepts representable by the official DODGE v0.1 schema.
- `wretched-demesne.gdd.sidecar.v0.1.json` is DODGE-adjacent and holds game semantics and design artifacts not representable by v0.1.
- The sidecar includes both structured extension candidates and a complete parsed-text transcription of the source GDD, making the pair lossless with respect to the supplied design document.
- Deliberately unresolved design questions are preserved as unresolved.
- Future DODGE revisions should migrate sidecar concepts into official fields without changing their meaning, then retain only genuinely unsupported material in the sidecar.

The official DODGE file references the sidecar as its rules/entity source rather than duplicating those facts.
