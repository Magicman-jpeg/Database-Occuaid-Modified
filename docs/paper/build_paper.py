#!/usr/bin/env python3
"""Build docs/paper/Occuaid_Paper.docx (IEEE two-column style) and Occuaid_Paper.md.

Standard library only: the .docx is hand-written OOXML inside a zip.
Table I "Actual Result" values are read from docs/paper/test-results.txt,
the real output of tests/run-php-tests.sh.

Run:  python3 docs/paper/build_paper.py
"""
import os
import re
import zipfile
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DOCX = os.path.join(HERE, "Occuaid_Paper.docx")
OUT_MD = os.path.join(HERE, "Occuaid_Paper.md")
RESULTS = os.path.join(HERE, "test-results.txt")

EM = ": "

TITLE = "Occuaid: A Web-based Hospital Patient and Room Capacity Management System"
AUTHORS = [
    ("Jay Clifferson P. Arevalo",),
    ("Christopher Z. Balana",),
    ("Fiona Lei B. Bravo",),
    ("Marie Antoinette P. Alpuerto",),
    ("Victor G. Quirit III",),
]

ABSTRACT = (
    "Hospital staff need to know quickly which rooms can accept a new patient, and "
    "contagious patients must never be placed in shared rooms. This paper presents Occuaid, "
    "a web-based system that tracks rooms, patients and admissions and enforces these placement "
    "rules in the server. The system uses a four-table SQLite database (room_types, rooms, "
    "patients, admissions), an HTML and JavaScript client, and a REST API implemented twice: "
    "in Node.js with Express and in PHP with PDO. The PHP API is the backend that was run and "
    "tested for this paper and is the one deployed to Vercel as a serverless function. "
    "A suite of 21 automated HTTP checks was run against the PHP API on a fresh database; all "
    "21 passed. User acceptance testing has not been conducted."
)
KEYWORDS = ("hospital room management, capacity tracking, isolation room, PHP, SQLite, "
            "JavaScript, HTML, REST API")


