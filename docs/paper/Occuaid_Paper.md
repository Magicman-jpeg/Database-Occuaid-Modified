# Occuaid: A Web-based Hospital Patient and Room Capacity Management System

Jay Clifferson P. Arevalo  
Christopher Z. Balana  
Fiona Lei B. Bravo  
Marie Antoinette P. Alpuerto  
Victor G. Quirit III  

**Abstract: ** Hospital staff need to know quickly which rooms can accept a new patient, and contagious patients must never be placed in shared rooms. This paper presents Occuaid, a web-based system that tracks rooms, patients and admissions and enforces these placement rules in the server. The system uses a four-table SQLite database (room_types, rooms, patients, admissions), an HTML and JavaScript client, and a REST API implemented twice: in Node.js with Express and in PHP with PDO. The PHP API is the backend that was run and tested for this paper and is the one deployed to Vercel as a serverless function. A suite of 21 automated HTTP checks was run against the PHP API on a fresh database; all 21 passed. User acceptance testing has not been conducted.

**Keywords: ** hospital room management, capacity tracking, isolation room, PHP, SQLite, JavaScript, HTML, REST API

## I. INTRODUCTION

Hospitals have a limited number of beds, and the beds differ by room type. An intensive care unit (ICU) room may hold five patients, a private room one, and a general ward eight. When a patient arrives, staff must find a room that has a free bed, is not under maintenance, and suits the patient. If the patient is contagious, the room must be a single-occupancy isolation room. Doing this from paper lists or memory is slow and error prone. Hospital bed capacity and resource allocation are central to healthcare management [1].

Occuaid is a web-based system that keeps the current state of every room, lists the patients and their admissions, and checks each admission against the placement rules before it is saved. The project has three goals: (1) store rooms, patients and admissions in a normalized relational database; (2) reject an admission that breaks a rule, namely a full room, a room in maintenance, or a contagious patient outside an isolation room; and (3) give staff a browser dashboard that shows capacity at a glance.

The design parameters of the system are PHP for the server-side API, SQLite for the database, HTML for the pages, and JavaScript for the browser client. The same REST API was written in Node.js with Express and in PHP. The PHP version is the one that was executed and tested for this paper.

## II. BACKGROUND

A room in Occuaid belongs to a room type. The room type holds the amenities (air conditioning, television, private bathroom), the bed capacity, and a flag that marks it as an isolation unit, following the guidance on isolation rooms in the CDC environmental infection control guidelines [2]. A room has a number, a current occupancy and a status of Available, Full or Maintenance. A patient record holds the name, contact number, medical case and a contagious flag. An admission links one patient to one room over a period of time and is Active until the patient is discharged.

The schema follows the principle stated in schema.sql, "walang labis, walang kulang" (nothing superfluous, nothing missing). Bed capacity is stored once per room type and is not repeated in each room, which avoids duplicated data.

## III. LITERATURE REVIEW

Web-based management systems replace manual record keeping with a shared database and a browser interface. Hospital management systems increasingly support resource allocation and workflow automation [3]. The sample paper used as the model for this document, a web-based library management system [4], describes the same kind of workflow: a relational database, a server-side language, and an HTML front end for staff. Occuaid applies that approach to hospital rooms instead of library books. The client and the API communicate through a REST interface, an architectural style defined by Fielding [5].

SQLite is a self-contained, serverless SQL database engine that stores a database in one file [6]. It supports CHECK constraints, foreign keys and partial unique indexes, all of which Occuaid uses. PHP accesses databases through the PDO extension, which provides one interface for several database drivers and supports prepared statements [7]. Express is a minimal web framework for Node.js [8], a platform that runs JavaScript on the server [9]. The browser client calls the API with the Fetch API [10].

## IV. METHODOLOGY

### A. Database Design

