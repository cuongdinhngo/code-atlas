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
     * Reserved words a SELECT uses that never name a column of its source (410), plus the table
     * hints. A date part, `Path` or `Rows` is a common column name, so those are read by place.
     * A delimited `[Status]` is a name however it is spelled, so only bare words count.
     */
    private const NOT_A_COLUMN = 'select from where and or not null is in like between as on join'
        . ' inner left right full outer cross apply order by group having union all distinct top'
        . ' percent case when then else end asc desc exists with nolock readuncommitted holdlock'
        . ' updlock rowlock readpast into values set insert update delete merge using output'
        . ' declare begin return returns if while go create alter view procedure proc function'
        . ' table trigger for of over escape collate pivot unpivot except intersect default any'
        . ' some current_timestamp current_user session_user system_user identity partition';

    private const COLUMN_PART = '(?:\[(?:[^\]]|\]\])+\]|"(?:[^"]|"")+"|[A-Za-z_@#][\w@#$]*)';

    /** Clauses whose words are syntax, not names: paging, `FOR XML/JSON`, `WITH TIES`. */
    private const NOT_NAMES = '/\boffset\s+\S+\s+rows?\b(?:\s+fetch\s+(?:first|next)\s+\S+\s+rows?\s+only\b)?'
        . '|\bfor\s+(?:xml|json)\b[^;]*|\bwith\s+ties\b/i';

    /** The first argument of a date function is a date part, never a column. */
    private const DATE_PART_ARG =
        '/\b(?:dateadd|datediff|datediff_big|datepart|datename|datetrunc|date_bucket)\s*\(\s*\z/i';

    /** A top-N count precedes the select list; any other number or name before a word aliases it. */
    private const TOP_N = '/\btop\s*\(?\s*\d+\s*\)?\s*(?:percent\s*)?(?:with\s+ties\s*)?\z/i';

    /**
     * The columns a SELECT literal reads of its first FROM's table, first seen, once each (410).
     *
     * ``alias.col`` / ``table.col`` always — unless another source in the string shares that
     * name; a bare name only when that table is the string's one source, never a keyword, call,
     * date part, alias, parameter or temp. A ``*`` on the table gives none.
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
        $masked = preg_replace_callback("/N?'(?:[^']|'')*'?/i", self::blank(...), $text) ?? '';
        $masked = preg_replace_callback(self::NOT_NAMES, self::blank(...), $masked) ?? '';
        if (preg_match('/\A\s*select\s+/i', $masked, $h) !== 1) {
            return [];
        }
        $start = strlen($h[0]);
        $at = null;
        preg_match_all('/\bfrom\s+/i', $masked, $froms, PREG_OFFSET_CAPTURE, $start);
        foreach ($froms[0] as [$word, $pos]) {
            if (self::topLevel($masked, $start, $pos)) {
                $at = [$pos, $pos + strlen($word)];
                break;
            }
        }
        $name = '/\G' . self::NAME_PART . '(?:\s*\.\s*' . self::NAME_PART . ')*/';
        if ($at === null || preg_match($name, $masked, $n, 0, $at[1]) !== 1) {
            return [];
        }
        $words = self::words();
        $parts = explode('.', $target);
        $names = [strtolower($target) => true, strtolower(self::last($parts)) => true];
        $after = $at[1] + strlen($n[0]);
        if (preg_match('/\G\s+(?:as\s+)?' . self::NAME_PART . '/i', $masked, $alias, 0, $after) === 1) {
            $tokens = self::tokens($alias[0], self::NAME_PART);
            $token = self::last($tokens);
            if (in_array($token[0], ['[', '"'], true) || !isset($words[strtolower(self::unquote($token))])) {
                $names[strtolower(self::unquote($token))] = true;
                $after += strlen($alias[0]);
            }
        }
        $names = array_diff_key($names, self::shared($masked, $target));
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
            $previous = $pos > 0 ? $masked[$pos - 1] : '';
            if (($before !== '' && str_contains('.:%${', substr($before, -1))) || ctype_digit($previous)) {
                continue;
            }
            $chainParts = array_map(self::unquote(...), self::dotted($match));
            $column = self::last($chainParts);
            if (count($chainParts) > 1) {
                $qualifier = strtolower(implode('.', array_slice($chainParts, 0, -1)));
                if (!isset($names[$qualifier]) || $column === '*') {
                    continue;
                }
            } elseif (!$single || ($pos >= $at[0] && $pos < $after)) {
                continue;
            } elseif (!self::bareColumn($match, substr($masked, $pos + strlen($match)), $before, $words)) {
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
     * Names another FROM / JOIN item also goes by — an alias reused in a subquery binds neither.
     *
     * @return array<string, true>
     */
    private static function shared(string $masked, string $target): array
    {
        $item = '/\b(?:from|join|apply)\s+(' . self::COLUMN_PART . '(?:\s*\.\s*' . self::COLUMN_PART
            . ')*)(?:\s+(?:as\s+)?(' . self::COLUMN_PART . '))?/i';
        preg_match_all($item, $masked, $all, PREG_SET_ORDER);
        $other = [];
        foreach ($all as $m) {
            $table = implode('.', array_map(self::unquote(...), self::dotted($m[1])));
            if (strtolower($table) === strtolower($target)) {
                continue;
            }
            $parts = explode('.', $table);
            $other[strtolower($table)] = true;
            $other[strtolower(self::last($parts))] = true;
            if (($m[2] ?? '') !== '') {
                $other[strtolower(self::unquote($m[2]))] = true;
            }
        }

        return $other;
    }

    /**
     * A bare word that is only a column: no keyword, call, date part, parameter, temp, alias.
     *
     * @param array<string, true> $words
     */
    private static function bareColumn(string $token, string $after, string $before, array $words): bool
    {
        $lower = strtolower(self::unquote($token));
        $delimited = in_array($token[0], ['[', '"'], true);
        if (in_array($token[0], ['@', '#'], true) || (!$delimited && isset($words[$lower]))) {
            return false;
        }
        if (str_starts_with(ltrim($after), '(') || preg_match(self::DATE_PART_ARG, $before) === 1) {
            return false;
        }
        if (preg_match('/\bas\z/i', $before) === 1) {
            return false;
        }
        if (preg_match(self::TOP_N, $before) === 1) {
            return true;
        }
        if (preg_match('/(?:\)|\bend)\z/i', $before) === 1) {
            return false;
        }
        if (preg_match('/(?:\[(?:[^\]]|\]\])+\]|"(?:[^"]|"")+"|[\w@#$]+)\z/', $before, $prior) !== 1) {
            return true;
        }

        return !in_array($prior[0][0], ['[', '"'], true) && !ctype_digit($prior[0][0])
            && isset($words[strtolower($prior[0])]);
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
        foreach (preg_split('/\s+/', self::NOT_A_COLUMN) ?: [] as $word) {
            $words[$word] = true;
        }

        return $words;
    }

    /**
     * A match blanked to spaces of its own length, so every later offset still holds.
     *
     * @param array<array-key, string> $match
     */
    private static function blank(array $match): string
    {
        return str_repeat(' ', strlen($match[0] ?? ''));
    }

    /** @param list<string> $list */
    private static function last(array $list): string
    {
        return $list === [] ? '' : $list[count($list) - 1];
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
