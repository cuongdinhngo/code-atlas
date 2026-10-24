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
        'select' => 'READS',
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

    /** An unqualified SELECT source must be followed by a clause, or end a closed literal (390). */
    private const AFTER_SOURCE =
        '/\A\s*(?:(?:where|join|inner|left|right|full|cross|order|group|having|union|with)\b|;)/i';

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
        $head = '/\A(\s*)(insert\s+into|update|merge\s+into|delete\s+from|exec(?:ute)?|select)\s+/i';
        if (preg_match($head, $text, $m) !== 1) {
            return null;
        }
        $verb = strtolower(substr($m[2], 0, (int) strcspn($m[2], " \t\r\n")));
        $verb = str_starts_with($verb, 'exec') ? 'exec' : $verb;
        $name = '/\G' . self::NAME_PART . '(?:\s*\.\s*' . self::NAME_PART . ')*/';
        $start = strlen($m[0]);
        if ($verb === 'select') {
            return self::readSelect($text, $start, $closed, $name, strlen($m[1]));
        }
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
            // A dotted target reaches no method through the bare-name fallback (204); a module
            // whose own qname is `dbo.<name>` still matches exactly, as the qualified form always has.
            array_unshift($parts, self::DEFAULT_SCHEMA);
        }

        return ['kind' => self::KINDS[$verb], 'target' => implode('.', $parts), 'offset' => strlen($m[1])];
    }

    /**
     * The table a SELECT reads: the first FROM's name, never a temp table or a derived one (390).
     *
     * @return array{kind: string, target: string, offset: int}|null
     */
    private static function readSelect(
        string $text,
        int $start,
        bool $closed,
        string $name,
        int $offset,
    ): ?array {
        $at = null;
        preg_match_all('/\bfrom\s+/i', $text, $froms, PREG_OFFSET_CAPTURE, $start);
        foreach ($froms[0] as [$word, $pos]) {
            if (self::topLevel($text, $start, $pos)) {
                $at = $pos + strlen($word);
                break;
            }
        }
        if ($at === null || preg_match($name, $text, $n, 0, $at) !== 1) {
            return null;
        }
        $parts = self::parts($n[0]);
        if (count($parts) === 1 && !self::sourceEnds($text, $at + strlen($n[0]), $closed)) {
            return null;
        }

        return ['kind' => self::KINDS['select'], 'target' => implode('.', $parts), 'offset' => $offset];
    }

    /** A clause follows the unqualified source, after an optional alias, or a closed literal ends. */
    private static function sourceEnds(string $text, int $at, bool $closed): bool
    {
        $rest = substr($text, $at);
        if (preg_match(self::AFTER_SOURCE, $rest) === 1 || ($closed && trim($rest) === '')) {
            return true;
        }
        // `FROM users u WHERE` / `FROM users AS u WHERE`: an alias still needs the clause after it.
        if (preg_match('/\G\s+(?:as\s+)?' . self::NAME_PART . '/i', $text, $alias, 0, $at) !== 1) {
            return false;
        }

        return preg_match(self::AFTER_SOURCE, substr($text, $at + strlen($alias[0]))) === 1;
    }

    /** Is ``$end`` outside every parenthesis and quoted string opened since ``$start``? */
    private static function topLevel(string $text, int $start, int $end): bool
    {
        $depth = 0;
        $quoted = false;
        foreach (str_split(substr($text, $start, $end - $start)) as $char) {
            if ($char === "'") {
                $quoted = !$quoted;
            } elseif (!$quoted && $char === '(') {
                ++$depth;
            } elseif (!$quoted && $char === ')') {
                --$depth;
            }
        }

        return $depth === 0 && !$quoted;
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

    /**
     * Words a SELECT uses that never name a column of its source (410): T-SQL keywords, table hints
     * and date parts. A delimited `[Status]` is a name however it is spelled, so only bare words count.
     */
    private const NOT_A_COLUMN = 'select from where and or not null is in like between as on join'
        . ' inner left right full outer cross apply order by group having union all distinct top'
        . ' percent ties case when then else end asc desc exists with nolock readuncommitted holdlock'
        . ' updlock rowlock readpast offset fetch next first rows row only into values set insert'
        . ' update delete merge using matched output declare begin return returns if while go create'
        . ' alter view procedure proc function table trigger for after instead of over partition'
        . ' escape collate pivot unpivot xml path json auto except intersect default any some'
        . ' current_timestamp current_user session_user system_user identity day month year hour'
        . ' minute second millisecond week weekday quarter dayofyear dd mm yy yyyy hh mi ss ms wk dw'
        . ' qq dy';

    private const COLUMN_PART = '(?:\[(?:[^\]]|\]\])+\]|"(?:[^"]|"")+"|[A-Za-z_@#][\w@#$]*)';

    /**
     * The columns a SELECT literal reads of its first FROM's table, first seen, once each (410).
     *
     * ``alias.col`` / ``table.col`` always; a bare name only when that table is the string's one
     * source, never a keyword, call, alias, parameter, temp or the source's own name. A ``*`` on
     * the table gives none: which columns it reads is not known.
     *
     * @return list<string>
     */
    public static function columns(string $text, bool $closed): array
    {
        $found = self::read($text, $closed);
        if ($found === null || $found['kind'] !== self::KINDS['select']) {
            return [];
        }
        $target = $found['target'];
        $masked = (string) preg_replace_callback(
            "/N?'(?:[^']|'')*'?/i",
            static fn (array $m): string => str_repeat(' ', strlen($m[0])),
            $text,
        );
        $head = '/\A\s*select\s+/i';
        if (preg_match($head, $masked, $h) !== 1) {
            return [];
        }
        $start = strlen($h[0]);
        $at = null;
        preg_match_all('/\bfrom\s+/i', $masked, $froms, PREG_OFFSET_CAPTURE, $start);
        foreach ($froms[0] as [$word, $pos]) {
            if (self::topLevel($masked, $start, $pos)) {
                $at = $pos + strlen($word);
                break;
            }
        }
        $name = '/\G' . self::NAME_PART . '(?:\s*\.\s*' . self::NAME_PART . ')*/';
        if ($at === null || preg_match($name, $masked, $n, 0, $at) !== 1) {
            return [];
        }
        $words = self::words();
        $parts = explode('.', $target);
        $names = [strtolower($target) => true, strtolower((string) end($parts)) => true];
        $after = $at + strlen($n[0]);
        if (preg_match('/\G\s+(?:as\s+)?' . self::NAME_PART . '/i', $masked, $alias, 0, $after) === 1) {
            $tokens = self::tokens($alias[0], self::NAME_PART);
            $token = (string) end($tokens);
            $word = self::unquote($token);
            if (in_array($token[0], ['[', '"'], true) || !isset($words[strtolower($word)])) {
                $names[strtolower($word)] = true;
                $after += strlen($alias[0]);
            }
        }
        if (self::stars($masked, $names)) {
            return [];
        }
        $single = preg_match('/\bjoin\b|\bapply\b/i', $masked) !== 1
            && preg_match_all('/\bfrom\s+/i', $masked) === 1
            && !str_starts_with(ltrim(substr($masked, $after)), ',');
        $chain = '/' . self::COLUMN_PART . '(?:\s*\.\s*(?:' . self::COLUMN_PART . '|\*))*/';
        preg_match_all($chain, $masked, $all, PREG_OFFSET_CAPTURE, $start);
        $out = [];
        $seen = [];
        foreach ($all[0] as [$match, $pos]) {
            $before = rtrim(substr($masked, 0, $pos));
            if ($before !== '' && str_contains('.:%${', substr($before, -1))) {
                continue;
            }
            $chainParts = array_map(self::unquote(...), self::dotted($match));
            $column = (string) end($chainParts);
            if (count($chainParts) > 1) {
                $qualifier = strtolower(implode('.', array_slice($chainParts, 0, -1)));
                if (!isset($names[$qualifier]) || $column === '*') {
                    continue;
                }
            } elseif (!$single || !self::bareColumn($match, $pos, $masked, $column, $names, $words)) {
                continue;
            }
            if (!isset($seen[strtolower($column)])) {
                $seen[strtolower($column)] = true;
                $out[] = $column;
            }
        }

        return $out;
    }

    /**
     * A bare name that can only be a column: no keyword, call, alias, parameter, temp, source.
     *
     * @param array<string, true> $names
     * @param array<string, true> $words
     */
    private static function bareColumn(
        string $match,
        int $pos,
        string $masked,
        string $column,
        array $names,
        array $words,
    ): bool {
        $lower = strtolower($column);
        if (in_array($column[0], ['@', '#'], true) || isset($names[$lower])) {
            return false;
        }
        if (!in_array($match[0], ['[', '"'], true) && isset($words[$lower])) {
            return false;
        }
        if (str_starts_with(ltrim(substr($masked, $pos + strlen($match))), '(')) {
            return false;
        }

        return preg_match('/\bas\z/i', rtrim(substr($masked, 0, $pos))) !== 1;
    }

    /**
     * Does the select list read the source with ``*`` — bare, or ``t.*`` naming it?
     *
     * @param array<string, true> $names
     */
    private static function stars(string $masked, array $names): bool
    {
        $bare = '/(?:\bselect\s+(?:distinct\s+)?(?:top\s*\(?\s*\d+\s*\)?\s*(?:percent\s+)?)?|,\s*)\*/i';
        if (preg_match($bare, $masked) === 1) {
            return true;
        }
        $dotted = '/(' . self::COLUMN_PART . '(?:\s*\.\s*' . self::COLUMN_PART . ')*)\s*\.\s*\*/';
        preg_match_all($dotted, $masked, $all);
        foreach ($all[1] as $qualifier) {
            $key = implode('.', array_map(self::unquote(...), self::dotted($qualifier)));
            if (isset($names[strtolower($key)])) {
                return true;
            }
        }

        return false;
    }

    /** @return array<string, true> */
    private static function words(): array
    {
        $words = [];
        foreach (explode(' ', self::NOT_A_COLUMN) as $word) {
            $words[$word] = true;
        }

        return $words;
    }

    /** @return list<string> a dotted chain's parts, delimiters kept */
    private static function dotted(string $chain): array
    {
        $parts = preg_split('/\s*\.\s*/', $chain);

        return $parts === false ? [] : $parts;
    }

    /** @return list<string> */
    private static function tokens(string $text, string $part): array
    {
        preg_match_all('/' . $part . '/', $text, $all);

        return $all[0];
    }

    private static function unquote(string $part): string
    {
        if ($part !== '' && $part[0] === '[') {
            return str_replace(']]', ']', substr($part, 1, -1));
        }
        if ($part !== '' && $part[0] === '"') {
            return str_replace('""', '"', substr($part, 1, -1));
        }

        return $part;
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