Conceptual design. The domain has four entities. A room type describes a category of room. A room is a physical instance of one room type. A patient is a person who is registered in the system. An admission records that a patient occupies a room. One room type has many rooms, one room has many admissions over time, and one patient has many admissions over time (Fig. 1).

```
room_types (PK type_id) | type_name, is_isolation_unit, has_aircon, has_tv, has_private_bathroom, bed_capacity
1 room type has N rooms
rooms (PK room_id, FK type_id) | room_number, current_occupancy, status
1 room has N admissions
admissions (PK admission_id, FK patient_id, FK room_id) | admission_date, discharge_date, status
1 patient has N admissions
patients (PK patient_id) | first_name, last_name, contact_number, medical_case, is_contagious, admission_status, created_at
```
*Fig. 1. Entity relationship diagram of Occuaid (crow's foot shown as 1 to N).*

Logical design. The schema is in third normal form, which rests on the relational model [11] and its normalization theory [12]. The attributes of each relation are listed in Fig. 1. Primary keys are integers. The foreign keys rooms.type_id, admissions.patient_id and admissions.room_id use ON DELETE RESTRICT so that referenced rows cannot be removed while they are in use.

Physical design. The schema is implemented in SQLite (schema.sql). Boolean values are stored as integers with CHECK (x IN (0, 1)). Room status and admission status are text columns restricted by CHECK constraints to the allowed values. A partial unique index, uq_patient_active_admission on admissions(patient_id) WHERE status = 'Active', guarantees that a patient has at most one active admission. Two further indexes speed up lookups by room and by status. The file also seeds five room types, nine rooms, five patients and three active admissions.

### B. Architecture Design

Occuaid has a client tier, an API tier and a data tier (Fig. 2). The browser client in public/ is plain HTML, CSS and JavaScript and is served by the Express server. The API tier exists in two implementations with the same endpoints, JSON shapes, status codes and error messages: server.js (Node.js, Express) and php/index.php (PHP 8, PDO). The data tier is a single SQLite file. A static demo in docs/ runs entirely in the browser with data in sessionStorage [13] and is published on GitHub Pages; it has no server.

```
CLIENT: Browser (HTML, CSS, JavaScript) | public/ (Express client), docs/ (static demo)
HTTP, JSON (fetch /api/*)
Node.js + Express (server.js) | PHP 8 + PDO (php/index.php, api/index.php)
db.js (SQLite driver) | php/db.php (PDO sqlite)
DATA: SQLite file (schema.sql, hospital.db)
Static demo: docs/ on GitHub Pages, data in sessionStorage, no server
```
*Fig. 2. System hierarchy of Occuaid.*

The PHP API can be run locally with the built-in server (php -S localhost:8000 php/router.php). For deployment, api/index.php is a Vercel serverless entry that copies the database to the writable /tmp directory and loads php/index.php. Vercel serverless functions run it through a community PHP runtime. This runtime and its version could not be verified from the offline environment where the paper was prepared, and data written on Vercel does not persist between function instances.

### C. Interface Design

The Express client in public/index.html has a sidebar with three pages: Dashboard, Patients and Admissions. The Dashboard page, titled Current capacity, shows a summary strip and a grid of room cards, with a filter panel for room type, status and the amenities air conditioning, television and private bathroom. The Patients page lists patients in a table (number, patient, contact, medical case, room, status, admitted on) with a search box and status tabs. The Admissions page lists admission history (ID, patient, room, type, admitted, discharged, status) with status tabs.

An Admit a patient dialog collects first name, last name, contact number, medical case, a contagious toggle and the room. Only rooms that can accept patients are offered. Errors returned by the API, such as the isolation rule message, are shown in the dialog. The static demo in docs/ has separate pages (index, dashboard, patients, admissions) with the same layout. No screenshots are included because the browser client was not run during the preparation of this paper.

### D. Module Design

The central module is the admission procedure, implemented in POST /api/admissions in both server.js and php/index.php (Fig. 3). The request is validated first (first name, last name and room are required). The room and its room type are then read inside a database transaction. The room must exist, must not be in Maintenance, and must have a free bed. If the patient is contagious, the room type must be an isolation unit with a bed capacity of one. Only then are the patient and the active admission inserted and the room occupancy and status updated. Because these steps share one transaction, occupancy cannot drift from the admission records.

```
START: POST /api/admissions
Names and room_id present? No: 400
Room exists? No: 404
Room in Maintenance? Yes: 409
Occupancy >= bed capacity? Yes: 409 Room is already full
Contagious? If yes: isolation unit AND bed capacity = 1? No: 409
Insert patient and active admission
Update occupancy; status Full if occupancy >= capacity, else Available
COMMIT, return 201 with admission_id
```
*Fig. 3. Flowchart of the admission process with the capacity and isolation checks.*

The other modules are discharge (PATCH /api/admissions/:id/discharge), which closes the admission, marks the patient Discharged and frees the bed unless the room is in Maintenance; room status change (PATCH /api/rooms/:id/status), which switches a room between Available and Maintenance; and the read endpoints for health, room types, rooms (with filters), admissions and patients.

## V. EVALUATION METHOD

The evaluation covers what was actually run. All tests target the PHP API, because the Node.js dependencies (Express) could not be installed in the offline environment, so server.js was not executed. The test levels used here (unit checks and integration tests) follow the usual categories and levels of software testing [14], [15].

### A. Unit Testing

Testing follows the general guidance on software testing in [14]. Each PHP file was checked for syntax errors with php -l (php/db.php, php/index.php, php/router.php and api/index.php). No separate unit test framework was used. Database constraints are exercised indirectly by the API tests below.

### B. Integration Testing

The script tests/php-api.test.mjs sends HTTP requests to the PHP API and checks status codes and response bodies. It covers the PHP code, PDO and SQLite together, including the business rules and the validation errors.

### C. System Testing

The script tests/run-php-tests.sh builds a fresh database from schema.sql, starts php -S with php/router.php on that database, runs the integration script, and records the output in docs/paper/test-results.txt. The committed hospital.db files are not touched. The Vercel entry api/index.php was started with php -S and answered requests, but no deployment to Vercel was tested.

### D. User Acceptance Testing

User acceptance testing has not been conducted. It is left as future work with hospital staff or a representative group of users.

## VI. EXPERIMENTAL RESULTS

Table I lists selected test cases and the results recorded in docs/paper/test-results.txt. The complete run had 21 checks, of which 21 passed and 0 failed.

**TABLE I: TEST CASES AND ACTUAL RESULTS (PHP API)**

| Test Case | Test Purpose | Test Condition | Expected Outcome | Actual Result |
|---|---|---|---|---|
| T1 | Health check | GET /api/health | 200 with ok true | PASS |
| T2 | Seed room types loaded | GET /api/room-types on fresh DB | 5 room types | PASS |
| T3 | Seed rooms loaded | GET /api/rooms on fresh DB | 9 rooms | PASS (got 9) |
| T4 | Contagion rule rejects shared room | POST admission, contagious, room type ICU | 409 with isolation message | PASS (409 Contagious patients can only be assigned to Isolation units. "ICU" is not an isolation room.) |
| T5 | Contagion rule accepts isolation room | POST admission, contagious, room ISO-502 | 201 Created | PASS (201) |
| T6 | Capacity check | POST admission into full room | 409 Room is already full | PASS (409 Room is already full.) |
| T7 | Normal admission | POST admission, non-contagious, regular room | 201 Created | PASS (201) |
| T8 | Input validation | POST admission without first_name | 400 | PASS (400) |
| T9 | Unknown room | POST admission with nonexistent room_id | 404 | PASS (404) |
| T10 | Amenity filter | GET /api/rooms?aircon=1 | Only aircon rooms | PASS (7 rooms) |
| T11 | Discharge | PATCH discharge of active admission | 200 | PASS (200) |
| T12 | Double discharge | PATCH discharge of the same admission | 409 | PASS (409) |
| T13 | Room reopens | ISO-502 after discharge | Status Available | PASS |
| T14 | Maintenance rule | POST admission into Maintenance room | 409 | PASS (409) |
| T15 | Unknown route | GET unknown /api path | 404 | PASS |

The two rules that define the system behaved as specified. A contagious patient sent to an ICU room was rejected with status 409 and the message that the room type is not an isolation room (T4), and the same kind of patient was accepted in isolation room ISO-502 (T5). A full room rejected a further admission (T6), a room in maintenance rejected admissions (T14), and discharge reopened the room (T13).

Limitations: the tests ran on a local PHP server with a freshly seeded database, response times were not measured, concurrent users were not simulated, and the browser interface was not tested by automation.

## VII. CONCLUSION

Occuaid combines a four-table SQLite database, an HTML and JavaScript client and a PHP REST API to manage room capacity and enforce placement rules. All 21 automated checks passed on the PHP API, including the isolation rule for contagious patients and the capacity checks. PHP serves as the tested backend and as the Vercel serverless function, while the Express version provides the same behavior for Node.js hosting.

Future work includes user acceptance testing, deploying and verifying the Vercel function, a persistent database for the hosted version, user login and roles, and room transfer between admissions.

## REFERENCES

[1] Optimizing Hospital Bed Capacity and Resource Allocation Using Inflow and Outflow Indices for Effective Healthcare Management, 2024.  
[2] Centers for Disease Control and Prevention (CDC), "Guidelines for Environmental Infection Control in Health-Care Facilities," CDC, Atlanta, GA, USA, Tech. Rep., 2019.  
[3] S. Banerjee, "IoT-based smart hospital management system: Real-time patient monitoring, resource allocation, and workflow automation," Int. J. Res. Appl. Sci. Eng. Technol. (IJRASET), vol. 14, pp. 3550–3555, 2026, doi: 10.22214/ijraset.2026.84167.  
[4] T. W. Araya and A. Mengsteab, "Designing web-based library management system," Int. J. Eng. Res. Technol. (IJERT), vol. 9, no. 10, pp. 272–277, Oct. 2020, doi: 10.17577/IJERTV9IS100131.  
[5] R. T. Fielding, "Architectural styles and the design of network-based software architectures," Ph.D. dissertation, Dept. Inf. Comput. Sci., Univ. California, Irvine, CA, USA, 2000.  
[6] SQLite Consortium, "SQLite Documentation," SQLite Official Documentation, 2026.  
[7] The PHP Group, "PHP Manual: PHP Data Objects (PDO)," PHP Documentation, 2026.  
[8] OpenJS Foundation, "Express: Fast, unopinionated, minimalist web framework for Node.js."  
[9] S. Tilkov and S. Vinoski, "Node.js: Using JavaScript to build high-performance network programs," IEEE Internet Comput., vol. 14, no. 6, pp. 80–83, Nov./Dec. 2010.  
[10] Mozilla Developer Network (MDN), "Fetch API," MDN Web Docs, 2026.  
[11] E. F. Codd, "A relational model of data for large shared data banks," Commun. ACM, vol. 13, no. 6, pp. 377–387, Jun. 1970.  
[12] C. J. Date, An Introduction to Database Systems, 8th ed. Boston, MA, USA: Addison-Wesley, 2004.  
[13] I. Hickson, "Web storage (second edition)," W3C Recommendation, Jan. 2021.  
[14] G. J. Myers, C. Sandler, and T. Badgett, The Art of Software Testing, 3rd ed. Hoboken, NJ, USA: John Wiley & Sons, 2011.  
[15] M. A. Umar, "A study of software testing: Categories, levels, techniques, and types," TechRxiv, 2020, doi: 10.36227/techrxiv.12578714.v1.  
