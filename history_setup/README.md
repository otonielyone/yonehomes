# Your FastAPI database: domain context and history archive

This package uses **your existing application database**:

`/var/www/html/yonehomes/brightscrape/brightmls.db`

It adds three tables to that same SQLite file. It does not create another database, change the MLS tables, or configure n8n's internal database. This matches the SQLite database in the source you uploaded. If the live app has since moved to PostgreSQL/Neon, do not point this SQLite adapter at it; that backend needs its own adapter.

The architecture is:

**n8n → authenticated FastAPI endpoints → your existing database**, with a synchronized copy in `/var/www/html/yonehomes/history/n8n_dns_foundation_history.json`.

The package contains:

- `yone_public_websites.json`: configure/check public root and www web DNS for both domains.
- `toni_yone_explicit_aliases.json`: the previously requested two explicit email aliases.
- `install_history.py`: install modules and attach the history router to your existing FastAPI app.
- `start_files/history_store.py`: database tables, immutable file versions, event search, facts and file synchronization.
- `start_files/history_archive.py`: FastAPI endpoints and server CLI.
- `domain_context_seed.json`: 28 evidence-labeled facts from this conversation.
- `n8n_app_history_client.json`: import the server archive, retrieve context, and save a sync execution through FastAPI.
- `env-history.example`: additions for your existing `.env`; no secrets are included.

## 1. Public website access first

Import `yone_public_websites.json` into n8n as a separate workflow. Select your existing **Cloudflare account** credential in the five Cloudflare API HTTP nodes; **Check Public HTTPS** needs no credential.

The Cloudflare token needs **Zone Read** and **DNS Edit** for both domains.

Click **Execute workflow**. It verifies the active zones, reads current DNS, applies only necessary web-record changes, then checks all four addresses:

| Address | Intended DNS |
| --- | --- |
| `yonehomes.com` | A → `66.124.127.168` |
| `www.yonehomes.com` | CNAME → `yonehomes.com` |
| `yonesolutions.com` | A → `66.124.127.168` |
| `www.yonesolutions.com` | CNAME → `yonesolutions.com` |

It preserves correct records and existing proxy choices. Conflicting root/www A, AAAA and CNAME records are replaced as necessary. Mail records are outside its changes. It adds no website redirects; your site controls navigation.

Success is `allPublic: true` in **Final Public Access Result**, with a successful HTTPS response for every host. This proves HTTP reachability, not the correctness of every application feature. A failed HTTPS request may indicate origin service, host routing, firewall or certificate configuration. This workflow cannot install certificates or deploy an application; the existing server must already serve these hostnames. DNS changes may already be applied if a later HTTPS check fails. Diagnose the failed host instead of repeatedly changing DNS.

If both domains already have the intended records, the workflow performs reads and public checks without DNS writes.

## 2. Install the archive into your existing application

Upload/extract this package on your server, for example into:

`/var/www/html/yonehomes/history_setup`

The extracted directory must contain `install_history.py`, `README.md`, and `start_files/` directly.

Run:

```bash
cd /var/www/html/yonehomes/history_setup
/var/www/html/yonehomes/venv/bin/python install_history.py --app-root /var/www/html/yonehomes
```

The installer requires your existing `brightmls.db` to exist. It copies only the two new Python modules into the existing `start_files/` directory and backs up `app.py` before adding:

```python
from start_files.history_archive import router as history_router
app.include_router(history_router)
```

It locates one top-level `app = FastAPI(...)` assignment. If your application is built by a factory or uses a different structure, it stops with an explicit message; attach those two lines after creating your actual app instead. Existing routes and models are retained. It does not restart the service.

Your app already uses FastAPI and python-dotenv. If either dependency is missing from that virtual environment:

```bash
/var/www/html/yonehomes/venv/bin/python -m pip install -r requirements-history.txt
```

Do not replace or upgrade the rest of the app's dependency file for this feature.

## 3. Configure the actual database and history paths

Add these lines to the **existing** `/var/www/html/yonehomes/.env`:

