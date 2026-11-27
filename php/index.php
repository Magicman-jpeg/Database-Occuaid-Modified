<?php
// Occuaid REST API, PHP port of server.js. Same endpoints, JSON shapes,
// status codes and error messages. Route /api/* here (see php/router.php).
require __DIR__ . '/db.php';

class HttpError extends Exception
{
    public function __construct(public int $status, string $message)
    {
        parent::__construct($message);
    }
}

function send_json($data, int $status = 200): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
}

function q(PDO $db, string $sql, array $params = []): PDOStatement
{
    $st = $db->prepare($sql);
    $st->execute($params);
    return $st;
}

function transaction(PDO $db, callable $fn)
{
    $db->exec('BEGIN TRANSACTION');
    try {
        $result = $fn();
        $db->exec('COMMIT');
        return $result;
    } catch (Throwable $e) {
        $db->exec('ROLLBACK');
        throw $e;
    }
}

/** Mirror JS Number(): numeric strings/numbers to float, otherwise NaN. */
function js_number($v): float
{
    if (is_int($v) || is_float($v)) return (float)$v;
    if (is_bool($v)) return $v ? 1.0 : 0.0;
    if (is_string($v) && is_numeric(trim($v))) return (float)trim($v);
    if ($v === null || (is_string($v) && trim($v) === '')) return 0.0;
    return NAN;
}

/** Mirror JS truthiness for body values. */
function js_truthy($v): bool
{
    if ($v === null || $v === false || $v === 0 || $v === 0.0 || $v === '') return false;
    if (is_float($v) && is_nan($v)) return false;
    return true;
}

function trimmed($v): string
{
    return is_string($v) ? trim($v) : '';
}

function ensure_int(float $n): int
{
    return is_nan($n) ? 0 : (int)$n;
}

