# AGENTS.md

## Cursor Cloud specific instructions

This is a **Braze Event Schema Registry** — a documentation-as-code repo that stores JSON schema definitions for Braze events and syncs them to Confluence via GitHub Actions. There are no long-running services.

### Key components

| Component | Description |
|---|---|
| `schemas/braze-events/*.json` | Braze event schema definitions (custom format, not strict JSON Schema) |
| `scripts/update_confluence.py` | Python script that syncs schemas to Confluence pages |
| `.github/workflows/validate-schemas.yml` | CI: validates schemas with `ajv compile --strict=false` |
| `.github/workflows/update-confluence.yml` | CD: syncs changed schemas to Confluence on merge to `main` |

### How to validate schemas locally

```bash
ajv compile -s schemas/braze-events/<schema>.json --strict=false
```

Note: The schemas use a custom `required: true/false` boolean per-property rather than the JSON Schema standard array-at-object-level format. This causes `ajv compile` to report `data/properties/.../required must be array`. This is a known pre-existing behavior in the repo.

### How to test the Confluence sync script

```bash
python3 scripts/update_confluence.py schemas/braze-events/purchase_completed.json
```

Requires environment variables: `CONFLUENCE_URL`, `CONFLUENCE_EMAIL`, `CONFLUENCE_API_TOKEN`. Without these, the script exits with an error message listing the missing variables — this is expected behavior.

### Dependencies

- **Python 3.11+** with `requests` (pre-installed in the VM)
- **Node.js 20+** with `ajv-cli` installed globally via `npm install -g ajv-cli`

### Gotchas

- `ajv-cli` must be installed to a user-writable prefix (`~/.npm-global`) since system `/usr/lib/node_modules` is not writable. The update script handles this. Ensure `~/.npm-global/bin` is on `PATH`.
- The `update_confluence.py` script is intended to be run by GitHub Actions CI, not locally, unless you have valid Confluence API credentials set as environment variables.