```dotenv
APP_DATABASE_PATH=/var/www/html/yonehomes/brightscrape/brightmls.db
APP_HISTORY_DIR=/var/www/html/yonehomes/history
APP_HISTORY_FILE=n8n_dns_foundation_history.json
```

These values are explicit so a different working directory cannot accidentally select another SQLite file. If the actual live database path differs, set `APP_DATABASE_PATH` to the existing file your FastAPI app uses. The archive refuses to silently create a missing database file.

Authentication uses the first configured secret in this order:

1. `HISTORY_API_KEY`
2. `FASTAPI_API`
3. `API_KEY`

The values stay on your server and in n8n credentials. They are not stored in the seed or database facts. If `FASTAPI_API` contains a URL, use `HISTORY_API_KEY` for the real secret instead. This authentication choice does not alter your existing routes' `check_key()` implementation.

## 4. Initialize, import all existing history, and load known context

Run from the application root:

```bash
cd /var/www/html/yonehomes
/var/www/html/yonehomes/venv/bin/python -m start_files.history_archive init
/var/www/html/yonehomes/venv/bin/python -m start_files.history_archive import
/var/www/html/yonehomes/venv/bin/python -m start_files.history_archive seed --seed-file /var/www/html/yonehomes/history_setup/domain_context_seed.json
/var/www/html/yonehomes/venv/bin/python -m start_files.history_archive status
```

`init` adds only `app_history_events`, `app_history_facts`, and `app_history_archives` to your existing database. `import` walks the history directory, preserves original bytes and checksums, and extracts JSON/JSONL events. Changed files produce new archive versions; unchanged files and events are not duplicated. Hidden lock/temp files and symlinks are skipped. Files larger than the default 64 MiB cap are reported rather than silently truncated; `APP_HISTORY_MAX_FILE_BYTES` can change that cap.

`seed` records the domain, DNS, mail, app-route and database knowledge from this conversation in both the database and `learned_context` in the JSON history file. Facts include a source, status and observation time. Repeating seed installation does not overwrite newer facts.

The original history document, record ID, snapshots and unrelated fields remain. Original file bytes are archived before the mirror changes the JSON file. A failed mirror leaves the event committed in the database with pending status, and retains the original file. Retry with:

```bash
/var/www/html/yonehomes/venv/bin/python -m start_files.history_archive sync
```

Check `pendingFileMirror: 0`, `historyFileSaved: true`, and no import `errors`. `status` intentionally does not print API keys.

**Use the FastAPI endpoints for future writes to the shared history file.** The new writer coordinates its own concurrent requests with a lock and atomic file replacement. Your old SSH history-writing nodes do not use that lock; leaving two different writers modifying the same file concurrently can lose an update. Replace those old write nodes with API event writes. Files saved elsewhere in the history directory can still be imported.

## 5. Restart your existing FastAPI service

Restart it using the service/container command you already use. The supplied files do not reveal its unit name, so this package does not guess a `systemctl` command.

Open the app's `/docs` page and confirm `/api/history/...` endpoints are listed. If your app disables Swagger, test `/api/history/health` from n8n instead.

## 6. Connect n8n to your FastAPI API

Create one n8n **Header Auth** credential named **FastAPI API**:

```text
Name: Authorization
Value: Bearer <your real secret from the server environment>
```

Do not put the secret in Code nodes or workflow JSON. n8n Cloud cannot read a server's `.env` file directly.

Import `n8n_app_history_client.json`. Select the **FastAPI API** credential in every HTTP node. **History Configuration** starts with `https://yonehomes.com`; change it only if your FastAPI API has a different base URL.

Execute the workflow. It checks the API, imports all history pages, fetches known context, and saves the archive-run result to both your database and the history file.

Success is:

```json
{"databaseSaved": true, "historyFileSaved": true}
```

No workflow should claim file archival succeeded when `historyFileSaved` is false. Retry using the same idempotency key after fixing the file error.

## API endpoints

Every endpoint below requires the Bearer key.

