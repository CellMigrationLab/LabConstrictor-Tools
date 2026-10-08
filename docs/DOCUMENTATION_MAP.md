# Documentation map

Shared Python contract and authoring.

The [README](../README.md) is the entry point. Detailed material belongs in the sections below. This map records the intended structure; a named page may still need to be created or updated by the implementation maintainers.

| Section | Intended file | Scope |
|---|---|---|
| Start here | `README.md` | Purpose, a short working example, host links and installation status |
| Write a tool | `AUTHORING.md` | Signatures, annotations, output types, errors, cancellation and registration |
| Host feature support | `HOST_FEATURES.md` | Host-by-host behavior and unsupported hints; maintained with host code |
| Protocol | `PROTOCOL.md` | Versioned schema, worker messages, data formats and compatibility |
| Operations | `OPERATIONS.md` | Registry, installations, diagnostics, logging and security boundaries |
| Integration | `LABCONSTRICTOR_INTEGRATION.md` | Application packaging and installer hooks |
| Repository map | `REPOSITORIES.md` | Ownership boundaries and links to host repositories |
| Testing | `HUMAN_TEST_PROTOCOL.md and tests/README.md` | Manual matrix and automated tests |

## Maintenance

Keep exact protocol and schema definitions here, not copied into each host README. Code owners should verify the sample command, return type and installation instructions.

When changing a tool or host behavior, update the relevant section in the same PR. Prefer one tested example to several unverified ones. Mark unsupported behavior explicitly; do not turn planned features into present-tense claims.
