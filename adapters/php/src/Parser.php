<?php

declare(strict_types=1);

namespace CodeAtlas\Php;

use PhpParser\ErrorHandler;
use PhpParser\NodeTraverser;
use PhpParser\NodeVisitor\NameResolver;
use PhpParser\ParserFactory;

/**
 * Turns one file path into one contract result.
 *
 * The parser is built once and reused, so server mode pays the boot cost once for a whole repo.
 * Both entry-point modes call this, which is what makes their output identical by construction.
 */
final class Parser
{
    private readonly \PhpParser\Parser $parser;

    public function __construct()
    {
        $this->parser = (new ParserFactory())->createForNewestSupportedVersion();
    }

    /**
     * @return array<string, mixed> `ok:true` with rows, or `ok:false` with an error (R5.1)
     */
    public function parse(string $path, bool $declarationsOnly = false): array
    {
        // Unsuppressed on purpose: the entry point sends diagnostics to stderr, where they belong.
        $source = file_get_contents($path);
        if ($source === false) {
            return self::failure($path, 'cannot read the file');
        }

        // One handler for both passes: a name that cannot be resolved is collected, never thrown.
        $errors = new ErrorHandler\Collecting();
        $members = new MemberTypes();
        $visitor = new Visitor($path, substr_count($source, "\n") + 1, $source, $declarationsOnly, $members);
        try {
            $statements = $this->parser->parse($source, $errors);
            if (!$errors->hasErrors()) {
                // Two traversals, not two visitors on one: a method may call one declared below
                // it, so the member types must be complete before the first edge is emitted.
                $resolve = new NodeTraverser();
                $resolve->addVisitor(new NameResolver($errors));
                if (!$declarationsOnly) {
                    $resolve->addVisitor($members);
                }
                $statements = $resolve->traverse($statements ?? []);

                $emit = new NodeTraverser();
                $emit->addVisitor($visitor);
                $emit->traverse($statements);
            }
        } catch (\Throwable $error) {
            // Backstop: Collecting recovers from every syntax error, so only a non-parse fault lands here.
            return self::failure($path, $error->getMessage());
        }

        if ($errors->hasErrors()) {
            return self::failure($path, self::describe($errors));
        }

        return [
            'path' => $path,
            'ok' => true,
            'nodes' => $visitor->nodes,
            'edges' => $visitor->edges,
        ];
    }

    /** The first collected error plus a count — ordered by the handler, so it is deterministic. */
    private static function describe(ErrorHandler\Collecting $errors): string
    {
        $collected = $errors->getErrors();
        $first = $collected[0]->getMessage();

        return count($collected) === 1 ? $first : $first . ' (+' . (count($collected) - 1) . ' more)';
    }

    /**
     * @return array<string, mixed>
     */
    private static function failure(string $path, string $error): array
    {
        return ['path' => $path, 'ok' => false, 'error' => $error];
    }
}