| Method | Path | Use |
| --- | --- | --- |
| GET | `/api/history/health` | Existing database path, counts and pending mirror count |
| POST | `/api/history/events` | Save a workflow result/event to database and history file |
| GET | `/api/history/events?q=...` | Search events; supports `event_type`, `limit`, `offset` |
| GET | `/api/history/events/{id}` | Read one event |
| POST | `/api/history/facts` | Save/update a sourced fact and archive the update |
| GET | `/api/history/facts?prefix=mail.&q=...` | Read current learned facts |
| GET | `/api/history/context?q=yonesolutions.com` | Facts and recent matching events for a task |
| POST | `/api/history/import?after=...&limit=100` | Import a page of server history files |
| POST | `/api/history/sync` | Retry pending file mirroring |
| GET | `/api/history/archives?q=...` | Search original file versions |
| GET | `/api/history/archives/{id}` | Download original bytes; response includes SHA-256 |

## Save every future workflow result

Add an **HTTP Request** node after a workflow's final result:

- Method: `POST`
- URL: `https://yonehomes.com/api/history/events`
- Authentication: your **FastAPI API** Header Auth credential
- Send Body: **ON as a fixed toggle**
- Body Content Type: JSON
- Specify Body: Using JSON

Use this expression as its complete JSON body:

```javascript
{{ {
  event_type: 'workflow.finished',
  source: 'n8n',
  idempotency_key: String($workflow.id) + ':' + String($execution.id) + ':final',
  payload: {
    workflow_id: $workflow.id,
    workflow_name: $workflow.name,
    execution_id: $execution.id,
    result: $json
  }
} }}
```

Give different result-writing stages in one execution distinct suffixes instead of reusing `:final`. A retry with the same key and identical content returns the original event; different content with that same key returns HTTP 409. The database commit happens before the file mirror, so retries are safe after partial file failures.

This records results only for workflows where the node is added. It does not automatically capture every n8n execution globally or train an AI model.

Before a future domain/DNS task, use a GET node:

```text
https://yonehomes.com/api/history/context?q=yonehomes.com
```

Give its result to the task/AI node as context. Use the stored sources and dates, and re-read live Cloudflare before DNS changes.

## Update specific facts after a verified change

Use `POST /api/history/facts` to promote a planned alias only AFTER its live-read verification succeeds:

```json
{
  "key": "mail.yonehomes.com.toni_yone_alias",
  "value": {
    "address": "toni.yone@yonehomes.com",
    "forward_to": "otonielyone@gmail.com",
    "execution_confirmation_received": true
  },
  "status": "verified",
  "source": "Cloudflare rule read-back from n8n execution <actual execution ID>",
  "observed_at": "<actual UTC verification time>"
}
```

Do the corresponding update for `yonesolutions.com` using its own verified result. The seed records your confirmation that the aliases are complete as reported evidence; a successful API read-back can promote them to independently verified evidence.

After the public-site workflow passes, record its final result as an event and update `hosting.public_websites` with the actual checks, `status: verified`, and that execution's real observation time. Keep old evidence in events; facts represent the latest sourced state.

## What is verified versus user-confirmed

API-verified historical evidence: both IONOS/Cloudflare zones passed cleanup; Cloudflare MX and DKIM matched; both catch-all rules targeted `otonielyone@gmail.com`; the supplied `toni@yonehomes.com` rule targeted `yonesolutions@gmail.com`.

User-confirmed: the new aliases and website access are complete, as stated on October 12. Those facts are marked `reported` with your confirmation as the source. They are not labeled unfinished. A later live API/public HTTPS result can mark them `verified` independently.

The uploaded app used SQLite; a Neon migration was not shown. This package's live installation is not claimed to have happened from this workspace.

No passwords, API tokens, `.env` values or private keys are included in the seed.

## Validation and limits

Storage tests run with the real SQLite library against an existing sample MLS database: model preservation, exact original-byte recovery, repeat imports, event idempotency, conflicting retries, concurrent writes, mirror failure/recovery, Unicode search and retention of newer facts.

The Python source compiles. Workflow code and graph references are checked, including fixed Send Body booleans and retention of mail records. Live Cloudflare changes, public HTTPS reachability, FastAPI server integration, service restart and end-to-end delivery must be confirmed on your server; they have not been executed from this workspace.
