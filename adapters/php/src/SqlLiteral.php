<?php

declare(strict_types=1);

namespace CodeAtlas\Php;

/**
 * Recognise the SHAPE of a T-SQL write or EXEC at the start of a string literal (task 335).
 *
 * Statement grammar only — never a wrapper method's name (R2.2) and never a SQL parse (R1.4): a
 * leading keyword, one object name, and the clause T-SQL requires after it. Prose such as
 * "Update settings" or "Insert into cart" lacks that clause and reads as nothing.
 */
final class SqlLiteral
{
    /** Leading keyword → the edge kind it writes. */
    private const KINDS = [
        'insert' => 'WRITES',
        'update' => 'WRITES',
        'merge' => 'WRITES',
        'delete' => 'DELETES',
        'exec' => 'CALLS',
    ];

    /** What must follow the object name for the text to be that statement. */
    private const CLAUSES = [
        'insert' => '/\A\s*(?:\(|values\b|select\b|default\s+values\b|output\b|with\s*\()/i',
        'update' => '/\A\s*(?:set\b|with\s*\()/i',
        'merge' => '/\A\s*(?:with\s*\([^)]*\)\s*)?(?:as\s+)?(?:[A-Za-z_]\w*\s+)?using\b/i',
        'delete' => '/\A\s*(?:where\b|output\b|with\s*\()/i',
        'exec' => '/\A\s+(?:@|\?|:[A-Za-z_]|N?\'|-?\d)/',
    ];

    /** An unqualified procedure resolves in the caller's default schema: `dbo` in T-SQL (386). */
    private const DEFAULT_SCHEMA = 'dbo';

    private const NAME_PART = '(?:\[(?:[^\]]|\]\])+\]|"(?:[^"]|"")+"|[A-Za-z_][\w@#$]*)';

    /**
     * The statement ``$text`` begins, or null.
     *
     * ``$closed`` says the literal is the whole string: its end then terminates the object name.
     * A literal cut short by interpolation or concatenation needs the name ended inside it.
     *
     * @return array{kind: string, target: string, offset: int}|null offset = keyword's byte offset
     */
    public static function read(string $text, bool $closed): ?array
    {
        $head = '/\A(\s*)(insert\s+into|update|merge\s+into|delete\s+from|exec(?:ute)?)\s+/i';
        if (preg_match($head, $text, $m) !== 1) {
            return null;
        }
        $verb = strtolower(substr($m[2], 0, (int) strcspn($m[2], " \t\r\n")));
        $verb = str_starts_with($verb, 'exec') ? 'exec' : $verb;
        $name = '/\G' . self::NAME_PART . '(?:\s*\.\s*' . self::NAME_PART . ')*/';
        $start = strlen($m[0]);
        if ($verb === 'exec' && preg_match('/\G@[A-Za-z_]\w*\s*=\s*/', $text, $rc, 0, $start) === 1) {
            $start += strlen($rc[0]);  // `EXEC @rc = dbo.P …` — the return-code capture form
        }
        if (preg_match($name, $text, $n, 0, $start) !== 1) {
            return null;
        }
        $rest = substr($text, $start + strlen($n[0]));
        $parts = self::parts($n[0]);
        $qualified = count($parts) > 1;
        if (!self::follows($verb, $rest, $qualified, $closed)) {
            return null;
        }
        if ($verb === 'exec' && !$qualified) {
            // A dotted name never matches a same-language method by name, so 204 cannot bind it.
            array_unshift($parts, self::DEFAULT_SCHEMA);
        }

        return ['kind' => self::KINDS[$verb], 'target' => implode('.', $parts), 'offset' => strlen($m[1])];
    }

    /** The clause T-SQL requires after the name, or — DELETE / EXEC on a qualified name — its end. */
    private static function follows(string $verb, string $rest, bool $qualified, bool $closed): bool
    {
        if (preg_match(self::CLAUSES[$verb], $rest) === 1) {
            return true;
        }
        if (!$qualified || ($verb !== 'delete' && $verb !== 'exec')) {
            return false;
        }
        // The statement ends: at the literal's close, or `;`, or only whitespace before an open end.
        return $rest === '' ? $closed : preg_match('/\A\s*(?:;|\z)/', $rest) === 1;
    }

    /** @return list<string> the dotted name's parts, delimiters removed */
    private static function parts(string $name): array
    {
        preg_match_all('/' . self::NAME_PART . '/', $name, $all);
        $parts = [];
        foreach ($all[0] as $part) {
            if ($part[0] === '[') {
                $part = str_replace(']]', ']', substr($part, 1, -1));
            } elseif ($part[0] === '"') {
                $part = str_replace('""', '"', substr($part, 1, -1));
            }
            $parts[] = $part;
        }

        return $parts;
    }
}
