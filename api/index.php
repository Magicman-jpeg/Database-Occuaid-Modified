<?php
// Vercel entry point (vercel-php runtime). Vercel's filesystem is read-only
// except /tmp, so the SQLite file lives in /tmp and is rebuilt from schema.sql
// (schema plus seed data) on a cold start. Data is therefore ephemeral.
if (!getenv('OCCUAID_DB')) {
    putenv('OCCUAID_DB=' . sys_get_temp_dir() . '/occuaid.db');
}

// Rewrites send /api/* here; recover the original path if REQUEST_URI was replaced.
$uriPath = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
if (strpos($uriPath, '/api/index.php') === 0 && isset($_GET['route'])) {
    $_SERVER['REQUEST_URI'] = '/api/' . ltrim((string)$_GET['route'], '/');
    unset($_GET['route']);
}

require __DIR__ . '/../php/index.php';
