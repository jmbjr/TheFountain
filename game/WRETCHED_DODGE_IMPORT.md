# Wretched Demesne DODGE import

This import follows DODGE v0.1.0 as defined by the Digitropolis reference implementation.

- `wretched-demesne.dodge.v0.1.json` contains only concepts representable by the official DODGE v0.1 schema.
- `wretched-demesne.gdd.sidecar.v0.1.json` is DODGE-adjacent and holds game semantics and design artifacts not representable by v0.1.
- The sidecar includes both structured extension candidates and a complete parsed-text transcription of the source GDD, making the pair lossless with respect to the supplied design document.
- Deliberately unresolved design questions are preserved as unresolved.
- Future DODGE revisions should migrate sidecar concepts into official fields without changing their meaning, then retain only genuinely unsupported material in the sidecar.

The official DODGE file references the sidecar as its rules/entity source rather than duplicating those facts.


## Current DODGE conformance

The original import remains as historical provenance. The active Wretched document is now `wretched-demesne.dodge.v0.2.json`, targeting official **DODGE 0.2.0**.

The project must remain compliant with official DODGE as it evolves. Under 0.2.0, the GDD sidecar is formally declared as an adjacent lossless source, component profiles are neutral DODGE data, and exporters share one resolved component inventory. Semantics deliberately deferred by 0.2.0 remain in the sidecar rather than being promoted ad hoc into renderers.

Adopting a later official DODGE version requires explicit review of this boundary and migration of the active Wretched document/build pipeline.
