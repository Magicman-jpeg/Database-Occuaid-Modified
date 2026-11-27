<?php
// SQLite connection for the Occuaid PHP backend (PDO).
// Uses ../hospital.db by default; override with the OCCUAID_DB env var.

function occuaid_db(): PDO
{
    static $pdo = null;
    if ($pdo !== null) {
        return $pdo;
    }

    $path = getenv('OCCUAID_DB') ?: __DIR__ . '/../hospital.db';
    $pdo = new PDO('sqlite:' . $path);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
    $pdo->exec('PRAGMA foreign_keys = ON');

    $exists = $pdo->query(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'room_types'"
    )->fetch();
    if (!$exists) {
        $pdo->exec(file_get_contents(__DIR__ . '/../schema.sql'));
    }
    return $pdo;
}
