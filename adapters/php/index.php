<?php

declare(strict_types=1);

use CodeAtlas\Php\Visitor;
use PhpParser\NodeTraverser;
use PhpParser\NodeVisitor\NameResolver;
use PhpParser\ParserFactory;

$autoload = __DIR__ . '/vendor/autoload.php';
if (!is_file($autoload)) {
    // A missing runtime is a config error, so it fails loud and never as a parse result (R5.3).
    fwrite(STDERR, "code-atlas php adapter: run `composer install` in " . __DIR__ . "\n");
    exit(2);
}
require $autoload;

$arguments = array_slice($argv, 1);
if (count($arguments) !== 2 || $arguments[0] !== '--file') {
    fwrite(STDERR, "usage: php index.php --file <path>\n");
    exit(2);
}

$path = $arguments[1];
$source = @file_get_contents($path);
if ($source === false) {
    echo json_encode(['path' => $path, 'ok' => false, 'error' => 'cannot read the file']), "\n";
    exit(0);
}

$parser = (new ParserFactory())->createForNewestSupportedVersion();
try {
    $statements = $parser->parse($source);
    $traverser = new NodeTraverser();
    $traverser->addVisitor(new NameResolver());
    $traverser->addVisitor($visitor = new Visitor($path, substr_count($source, "\n") + 1));
    $traverser->traverse($statements ?? []);
    $result = [
        'path' => $path,
        'ok' => true,
        'nodes' => $visitor->nodes,
        'edges' => $visitor->edges,
    ];
} catch (Throwable $error) {
    // A bad source file fails softly, one file at a time (R5.1). Collecting errors is task 007.
    $result = ['path' => $path, 'ok' => false, 'error' => $error->getMessage()];
}

$line = json_encode($result, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
if ($line === false) {
    // Undecodable bytes are never repaired into mojibake — that would store silently wrong rows.
    $line = json_encode(['path' => $path, 'ok' => false, 'error' => 'result is not encodable as UTF-8']);
}
echo $line, "\n";
