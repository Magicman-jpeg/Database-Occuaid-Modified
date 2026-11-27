<?php
// Router for PHP's built-in server. Run from the project root:
//   php -S localhost:8000 php/router.php
// Sends /api/* to php/index.php and serves public/ for everything else.
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/';

if (strpos($path, '/api/') === 0) {
    require __DIR__ . '/index.php';
    return true;
}

$public = realpath(__DIR__ . '/../public');
$file = realpath($public . $path);
if ($file !== false && is_file($file) && strpos($file, $public . DIRECTORY_SEPARATOR) === 0) {
    $types = ['css' => 'text/css', 'js' => 'application/javascript', 'html' => 'text/html'];
    $ext = strtolower(pathinfo($file, PATHINFO_EXTENSION));
    header('Content-Type: ' . ($types[$ext] ?? 'application/octet-stream'));
    readfile($file);
    return true;
}

header('Content-Type: text/html');
readfile($public . '/index.html');
return true;
