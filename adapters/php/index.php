<?php

declare(strict_types=1);

use CodeAtlas\Php\Parser;

// display_errors is host-set and defaults to stdout on many builds, which would put a PHP
// diagnostic between two protocol lines. Move it before anything can be written (§4.1).
ini_set('display_errors', 'stderr');

$autoload = __DIR__ . '/vendor/autoload.php';
if (!is_file($autoload)) {
    // A missing runtime is a config error, so it fails loud and never as a parse result (R5.3).
    fwrite(STDERR, "code-atlas php adapter: run `composer install` in " . __DIR__ . "\n");
    exit(2);
}
require $autoload;

/**
 * Announce the adapter, then answer one request per line until stdin closes (§4.1).
 */
function serve(Parser $parser): void
{
    // capabilities must reach the core as a JSON object; PHP's natural empty array encodes as `[]`.
    emit([
        'name' => 'php',
        'extensions' => ['.php'],
        'capabilities' => new stdClass(),
        'contract_version' => 2,
    ]);

    while (($line = fgets(STDIN)) !== false) {
        $request = json_decode(trim($line), true);
        $path = is_array($request) && is_string($request['path'] ?? null) ? $request['path'] : null;
        if ($path === null) {
            // Never answer an uncorrelatable line: a made-up path would misattribute every reply.
            if (trim($line) !== '') {
                fwrite(STDERR, "code-atlas php adapter: skipped an unusable request line\n");
            }
            continue;
        }
        $declarationsOnly = is_array($request) && ($request['declarations_only'] ?? false) === true;
        emit($parser->parse($path, $declarationsOnly));
    }
}

/**
 * One `\n`-framed JSON line, written straight to the stream so a lock-step reader never blocks.
 *
 * `echo` would go through PHP's output buffer, which a host-set `output_buffering` holds until
 * exit — neither `fflush(STDOUT)` nor `flush()` releases it, and the driver deadlocks (§4.1).
 *
 * @param array<string, mixed> $result
 */
function emit(array $result): void
{
    $line = json_encode($result, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    if ($line === false) {
        // Undecodable bytes are never repaired into mojibake — that would store silently wrong rows.
        $line = json_encode([
            'path' => $result['path'] ?? '',
            'ok' => false,
            'error' => 'result is not encodable as UTF-8',
        ]);
    }
    fwrite(STDOUT, $line . "\n");
}

$arguments = array_slice($argv, 1);
if ($arguments === ['--server']) {
    serve(new Parser());
    exit(0);
}
if (count($arguments) === 2 && $arguments[0] === '--file') {
    emit((new Parser())->parse($arguments[1]));
    exit(0);
}

fwrite(STDERR, "usage: php index.php --file <path> | --server\n");
exit(2);
