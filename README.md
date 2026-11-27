# Occuaid — Hospital Patient & Room Capacity Management System

A full-stack app that manages hospital room/bed capacity with patient case
tracking, contagion isolation rules, and room amenity management.

**Stack:** PHP (PDO) and Node.js (Express) backends · SQLite (local file) · HTML + Tailwind (CDN) + vanilla JS (Fetch API).

## Project layout

| Path | What it is |
|------|------------|
| `php/` | PHP backend: `/api/*` endpoints (`index.php`), PDO SQLite connection (`db.php`), dev-server router (`router.php`) |
| `api/index.php` | Vercel entry point for the PHP API |
| `server.js`, `db.js`, `init-db.js` | Node.js (Express) backend with the same API |
| `schema.sql` | Database schema and sample data |
| `public/` | Web client served by the PHP and Node servers |
| `docs/` | Deployed site (Vercel and GitHub Pages); runs in the browser with demo data |
| `docs/paper/` | Research paper (`Occuaid_Paper.docx`), its build script and the recorded test results |
| `tests/` | API tests for the PHP and Node backends |
| `run.bat` | Windows one-click launcher for the Node server |

`hospital.db` is not stored in the repository. Both backends create it from
`schema.sql` the first time they run.

---

## What changed in this refactor

Based on professor feedback, three targeted improvements were made:

### 1. Patient Case & Contagion Isolation
- The `patients` table now has a `medical_case` (free-text diagnosis) and
  `is_contagious` (boolean) field.
- **Business rule enforced in the API:** if `is_contagious == true`, the patient
  can **only** be assigned to a room whose room type has `is_isolation_unit = 1`
  **and** `bed_capacity = 1` (single-occupancy Isolation unit).
- The UI lets you mark a patient as contagious; the room dropdown automatically
  filters to eligible Isolation rooms, and the backend returns a clear error if
  the rule is violated.

### 2. Expanded Room Amenities
- Room types now carry amenity flags: `has_aircon`, `has_tv`,
  `has_private_bathroom`, `bed_capacity`, and `is_isolation_unit`.
- The dashboard shows amenity badges on every room card and offers filter
  checkboxes (Aircon / TV / Bathroom).

### 3. Entity Balance (Minimalist)
- The schema has exactly four entities: `room_types`, `rooms`, `patients`,
  `admissions` — nothing superfluous, nothing missing ("walang labis, walang kulang").
- The old `departments` table was removed; `bed_capacity` was normalised into
  `room_types` so each room inherits its capacity from its type.

---

## Quick start (Windows)

1. **Download/clone** this repository to any local folder.
2. **Double-click `run.bat`** — it will:
   - Check Node.js is installed
   - Run `npm install` (first time only)
   - Initialise the SQLite database (`hospital.db`) with sample data
   - Start the server on `http://localhost:5000`
   - Open your default browser automatically