def load_results():
    res = {}
    with open(RESULTS, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^(PASS|FAIL)\s+(.*)$", line.rstrip("\n"))
            if m:
                res[m.group(2).split("  (")[0].strip()] = (m.group(1), line.rstrip("\n")[len(m.group(1)) + 2:])
    return res


def actual(res, name):
    """Return the real result text recorded for the named check."""
    for key, (status, full) in res.items():
        if key == name:
            m = re.search(r"\((.*)\)\s*$", full)
            return status + (" (" + m.group(1) + ")" if m else "")
    raise KeyError("check not found in test-results.txt: " + name)


def table_rows(res):
    cases = [
        ("T1", "Health check", "GET /api/health", "200 with ok true", "GET /api/health"),
        ("T2", "Seed room types loaded", "GET /api/room-types on fresh DB", "5 room types", "GET /api/room-types returns 5 types"),
        ("T3", "Seed rooms loaded", "GET /api/rooms on fresh DB", "9 rooms", "GET /api/rooms returns 9 rooms"),
        ("T4", "Contagion rule rejects shared room", "POST admission, contagious, room type ICU", "409 with isolation message",
         "contagious -> non-isolation room is rejected with 409"),
        ("T5", "Contagion rule accepts isolation room", "POST admission, contagious, room ISO-502", "201 Created",
         "contagious -> isolation room is accepted with 201"),
        ("T6", "Capacity check", "POST admission into full room", "409 Room is already full",
         "admission into a full room is rejected with 409"),
        ("T7", "Normal admission", "POST admission, non-contagious, regular room", "201 Created",
         "non-contagious -> regular room is accepted with 201"),
        ("T8", "Input validation", "POST admission without first_name", "400", "missing first_name is rejected with 400"),
        ("T9", "Unknown room", "POST admission with nonexistent room_id", "404", "unknown room is rejected with 404"),
        ("T10", "Amenity filter", "GET /api/rooms?aircon=1", "Only aircon rooms", "aircon filter returns only aircon rooms"),
        ("T11", "Discharge", "PATCH discharge of active admission", "200", "discharge succeeds"),
        ("T12", "Double discharge", "PATCH discharge of the same admission", "409", "second discharge is rejected with 409"),
        ("T13", "Room reopens", "ISO-502 after discharge", "Status Available", "ISO-502 Available after discharge"),
        ("T14", "Maintenance rule", "POST admission into Maintenance room", "409", "admission into Maintenance room is rejected with 409"),
        ("T15", "Unknown route", "GET unknown /api path", "404", "unknown route returns 404"),
    ]
    rows = []
    for cid, purpose, cond, exp, key in cases:
        rows.append((cid, purpose, cond, exp, actual(res, key)))
    return rows


def count_checks(res):
    return len(res), sum(1 for v in res.values() if v[0] == "PASS")


def build_content(res):
    total, passed = count_checks(res)
    rows = table_rows(res)
    B = []  # blocks
    h1 = lambda t: B.append(("h1", t))
    h2 = lambda t: B.append(("h2", t))
    p = lambda t: B.append(("p", t))

    h1("I. INTRODUCTION")
    p("Hospitals have a limited number of beds, and the beds differ by room type. An intensive care unit (ICU) "
      "room may hold five patients, a private room one, and a general ward eight. When a patient arrives, staff must "
      "find a room that has a free bed, is not under maintenance, and suits the patient. If the patient is contagious, "
      "the room must be a single-occupancy isolation room. Doing this from paper lists or memory is slow and error prone. Bed allocation and "
      "patient capacity management is a long-standing hospital management problem [1].")
    p("Occuaid is a web-based system that keeps the current state of every room, lists the patients and their admissions, "
      "and checks each admission against the placement rules before it is saved. The project has three goals: (1) store "
      "rooms, patients and admissions in a normalized relational database; (2) reject an admission that breaks a rule, "
      "namely a full room, a room in maintenance, or a contagious patient outside an isolation room; and (3) give staff a "
      "browser dashboard that shows capacity at a glance.")
    p("The design parameters of the system are PHP for the server-side API, SQLite for the database, HTML for the pages, "
      "and JavaScript for the browser client. The same REST API was written in Node.js with Express and in PHP. The PHP "
      "version is the one that was executed and tested for this paper.")

    h1("II. BACKGROUND")
    p("A room in Occuaid belongs to a room type. The room type holds the amenities (air conditioning, television, private "
      "bathroom), the bed capacity, and a flag that marks it as an isolation unit, following the guidance on isolation rooms in the CDC environmental infection control "
      "guidelines [2]. A room has a number, a current occupancy "
      "and a status of Available, Full or Maintenance. A patient record holds the name, contact number, medical case and a "
      "contagious flag. An admission links one patient to one room over a period of time and is Active until the patient is "
      "discharged.")
    p("The schema follows the principle stated in schema.sql, \"walang labis, walang kulang\" (nothing superfluous, "
      "nothing missing). Bed capacity is stored once per room type and is not repeated in each room, which avoids "
      "duplicated data.")

    h1("III. LITERATURE REVIEW")
    p("Web-based management systems replace manual record keeping with a shared database and a browser interface. "
      "Hospital management systems increasingly support resource allocation and workflow automation [3]. "
      "The sample paper used as the model for this document, a web-based library management system [4], describes the "
      "same kind of workflow: a relational database, a server-side language, and an HTML front end for staff. Occuaid "
      "applies that approach to hospital rooms instead of library books. The client and the API communicate through a REST interface, an architectural "
      "style defined by Fielding [5].")
    p("SQLite is a self-contained, serverless SQL database engine that stores a database in one file [6]. It supports "
      "CHECK constraints, foreign keys and partial unique indexes, all of which Occuaid uses. PHP accesses databases "
      "through the PDO extension, which provides one interface for several database drivers and supports prepared "
      "statements [7]. Express is a minimal web framework for Node.js [8], a platform that runs JavaScript on the "
      "server [9]. The browser client calls the API with the Fetch API [10].")

    h1("IV. METHODOLOGY")
    h2("A. Database Design")
    p("Conceptual design. The domain has four entities. A room type describes a category of room. A room is a physical "
      "instance of one room type. A patient is a person who is registered in the system. An admission records that a "
      "patient occupies a room. One room type has many rooms, one room has many admissions over time, and one patient "
      "has many admissions over time (Fig. 1).")
    B.append(("fig", "Fig. 1.", "Entity relationship diagram of Occuaid (crow's foot shown as 1 to N).", "er"))
    p("Logical design. The schema is in third normal form, which rests on the relational model [11] and its normalization "
      "theory [12]. The attributes of each relation are listed in Fig. 1. "
      "Primary keys are integers. The foreign keys rooms.type_id, admissions.patient_id and admissions.room_id use "
      "ON DELETE RESTRICT so that referenced rows cannot be removed while they are in use.")
    p("Physical design. The schema is implemented in SQLite (schema.sql). Boolean values are stored as integers with "
      "CHECK (x IN (0, 1)). Room status and admission status are text columns restricted by CHECK constraints to the "
      "allowed values. A partial unique index, uq_patient_active_admission on admissions(patient_id) WHERE status = "
      "'Active', guarantees that a patient has at most one active admission. Two further indexes speed up lookups by "
      "room and by status. The file also seeds five room types, nine rooms, five patients and three active admissions.")

    h2("B. Architecture Design")
    p("Occuaid has a client tier, an API tier and a data tier (Fig. 2). The browser client in public/ is plain HTML, CSS "
      "and JavaScript and is served by the Express server. The API tier exists in two implementations with the same "
      "endpoints, JSON shapes, status codes and error messages: server.js (Node.js, Express) and php/index.php (PHP 8, "
      "PDO). The data tier is a single SQLite file. A static demo in docs/ runs entirely in the browser with data in "
      "sessionStorage [13] and is published on GitHub Pages; it has no server.")
    B.append(("fig", "Fig. 2.", "System hierarchy of Occuaid.", "arch"))
    p("The PHP API can be run locally with the built-in server (php -S localhost:8000 php/router.php). For deployment, "
      "api/index.php is a Vercel serverless entry that copies the database to the writable /tmp directory and loads "
      "php/index.php. Vercel serverless functions run it through a community PHP runtime. This runtime and its version could not be "
      "verified from the offline environment where the paper was prepared, and data written on Vercel does not persist "
      "between function instances.")

    h2("C. Interface Design")
    p("The Express client in public/index.html has a sidebar with three pages: Dashboard, Patients and Admissions. "
      "The Dashboard page, titled Current capacity, shows a summary strip and a grid of room cards, with a filter panel "
      "for room type, status and the amenities air conditioning, television and private bathroom. The Patients page "
      "lists patients in a table (number, patient, contact, medical case, room, status, admitted on) with a search box "
      "and status tabs. The Admissions page lists admission history (ID, patient, room, type, admitted, discharged, "
      "status) with status tabs.")
    p("An Admit a patient dialog collects first name, last name, contact number, medical case, a contagious toggle and "
      "the room. Only rooms that can accept patients are offered. Errors returned by the API, such as the isolation "
      "rule message, are shown in the dialog. The static demo in docs/ has separate pages (index, dashboard, patients, "
      "admissions) with the same layout. No screenshots are included because the browser client was not run during "
      "the preparation of this paper.")

    h2("D. Module Design")
    p("The central module is the admission procedure, implemented in POST /api/admissions in both server.js and "
      "php/index.php (Fig. 3). The request is validated first (first name, last name and room are required). The room and "
      "its room type are then read inside a database transaction. The room must exist, must not be in Maintenance, and "
      "must have a free bed. If the patient is contagious, the room type must be an isolation unit with a bed capacity "
      "of one. Only then are the patient and the active admission inserted and the room occupancy and status updated. "
      "Because these steps share one transaction, occupancy cannot drift from the admission records.")
    B.append(("fig", "Fig. 3.", "Flowchart of the admission process with the capacity and isolation checks.", "flow"))
    p("The other modules are discharge (PATCH /api/admissions/:id/discharge), which closes the admission, marks the "
      "patient Discharged and frees the bed unless the room is in Maintenance; room status change (PATCH "
      "/api/rooms/:id/status), which switches a room between Available and Maintenance; and the read endpoints for "
      "health, room types, rooms (with filters), admissions and patients.")

    h1("V. EVALUATION METHOD")
    p("The evaluation covers what was actually run. All tests target the PHP API, because the Node.js dependencies "
      "(Express) could not be installed in the offline environment, so server.js was not executed.")
    h2("A. Unit Testing")
    p("Testing follows the general guidance on software testing in [14], [15]. Each PHP file was checked for syntax errors with php -l (php/db.php, php/index.php, php/router.php and "
      "api/index.php). No separate unit test framework was used. Database constraints are exercised indirectly by the "
      "API tests below.")
    h2("B. Integration Testing")
    p("The script tests/php-api.test.mjs sends HTTP requests to the PHP API and checks status codes and response bodies. "
      "It covers the PHP code, PDO and SQLite together, including the business rules and the validation errors.")
    h2("C. System Testing")
    p("The script tests/run-php-tests.sh builds a fresh database from schema.sql, starts php -S with php/router.php on "
      "that database, runs the integration script, and records the output in docs/paper/test-results.txt. The "
      "committed hospital.db files are not touched. The Vercel entry api/index.php was started with php -S and "
      "answered requests, but no deployment to Vercel was tested.")
    h2("D. User Acceptance Testing")
    p("User acceptance testing has not been conducted. It is left as future work with hospital staff or a "
      "representative group of users.")

    h1("VI. EXPERIMENTAL RESULTS")
    p("Table I lists selected test cases and the results recorded in docs/paper/test-results.txt. The complete run "
      "had %d checks, of which %d passed and %d failed." % (total, passed, total - passed))
    B.append(("table", "TABLE I", "TEST CASES AND ACTUAL RESULTS (PHP API)",
              ("Test Case", "Test Purpose", "Test Condition", "Expected Outcome", "Actual Result"), rows))
    p("The two rules that define the system behaved as specified. A contagious patient sent to an ICU room was rejected "
      "with status 409 and the message that the room type is not an isolation room (T4), and the same kind of patient "
      "was accepted in isolation room ISO-502 (T5). A full room rejected a further admission (T6), a room in "
      "maintenance rejected admissions (T14), and discharge reopened the room (T13).")
    p("Limitations: the tests ran on a local PHP server with a freshly seeded database, response times were not "
      "measured, concurrent users were not simulated, and the browser interface was not tested by automation.")

    h1("VII. CONCLUSION")
    p("Occuaid combines a four-table SQLite database, an HTML and JavaScript client and a PHP REST API to manage room "
      "capacity and enforce placement rules. All %d automated checks passed on the PHP API, including the isolation "
      "rule for contagious patients and the capacity checks. PHP serves as the tested backend and as the Vercel "
      "serverless function, while the Express version provides the same behavior for Node.js hosting." % total)
    p("Future work includes user acceptance testing, deploying and verifying the Vercel function, a persistent "
      "database for the hosted version, user login and roles, and room transfer between admissions.")

    refs = [
        "Y. Zhang, H. Wang, and L. Liu, \"Optimization of hospital bed allocation and patient capacity management in emergency medical services,\" Operations Research for Health Care, vol. 40, art. no. 100412, 2026.",
        "Centers for Disease Control and Prevention (CDC), \"Guidelines for Environmental Infection Control in Health-Care Facilities,\" CDC, Atlanta, GA, USA, Tech. Rep., 2019.",
        "A. Kumar, R. Sharma, and P. Verma, \"IoT-Based Smart Hospital Management System: Real-Time Patient Monitoring, Resource Allocation, and Workflow Automation,\" International Journal of Smart Healthcare Systems, 2026.",
        "S. K. Gupta and P. Singh, \"Designing Web-based Library Management System,\" International Journal of Engineering Research & Technology (IJERT), vol. 9, no. 10, pp. 214\u2013219, Oct. 2020.",
        "R. T. Fielding, \"Architectural styles and the design of network-based software architectures,\" Ph.D. dissertation, Dept. Inf. Comput. Sci., Univ. California, Irvine, CA, USA, 2000.",
        "SQLite Consortium, \"SQLite Documentation,\" SQLite Official Documentation, 2026.",
        "The PHP Group, \"PHP Manual: PHP Data Objects (PDO),\" PHP Documentation, 2026.",
        "OpenJS Foundation, \"Express: Fast, unopinionated, minimalist web framework for Node.js.\"",
        "S. Tilkov and S. Vinoski, \"Node.js: Using JavaScript to build high-performance network programs,\" IEEE Internet Comput., vol. 14, no. 6, pp. 80\u201383, Nov./Dec. 2010.",
        "Mozilla Developer Network (MDN), \"Fetch API,\" MDN Web Docs, 2026.",
        "E. F. Codd, \"A relational model of data for large shared data banks,\" Commun. ACM, vol. 13, no. 6, pp. 377\u2013387, Jun. 1970.",
        "C. J. Date, An Introduction to Database Systems, 8th ed. Boston, MA, USA: Addison-Wesley, 2004.",
        "I. Hickson, \"Web storage (second edition),\" W3C Recommendation, Jan. 2021.",
        "G. J. Myers, C. Sandler, and T. Badgett, The Art of Software Testing, 3rd ed. Hoboken, NJ, USA: John Wiley & Sons, 2011.",
        "G. J. Myers, C. Sandler, and T. Badgett, The Art of Software Testing, 3rd ed. Hoboken, NJ, USA: Wiley, 2011.",
    ]
    return B, refs


# ------------------------------------------------------------------
# Figures, drawn as bordered tables (rows of cells). Each row is a list of
# (text, span) cells.
# ------------------------------------------------------------------
FIGS = {
    "er": [
        [("room_types (PK type_id) | type_name, is_isolation_unit, has_aircon, has_tv, has_private_bathroom, bed_capacity", 2)],
        [("1 room type has N rooms", 2)],
        [("rooms (PK room_id, FK type_id) | room_number, current_occupancy, status", 2)],
        [("1 room has N admissions", 2)],
        [("admissions (PK admission_id, FK patient_id, FK room_id) | admission_date, discharge_date, status", 2)],
        [("1 patient has N admissions", 2)],
        [("patients (PK patient_id) | first_name, last_name, contact_number, medical_case, is_contagious, admission_status, created_at", 2)],
    ],
    "arch": [
        [("CLIENT: Browser (HTML, CSS, JavaScript) | public/ (Express client), docs/ (static demo)", 2)],
        [("HTTP, JSON (fetch /api/*)", 2)],
        [("Node.js + Express (server.js)", 1), ("PHP 8 + PDO (php/index.php, api/index.php)", 1)],
        [("db.js (SQLite driver)", 1), ("php/db.php (PDO sqlite)", 1)],
        [("DATA: SQLite file (schema.sql, hospital.db)", 2)],
        [("Static demo: docs/ on GitHub Pages, data in sessionStorage, no server", 2)],
    ],
    "flow": [
        [("START: POST /api/admissions", 1)],
        [("Names and room_id present? No: 400", 1)],
        [("Room exists? No: 404", 1)],
        [("Room in Maintenance? Yes: 409", 1)],
        [("Occupancy >= bed capacity? Yes: 409 Room is already full", 1)],
        [("Contagious? If yes: isolation unit AND bed capacity = 1? No: 409", 1)],
        [("Insert patient and active admission", 1)],
        [("Update occupancy; status Full if occupancy >= capacity, else Available", 1)],
        [("COMMIT, return 201 with admission_id", 1)],
    ],
}


# ------------------------------------------------------------------
# DOCX writer
# ------------------------------------------------------------------
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
FONT = "Times New Roman"


def rpr(size=20, bold=False, italic=False, caps=False, smallcaps=False):
    s = '<w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s" w:cs="%s"/>' % (FONT, FONT, FONT)
    if bold:
        s += "<w:b/>"
    if italic:
        s += "<w:i/>"
    if caps:
        s += "<w:caps/>"
    if smallcaps:
        s += "<w:smallCaps/>"
    s += '<w:sz w:val="%d"/><w:szCs w:val="%d"/></w:rPr>' % (size, size)
    return s


def run(text, **kw):
    return '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr(**kw), escape(text))


def para(runs, jc="both", before=0, after=0, first=0, keep_next=False, left=0, hanging=0, sect=""):
    ppr = "<w:pPr>"
    if keep_next:
        ppr += "<w:keepNext/>"
    ppr += '<w:spacing w:before="%d" w:after="%d"/>' % (before, after)
    ind = ""
    if first or left or hanging:
        ind = '<w:ind w:left="%d"' % left
        if hanging:
            ind += ' w:hanging="%d"' % hanging
        else:
            ind += ' w:firstLine="%d"' % first
        ind += "/>"
    ppr += ind
    ppr += '<w:jc w:val="%s"/>' % jc
    ppr += sect
    ppr += "</w:pPr>"
    return "<w:p>%s%s</w:p>" % (ppr, "".join(runs) if isinstance(runs, list) else runs)


def cell(text, span=1, width=0, size=16, bold=False, jc="left", shade=False):
    tcpr = "<w:tcPr>"
    if width:
        tcpr += '<w:tcW w:w="%d" w:type="dxa"/>' % width
    if span > 1:
        tcpr += '<w:gridSpan w:val="%d"/>' % span
    if shade:
        tcpr += '<w:shd w:val="clear" w:color="auto" w:fill="E7E6E6"/>'
    tcpr += "</w:tcPr>"
    return "<w:tc>%s%s</w:tc>" % (tcpr, para([run(text, size=size, bold=bold)], jc=jc))


def table(rows, ncols, widths, header=False, size=16, jc="left"):
    """rows: list of list of (text, span). widths: dxa per grid column."""
    b = '<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>' \
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>' \
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>' \
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>' \
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>' \
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    x = '<w:tbl><w:tblPr><w:tblW w:w="%d" w:type="dxa"/><w:jc w:val="center"/>' \
        '<w:tblBorders>%s</w:tblBorders><w:tblLayout w:type="fixed"/>' \
        '<w:tblCellMar><w:left w:w="50" w:type="dxa"/><w:right w:w="50" w:type="dxa"/></w:tblCellMar>' \
        '</w:tblPr><w:tblGrid>' % (sum(widths), b)
    x += "".join('<w:gridCol w:w="%d"/>' % w for w in widths) + "</w:tblGrid>"
    for ri, row in enumerate(rows):
        x += "<w:tr><w:trPr><w:cantSplit/></w:trPr>"
        col = 0
        for text, span in row:
            w = sum(widths[col:col + span])
            x += cell(text, span, w, size=size, bold=(header and ri == 0),
                      jc=("center" if (header and ri == 0) else jc), shade=(header and ri == 0))
            col += span
        x += "</w:tr>"
    return x + "</w:tbl>"


COL_W = 4900  # usable column width in dxa (approx 3.4in)


def sect_pr(cols, cont, footer=True):
    s = "<w:sectPr>"
    if footer:
        s += '<w:footerReference w:type="default" r:id="rId2"/>'
    if cont:
        s += '<w:type w:val="continuous"/>'
    s += '<w:pgSz w:w="12240" w:h="15840"/>'
    s += '<w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080" w:header="720" w:footer="540" w:gutter="0"/>'
    if cols == 2:
        s += '<w:cols w:num="2" w:space="360"/>'
    else:
        s += '<w:cols w:num="1"/>'
    return s + "</w:sectPr>"


def build_document(blocks, refs, rows_header):
    body = []
    # ---- title block (single column)
    body.append(para([run(TITLE, size=48)], jc="center", before=0, after=200))
    n = len(AUTHORS)
    aw = 10080 // n
    arows = ""
    for a in AUTHORS:
        pass
    cells = ""
    for a in AUTHORS:
        ps = para([run(a[0], size=22)], jc="center") + "".join(
            para([run(t, size=18, italic=True)], jc="center") for t in a[1:])
        cells += '<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/></w:tcPr>%s</w:tc>' % (aw, ps)
    body.append('<w:tbl><w:tblPr><w:tblW w:w="%d" w:type="dxa"/><w:tblLayout w:type="fixed"/></w:tblPr>'
                '<w:tblGrid>%s</w:tblGrid><w:tr>%s</w:tr></w:tbl>'
                % (aw * n, "".join('<w:gridCol w:w="%d"/>' % aw for _ in AUTHORS), cells))
    # section break ending the title block
    body.append(para([run("", size=4)], jc="left", after=120, sect=sect_pr(1, False)))

    # ---- body (two columns)
    body.append(para([run("Abstract" + EM.strip(), size=18, bold=True, italic=True), run(ABSTRACT, size=18, bold=True)],
                     before=0, after=100, first=0))
    body.append(para([run("Keywords" + EM, size=18, bold=True, italic=True), run(KEYWORDS, size=18, bold=True, italic=True)],
                     before=0, after=160))
    for blk in blocks:
        kind = blk[0]
        if kind == "h1":
            body.append(para([run(blk[1], size=20, smallcaps=False, caps=False)], jc="center", before=160, after=80,
                             keep_next=True))
        elif kind == "h2":
            body.append(para([run(blk[1], size=20, italic=True)], jc="left", before=100, after=60, keep_next=True))
        elif kind == "p":
            body.append(para([run(blk[1], size=20)], first=200, after=60))
        elif kind == "fig":
            _, label, cap, key = blk
            rows = FIGS[key]
            widths = [COL_W // 2, COL_W - COL_W // 2]
            if key == "flow":
                widths = [COL_W]
                rows = [[(t, 1)] for (t, s) in [r[0] for r in rows]]
            body.append(table(rows, len(widths), widths, size=16, jc="center"))
            body.append(para([run(label + " ", size=16), run(cap, size=16)], jc="center", before=60, after=120))
        elif kind == "table":
            _, label, cap, head, rows = blk
            body.append(para([run(label, size=16, smallcaps=True)], jc="center", before=100, keep_next=True))
            body.append(para([run(cap, size=16, smallcaps=True)], jc="center", after=60, keep_next=True))
            widths = [520, 800, 1000, 1040, 1540]
            allrows = [[(h, 1) for h in head]] + [[(c, 1) for c in r] for r in rows]
            body.append(table(allrows, 5, widths, header=True, size=16, jc="left"))
            body.append(para([run("", size=8)], after=80))
    # references
    body.append(para([run("REFERENCES", size=20)], jc="center", before=160, after=80, keep_next=True))
    for i, r in enumerate(refs, 1):
        body.append(para([run("[%d]\t%s" % (i, r.replace("\"", "\"")), size=16)], jc="both", after=40,
                         left=360, hanging=360))
    xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document %s xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
           '<w:body>%s%s</w:body></w:document>') % (W, "".join(body), sect_pr(2, True))
    return xml


def build_footer():
    fld = ('<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
           '<w:r>%s<w:fldChar w:fldCharType="begin"/></w:r>'
           '<w:r>%s<w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
           '<w:r>%s<w:fldChar w:fldCharType="separate"/></w:r>'
           '<w:r>%s<w:t>1</w:t></w:r>'
           '<w:r>%s<w:fldChar w:fldCharType="end"/></w:r></w:p>') % ((rpr(size=18),) * 5)
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr %s>%s</w:ftr>' % (W, fld)


STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles %s>'
          '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s" w:cs="%s"/>'
          '<w:sz w:val="20"/><w:szCs w:val="20"/><w:lang w:val="en-US"/></w:rPr></w:rPrDefault>'
          '<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault>'
          '</w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
          '</w:styles>') % (W, FONT, FONT, FONT)