function handle(string $method, string $path): void
{
    $db = occuaid_db();
    $body = [];
    if (in_array($method, ['POST', 'PATCH', 'PUT'], true)) {
        $raw = file_get_contents('php://input');
        $decoded = json_decode($raw === false ? '' : $raw, true);
        $body = is_array($decoded) ? $decoded : [];
    }

    // GET /api/health
    if ($method === 'GET' && $path === '/api/health') {
        q($db, 'SELECT 1')->fetch();
        send_json(['ok' => true]);
        return;
    }

    // GET /api/room-types
    if ($method === 'GET' && $path === '/api/room-types') {
        send_json(q($db, 'SELECT * FROM room_types ORDER BY type_id')->fetchAll());
        return;
    }

    // GET /api/rooms
    if ($method === 'GET' && $path === '/api/rooms') {
        $where = [];
        $params = [];
        if (!empty($_GET['type']))   { $where[] = 'rt.type_name = ?'; $params[] = (string)$_GET['type']; }
        if (!empty($_GET['status'])) { $where[] = 'r.status = ?';     $params[] = (string)$_GET['status']; }
        if (($_GET['aircon'] ?? null) === '1')   $where[] = 'rt.has_aircon = 1';
        if (($_GET['tv'] ?? null) === '1')       $where[] = 'rt.has_tv = 1';
        if (($_GET['bathroom'] ?? null) === '1') $where[] = 'rt.has_private_bathroom = 1';

        $sql = "
            SELECT  r.room_id, r.room_number, r.current_occupancy, r.status,
                    rt.type_id, rt.type_name, rt.is_isolation_unit,
                    rt.has_aircon, rt.has_tv, rt.has_private_bathroom, rt.bed_capacity,
                    (rt.bed_capacity - r.current_occupancy)                          AS beds_available,
                    ROUND(CAST(r.current_occupancy AS REAL) / rt.bed_capacity * 100) AS occupancy_pct
              FROM  rooms r
              JOIN  room_types rt ON rt.type_id = r.type_id
              " . ($where ? 'WHERE ' . implode(' AND ', $where) : '') . "
              ORDER BY  rt.type_name, r.room_number";
        send_json(q($db, $sql, $params)->fetchAll());
        return;
    }

    // GET /api/admissions
    if ($method === 'GET' && $path === '/api/admissions') {
        $activeOnly = ($_GET['active'] ?? null) !== 'false';
        $sql = "
            SELECT  a.admission_id, a.patient_id, a.room_id, a.admission_date,
                    a.discharge_date, a.status,
                    p.first_name, p.last_name, p.contact_number,
                    p.medical_case, p.is_contagious,
                    r.room_number, rt.type_name
              FROM  admissions a
              JOIN  patients    p  ON p.patient_id  = a.patient_id
              JOIN  rooms       r  ON r.room_id     = a.room_id
              JOIN  room_types  rt ON rt.type_id    = r.type_id
              " . ($activeOnly ? "WHERE a.status = 'Active'" : '') . "
              ORDER BY  a.admission_date DESC";
        send_json(q($db, $sql)->fetchAll());
        return;
    }

    // POST /api/admissions
    if ($method === 'POST' && $path === '/api/admissions') {
        $first = trimmed($body['first_name'] ?? null);
        $last  = trimmed($body['last_name'] ?? null);
        if ($first === '' || $last === '') {
            throw new HttpError(400, 'first_name and last_name are required.');
        }
        $roomIdRaw = $body['room_id'] ?? null;
        if (!js_truthy($roomIdRaw)) throw new HttpError(400, 'room_id is required.');

        $contagious = js_truthy($body['is_contagious'] ?? null) ? 1 : 0;
        $contact = trimmed($body['contact_number'] ?? null);
        $case = trimmed($body['medical_case'] ?? null);

        $result = transaction($db, function () use ($db, $roomIdRaw, $contagious, $first, $last, $contact, $case) {
            $room = q($db, "
                SELECT  r.room_id, r.current_occupancy, r.status,
                        rt.bed_capacity, rt.is_isolation_unit, rt.type_name
                  FROM  rooms r
                  JOIN  room_types rt ON rt.type_id = r.type_id
                 WHERE  r.room_id = ?", [ensure_int(js_number($roomIdRaw))])->fetch();

            if (!$room) throw new HttpError(404, 'Room not found.');
            if ($room['status'] === 'Maintenance') {
                throw new HttpError(409, 'Room is under maintenance and cannot accept patients.');
            }
            if ($room['current_occupancy'] >= $room['bed_capacity']) {
                throw new HttpError(409, 'Room is already full.');
            }

            // Contagion rule: isolation unit AND single occupancy.
            if ($contagious === 1) {
                if (!$room['is_isolation_unit']) {
                    throw new HttpError(409,
                        'Contagious patients can only be assigned to Isolation units. ' .
                        '"' . $room['type_name'] . '" is not an isolation room.');
                }
                if ((int)$room['bed_capacity'] !== 1) {
                    throw new HttpError(409,
                        'Contagious patients require a single-occupancy room (bed_capacity = 1). ' .
                        'This room has bed_capacity = ' . $room['bed_capacity'] . '.');
                }
            }

            q($db, "INSERT INTO patients (first_name, last_name, contact_number, medical_case, is_contagious, admission_status)
                    VALUES (?, ?, ?, ?, ?, 'Admitted')",
                [$first, $last, $contact !== '' ? $contact : null, $case !== '' ? $case : null, $contagious]);
            $patientId = (int)$db->lastInsertId();

            q($db, "INSERT INTO admissions (patient_id, room_id, status) VALUES (?, ?, 'Active')",
                [$patientId, $room['room_id']]);
            $admissionId = (int)$db->lastInsertId();

            $newOcc = $room['current_occupancy'] + 1;
            $newStatus = $newOcc >= $room['bed_capacity'] ? 'Full' : 'Available';
            q($db, 'UPDATE rooms SET current_occupancy = ?, status = ? WHERE room_id = ?',
                [$newOcc, $newStatus, $room['room_id']]);

            return [
                'admission_id' => $admissionId,
                'patient_id' => $patientId,
                'room_id' => (int)$room['room_id'],
            ];
        });
        send_json($result, 201);
        return;
    }

    // PATCH /api/admissions/:id/discharge
    if ($method === 'PATCH' && preg_match('#^/api/admissions/([^/]+)/discharge$#', $path, $m)) {
        $admissionId = ensure_int(js_number(urldecode($m[1])));
        if (!$admissionId) throw new HttpError(400, 'Invalid admission id.');

        $result = transaction($db, function () use ($db, $admissionId) {
            $adm = q($db, 'SELECT admission_id, patient_id, status, room_id FROM admissions WHERE admission_id = ?',
                [$admissionId])->fetch();
            if (!$adm) throw new HttpError(404, 'Admission not found.');
            if ($adm['status'] !== 'Active') throw new HttpError(409, 'Admission is not active.');

            q($db, "UPDATE admissions SET status = 'Discharged', discharge_date = datetime('now', 'localtime')
                     WHERE admission_id = ?", [$admissionId]);
            q($db, "UPDATE patients SET admission_status = 'Discharged' WHERE patient_id = ?", [$adm['patient_id']]);

            $room = q($db, "
                SELECT  r.current_occupancy, r.status, rt.bed_capacity
                  FROM  rooms r JOIN room_types rt ON rt.type_id = r.type_id
                 WHERE  r.room_id = ?", [$adm['room_id']])->fetch();
            $newOcc = max($room['current_occupancy'] - 1, 0);
            $newStatus = $room['status'] === 'Maintenance'
                ? 'Maintenance'
                : ($newOcc >= $room['bed_capacity'] ? 'Full' : 'Available');
            q($db, 'UPDATE rooms SET current_occupancy = ?, status = ? WHERE room_id = ?',
                [$newOcc, $newStatus, $adm['room_id']]);

            return ['ok' => true, 'admission_id' => $admissionId];
        });
        send_json($result);
        return;
    }

    // PATCH /api/rooms/:id/status
    if ($method === 'PATCH' && preg_match('#^/api/rooms/([^/]+)/status$#', $path, $m)) {
        $roomId = js_number(urldecode($m[1]));
        $status = $body['status'] ?? null;
        if (!in_array($status, ['Available', 'Maintenance'], true)) {
            throw new HttpError(400, "status must be 'Available' or 'Maintenance'.");
        }
        $room = is_nan($roomId) ? false : q($db, "
            SELECT  r.current_occupancy, r.status, rt.bed_capacity
              FROM  rooms r JOIN room_types rt ON rt.type_id = r.type_id
             WHERE  r.room_id = ?", [(int)$roomId])->fetch();
        if (!$room) throw new HttpError(404, 'Room not found.');

        $next = $status;
        if ($status === 'Available' && $room['current_occupancy'] >= $room['bed_capacity']) {
            $next = 'Full';
        }
        q($db, 'UPDATE rooms SET status = ? WHERE room_id = ?', [$next, (int)$roomId]);
        send_json(['ok' => true, 'status' => $next]);
        return;
    }

    // GET /api/patients
    if ($method === 'GET' && $path === '/api/patients') {
        $status = $_GET['status'] ?? '';
        $where = $status !== '' ? 'WHERE p.admission_status = ?' : '';
        $params = $status !== '' ? [(string)$status] : [];
        $sql = "
            SELECT  p.patient_id, p.first_name, p.last_name, p.contact_number,
                    p.medical_case, p.is_contagious, p.admission_status, p.created_at,
                    a.admission_id, a.room_id, a.admission_date, a.discharge_date,
                    r.room_number, rt.type_name
              FROM  patients p
              LEFT JOIN admissions a ON a.patient_id = p.patient_id AND a.status = 'Active'
              LEFT JOIN rooms r ON r.room_id = a.room_id
              LEFT JOIN room_types rt ON rt.type_id = r.type_id
              $where
              ORDER BY p.patient_id DESC";
        send_json(q($db, $sql, $params)->fetchAll());
        return;
    }

    throw new HttpError(404, 'Not found.');
}

try {
    $path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
    handle($_SERVER['REQUEST_METHOD'] ?? 'GET', rtrim($path, '/') ?: '/');
} catch (HttpError $e) {
    send_json(['error' => $e->getMessage()], $e->status);
} catch (Throwable $e) {
    error_log((string)$e);
    send_json(['error' => $e->getMessage() ?: 'Server error'], 500);
}