> Requires [Node.js](https://nodejs.org/) LTS (v18 or newer).

### Manual start
```bash
npm install
npm run init-db      # creates hospital.db with tables + sample data
npm start            # starts the server on port 5000
```
Then open http://localhost:5000

---

## PHP backend (first-class)

PHP is a first-class backend of Occuaid, alongside the Node server. The `php/`
folder implements the same `/api/*` endpoints as `server.js` (same JSON shapes,
status codes, error messages and the contagion isolation rule) using PDO SQLite.

```bash
# from the project root, needs PHP 8+ with pdo_sqlite
php -S localhost:8000 php/router.php
```

Then open http://localhost:8000. `php/router.php` serves `public/` and sends
`/api/*` to `php/index.php`. Set `OCCUAID_DB` to use a different SQLite file. If
the file does not exist, it is created from `schema.sql` (schema plus seed data).

### Tests

```bash
PHP_BIN=php tests/run-php-tests.sh
```

The script runs `php -l` on every PHP file, starts `php -S` on a throwaway
database (your local `hospital.db` is never touched) and runs
`tests/php-api.test.mjs`: 21 checks covering the contagion rule, full and
maintenance rooms, discharge, filters and validation. Result of the latest run:
all 21 passed, saved in `docs/paper/test-results.txt`. `tests/node-api.test.mjs` also reads
`BASE` from the environment (`BASE=http://localhost:8000 node tests/node-api.test.mjs`).

---

## Deploying to Vercel (free Hobby plan)

`vercel.json` serves the static demo in `docs/` and runs the PHP API from
`api/index.php` using the community `vercel-php@0.7.4` runtime. It uses nothing
paid: no cron jobs, no add-ons, no analytics.

1. Sign in at vercel.com on the free **Hobby** plan and import the GitHub repo
   (or run `npx vercel` from the project root).
2. Leave the defaults. `vercel.json` sets the output directory to `docs` and
   routes `/api/*` to `api/index.php`.
3. Do not enable any paid add-on or upgrade prompt. Hobby needs no payment method.

Caveats:

- `vercel-php` is a community runtime. The `api/index.php` entry and the rewrite
  were checked locally with `php -S`, but the runtime version `0.7.4` could not be
  verified offline, so check the first deployment's build log.
- On Vercel the SQLite file lives in `/tmp` and is rebuilt from `schema.sql` on a
  cold start, so API data is ephemeral. The static `docs/` demo keeps its data in
  the visitor's browser (`localStorage`, key `occuaid_demo_v1`).

---

## Database schema

### room_types
| Column | Type | Description |
|--------|------|-------------|
| `type_id` | INTEGER PK | Auto-increment |
| `type_name` | TEXT UNIQUE | e.g. ICU, Private, Isolation |
| `is_isolation_unit` | INTEGER (0/1) | Single-occupancy isolation flag |
| `has_aircon` | INTEGER (0/1) | Air conditioning |
| `has_tv` | INTEGER (0/1) | Television |
| `has_private_bathroom` | INTEGER (0/1) | Private bathroom |
| `bed_capacity` | INTEGER | Max beds for rooms of this type |

### rooms
| Column | Type | Description |
|--------|------|-------------|
| `room_id` | INTEGER PK | Auto-increment |
| `room_number` | TEXT UNIQUE | e.g. ICU-101, ISO-501 |
| `type_id` | INTEGER FK → room_types | Links to amenities + capacity |
| `current_occupancy` | INTEGER | Runtime state (managed by API) |
| `status` | TEXT | Available / Full / Maintenance |

### patients
| Column | Type | Description |
|--------|------|-------------|
| `patient_id` | INTEGER PK | Auto-increment |
| `first_name` | TEXT | |
| `last_name` | TEXT | |
| `contact_number` | TEXT | |
| `medical_case` | TEXT | Diagnosis / reason for admission |
| `is_contagious` | INTEGER (0/1) | Infectious disease flag |
| `admission_status` | TEXT | Admitted / Discharged / Transferred |
| `created_at` | TEXT | Timestamp |

### admissions
| Column | Type | Description |
|--------|------|-------------|
| `admission_id` | INTEGER PK | Auto-increment |
| `patient_id` | INTEGER FK → patients | |
| `room_id` | INTEGER FK → rooms | |
| `admission_date` | TEXT | Timestamp |
| `discharge_date` | TEXT | Set on discharge |
| `status` | TEXT | Active / Discharged |

A partial unique index ensures a patient can have at most one Active admission.

---

## API

| Method | Route | Purpose |
|--------|-------|---------|
| GET   | `/api/health` | DB connectivity check |
| GET   | `/api/room-types` | List room types + amenities |
| GET   | `/api/rooms` | Rooms with amenities. Query: `?type=&status=&aircon=1&tv=1&bathroom=1` |
| GET   | `/api/admissions?active=true` | Active admissions with patient + room info |
| POST  | `/api/admissions` | Admit: `{ first_name, last_name, contact_number, medical_case, is_contagious, room_id }` |
| PATCH | `/api/admissions/:id/discharge` | Discharge a patient |
| PATCH | `/api/rooms/:id/status` | Set `Available` / `Maintenance` |

### Contagion validation (POST /api/admissions)

If `is_contagious` is `true` and the selected room is not a single-occupancy
Isolation unit, the API returns HTTP 409 with a message like:

> "Contagious patients can only be assigned to Isolation units. 'ICU' is not an isolation room."

---

## How the capacity logic works

1. **Admit** → `INSERT` into `admissions` (status='Active'), then
   `current_occupancy + 1` and flip `status` to `Full` if now at capacity.
   All in one SQLite transaction.
2. **Discharge** → `UPDATE admissions SET status='Discharged'`, then
   `current_occupancy - 1` and reopen the room (unless Maintenance).

Because occupancy is updated atomically within the same transaction as the
admission/discharge, the counts can never drift out of sync.

---

## Notes

- Zero cloud dependencies — the entire system runs locally with a single
  SQLite file (`hospital.db`). No AWS, Firebase, or external database.
- All file paths are relative; the project runs from any folder.
- The `docs/` folder is the deployed site on Vercel and GitHub Pages. It runs
  entirely in the browser with demo data and is not required for local operation.
- This is sample/demo software. For real clinical use you'd add
  authentication, audit logging, and data-privacy controls.