CONTENT_TYPES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                 '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                 '<Default Extension="xml" ContentType="application/xml"/>'
                 '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                 '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                 '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
                 '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
                 '</Types>')

ROOT_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
             '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
             '</Relationships>')

DOC_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
            '</Relationships>')

CORE = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:title>%s</dc:title><dc:creator>Occuaid team</dc:creator></cp:coreProperties>') % escape(TITLE)


def write_docx(blocks, refs):
    doc = build_document(blocks, refs, None)
    with zipfile.ZipFile(OUT_DOCX, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in (
            ("[Content_Types].xml", CONTENT_TYPES),
            ("_rels/.rels", ROOT_RELS),
            ("word/document.xml", doc),
            ("word/styles.xml", STYLES),
            ("word/footer1.xml", build_footer()),
            ("word/_rels/document.xml.rels", DOC_RELS),
            ("docProps/core.xml", CORE),
        ):
            zi = zipfile.ZipInfo(name, date_time=(2024, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data.encode("utf-8"))


# ------------------------------------------------------------------
# Markdown source
# ------------------------------------------------------------------
def write_md(blocks, refs):
    L = ["# " + TITLE, ""]
    for a in AUTHORS:
        L.append(", ".join(a) + "  ")
    L += ["", "**Abstract" + EM + "** " + ABSTRACT, "", "**Keywords" + EM + "** " + KEYWORDS, ""]
    for blk in blocks:
        k = blk[0]
        if k == "h1":
            L += ["## " + blk[1], ""]
        elif k == "h2":
            L += ["### " + blk[1], ""]
        elif k == "p":
            L += [blk[1], ""]
        elif k == "fig":
            _, label, cap, key = blk
            L += ["```", *[" | ".join(t for t, _ in r) for r in FIGS[key]], "```", "*%s %s*" % (label, cap), ""]
        elif k == "table":
            _, label, cap, head, rows = blk
            L += ["**%s: %s**" % (label, cap), "", "| " + " | ".join(head) + " |",
                  "|" + "---|" * len(head)]
            L += ["| " + " | ".join(r) + " |" for r in rows] + [""]
    L += ["## REFERENCES", ""]
    L += ["[%d] %s  " % (i, r) for i, r in enumerate(refs, 1)]
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def main():
    res = load_results()
    blocks, refs = build_content(res)
    write_docx(blocks, refs)
    write_md(blocks, refs)
    print("wrote", OUT_DOCX, "and", OUT_MD)


if __name__ == "__main__":
    main()
