#!/usr/bin/env python3
"""
update_confluence.py
--------------------
Reads changed Braze event schema JSON files and updates their corresponding
Confluence pages via the Confluence REST API.

Usage (called by GitHub Actions):
    python scripts/update_confluence.py schemas/braze-events/purchase_completed.json

Required environment variables:
    CONFLUENCE_URL        e.g. https://yourcompany.atlassian.net/wiki
    CONFLUENCE_EMAIL      your Atlassian account email
    CONFLUENCE_API_TOKEN  your Atlassian API token
"""

import sys
import json
import os
import requests
from datetime import datetime


# ---------------------------------------------------------------------------
# Config from environment variables
# ---------------------------------------------------------------------------
CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL", "").rstrip("/")
EMAIL = os.environ.get("CONFLUENCE_EMAIL", "")
API_TOKEN = os.environ.get("CONFLUENCE_API_TOKEN", "")


def get_auth_headers() -> dict:
    """Return HTTP headers with Basic auth for the Confluence API."""
    import base64
    token = base64.b64encode(f"{EMAIL}:{API_TOKEN}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get_page(page_id: str) -> dict:
    """Fetch the current page metadata from Confluence (needed for version bump)."""
    url = f"{CONFLUENCE_URL}/rest/api/content/{page_id}?expand=version,body.storage"
    response = requests.get(url, headers=get_auth_headers())
    response.raise_for_status()
    return response.json()


def build_properties_table(properties: dict) -> str:
    """Build an HTML table of event properties for Confluence storage format."""
    rows = ""
    for prop_name, prop_info in properties.items():
        required = "Yes" if prop_info.get("required") else "No"
        rows += f"""
        <tr>
            <td><strong>{prop_name}</strong></td>
            <td>{prop_info.get('type', 'N/A')}</td>
            <td>{required}</td>
            <td>{prop_info.get('description', '')}</td>
        </tr>"""

    return f"""
    <table>
        <thead>
            <tr>
                <th>Property</th>
                <th>Type</th>
                <th>Required</th>
                <th>Description</th>
            </tr>
        </thead>
        <tbody>{rows}
        </tbody>
    </table>"""


def build_page_content(schema: dict) -> str:
    """Convert a schema dict into Confluence storage-format HTML."""
    props_table = build_properties_table(schema.get("properties", {}))
    status = schema.get("status", "active").upper()
    status_color = "Green" if status == "ACTIVE" else "Yellow"

    return f"""
<ac:structured-macro ac:name="info">
  <ac:parameter ac:name="title">Auto-generated from GitHub</ac:parameter>
  <ac:rich-text-body>
    <p>This page is automatically maintained from the schema file
    <code>schemas/braze-events/{schema['event_name']}.json</code> in GitHub.
    Do not edit manually — your changes will be overwritten on next merge.</p>
  </ac:rich-text-body>
</ac:structured-macro>

<h2>Event Overview</h2>
<table>
  <tbody>
    <tr><td><strong>Event Name</strong></td><td><code>{schema['event_name']}</code></td></tr>
    <tr><td><strong>Status</strong></td><td>
      <ac:structured-macro ac:name="status">
        <ac:parameter ac:name="colour">{status_color}</ac:parameter>
        <ac:parameter ac:name="title">{status}</ac:parameter>
      </ac:structured-macro>
    </td></tr>
    <tr><td><strong>Trigger</strong></td><td>{schema.get('trigger', '')}</td></tr>
    <tr><td><strong>Description</strong></td><td>{schema.get('description', '')}</td></tr>
    <tr><td><strong>Last Updated</strong></td><td>{schema.get('last_updated', '')}</td></tr>
    <tr><td><strong>Updated By</strong></td><td>{schema.get('updated_by', '')}</td></tr>
  </tbody>
</table>

<h2>Event Properties</h2>
{props_table}

<h2>Full Schema (JSON)</h2>
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">json</ac:parameter>
  <ac:plain-text-body><![CDATA[{json.dumps(schema, indent=2)}]]></ac:plain-text-body>
</ac:structured-macro>

<p><em>Page auto-updated by GitHub Actions on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</em></p>
"""


def update_confluence_page(page_id: str, schema: dict) -> None:
    """Fetch the current page version and push updated content."""
    print(f"  Fetching page {page_id} from Confluence...")
    page = get_page(page_id)
    current_version = page["version"]["number"]
    page_title = page["title"]

    new_content = build_page_content(schema)

    print(f"  Updating '{page_title}' (version {current_version} → {current_version + 1})...")
    url = f"{CONFLUENCE_URL}/rest/api/content/{page_id}"
    payload = {
        "version": {"number": current_version + 1},
        "title": page_title,
        "type": "page",
        "body": {
            "storage": {
                "value": new_content,
                "representation": "storage"
            }
        }
    }

    response = requests.put(url, headers=get_auth_headers(), json=payload)
    response.raise_for_status()
    print(f"  ✅ Successfully updated: {CONFLUENCE_URL}/wiki/pages/viewpage.action?pageId={page_id}")


def validate_env() -> bool:
    """Check that all required environment variables are set."""
    missing = []
    if not CONFLUENCE_URL:
        missing.append("CONFLUENCE_URL")
    if not EMAIL:
        missing.append("CONFLUENCE_EMAIL")
    if not API_TOKEN:
        missing.append("CONFLUENCE_API_TOKEN")
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        return False
    return True


def process_schema_file(file_path: str) -> bool:
    """Load a schema JSON and update its Confluence page. Returns True on success."""
    print(f"\nProcessing: {file_path}")

    if not os.path.exists(file_path):
        print(f"  ⚠️  File not found (may have been deleted): {file_path}")
        return False

    with open(file_path) as f:
        try:
            schema = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  ❌ Invalid JSON in {file_path}: {e}")
            return False

    page_id = schema.get("confluence_page_id")
    if not page_id or page_id == "YOUR_PAGE_ID_HERE":
        print(f"  ⚠️  Skipping {file_path}: 'confluence_page_id' is not set.")
        return False

    try:
        update_confluence_page(page_id, schema)
        return True
    except requests.HTTPError as e:
        print(f"  ❌ HTTP error updating Confluence: {e.response.status_code} {e.response.text}")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False


def main():
    if not validate_env():
        sys.exit(1)

    # Schema files are passed as CLI arguments by the GitHub Action
    schema_files = sys.argv[1:]

    if not schema_files:
        print("No schema files specified. Pass file paths as arguments.")
        print("Example: python scripts/update_confluence.py schemas/braze-events/purchase_completed.json")
        sys.exit(0)

    print(f"🚀 Updating {len(schema_files)} Confluence page(s)...")

    results = [process_schema_file(f) for f in schema_files]
    failed = results.count(False)

    print(f"\n{'='*50}")
    print(f"Done. {results.count(True)} succeeded, {failed} failed.")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
