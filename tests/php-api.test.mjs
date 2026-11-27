// Rule checks for the Occuaid API. Works against either backend.
// Usage: BASE=http://localhost:8000 node tests/php-api.test.mjs
const BASE = process.env.BASE || 'http://localhost:8000';
let failed = 0;

async function call(method, path, body) {
  const res = await fetch(BASE + path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  return { status: res.status, data };
}

function check(name, ok, detail = '') {
  if (!ok) failed++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  (' + detail + ')' : ''}`);
}

const rooms = (await call('GET', '/api/rooms')).data;
const byNumber = (n) => rooms.find((r) => r.room_number === n);

check('GET /api/health', (await call('GET', '/api/health')).data.ok === true);
check('GET /api/room-types returns 5 types', (await call('GET', '/api/room-types')).data.length === 5);
check('GET /api/rooms returns 9 rooms', rooms.length === 9, `got ${rooms.length}`);

let r = await call('POST', '/api/admissions', { first_name: 'T', last_name: 'A', is_contagious: true, room_id: byNumber('ICU-102').room_id });
check('contagious -> non-isolation room is rejected with 409', r.status === 409, `${r.status} ${r.data.error}`);

r = await call('POST', '/api/admissions', { first_name: 'T', last_name: 'B', is_contagious: true, room_id: byNumber('ISO-502').room_id });
check('contagious -> isolation room is accepted with 201', r.status === 201, `${r.status}`);
const isoAdmission = r.data.admission_id;

r = await call('POST', '/api/admissions', { first_name: 'T', last_name: 'C', is_contagious: true, room_id: byNumber('ISO-502').room_id });
check('admission into a full room is rejected with 409', r.status === 409, `${r.status} ${r.data.error}`);

r = await call('POST', '/api/admissions', { first_name: 'T', last_name: 'D', room_id: byNumber('SEMI-301').room_id });
check('non-contagious -> regular room is accepted with 201', r.status === 201, `${r.status}`);

r = await call('POST', '/api/admissions', { first_name: '', last_name: 'E', room_id: 1 });
check('missing first_name is rejected with 400', r.status === 400, `${r.status}`);

r = await call('POST', '/api/admissions', { first_name: 'T', last_name: 'F', room_id: 9999 });
check('unknown room is rejected with 404', r.status === 404, `${r.status}`);

const iso = (await call('GET', '/api/rooms?type=Isolation')).data;
check('type filter returns only Isolation rooms', iso.length === 2 && iso.every((x) => x.type_name === 'Isolation'));
check('ISO-502 now Full', iso.find((x) => x.room_number === 'ISO-502').status === 'Full');

const ac = (await call('GET', '/api/rooms?aircon=1')).data;
check('aircon filter returns only aircon rooms', ac.length > 0 && ac.every((x) => x.has_aircon === 1), `${ac.length} rooms`);

r = await call('PATCH', `/api/admissions/${isoAdmission}/discharge`);
check('discharge succeeds', r.status === 200 && r.data.ok === true, `${r.status}`);
r = await call('PATCH', `/api/admissions/${isoAdmission}/discharge`);
check('second discharge is rejected with 409', r.status === 409, `${r.status}`);
check('ISO-502 Available after discharge',
  (await call('GET', '/api/rooms?type=Isolation')).data.find((x) => x.room_number === 'ISO-502').status === 'Available');

r = await call('PATCH', `/api/rooms/${byNumber('WARD-402').room_id}/status`, { status: 'Maintenance' });
check('set room to Maintenance', r.status === 200 && r.data.status === 'Maintenance');
r = await call('POST', '/api/admissions', { first_name: 'T', last_name: 'G', room_id: byNumber('WARD-402').room_id });
check('admission into Maintenance room is rejected with 409', r.status === 409, `${r.status}`);
r = await call('PATCH', `/api/rooms/${byNumber('WARD-402').room_id}/status`, { status: 'Bogus' });
check('invalid room status is rejected with 400', r.status === 400);

check('GET /api/admissions active list', Array.isArray((await call('GET', '/api/admissions')).data));
check('GET /api/patients list', (await call('GET', '/api/patients')).data.length >= 5);
check('unknown route returns 404', (await call('GET', '/api/nope')).status === 404);

console.log(failed ? `\n${failed} check(s) FAILED` : '\nAll checks passed');
process.exit(failed ? 1 : 0);
