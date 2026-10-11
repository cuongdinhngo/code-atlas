<?php

declare(strict_types=1);

namespace CodeAtlas\Php;

/**
 * Per-symbol body fingerprint (task 384): the tokens on a symbol's lines, comments and layout
 * dropped, so the core can tell a body edit from a comment edit. Opaque — compared for equality only.
 */
final class BodyHash
{
    public const KEY = 'body_hash';
    private const CHARS = 16;
    /** A File or Namespace spans unrelated symbols; a fingerprint of one is no symbol's body. */
    private const UNHASHED = ['File', 'Namespace'];

    /**
     * @param array<int, array<string, mixed>> $nodes
     * @return array<int, array<string, mixed>>
     */
    public static function stamp(string $source, array $nodes): array
    {
        $lines = [];
        $pieces = [];
        foreach (\PhpToken::tokenize($source) as $token) {
            if ($token->is([T_WHITESPACE, T_COMMENT, T_DOC_COMMENT])) {
                continue;
            }
            $lines[] = $token->line;
            // An open or close tag carries the whitespace after it; only the tag is code.
            $pieces[] = $token->is([T_OPEN_TAG, T_CLOSE_TAG]) ? trim($token->text) : $token->text;
        }
        $spans = self::qnameSpans($nodes);
        foreach ($nodes as $index => $node) {
            $qname = $node['qualified_name'] ?? null;
            if (in_array($node['kind'] ?? null, self::UNHASHED, true) || !is_string($qname) || !isset($spans[$qname])) {
                continue;
            }
            [$start, $end] = $spans[$qname];
            $first = self::firstAtOrAfter($lines, $start);
            $span = [];
            for ($at = $first, $count = count($lines); $at < $count && $lines[$at] <= $end; $at++) {
                $span[] = $pieces[$at];
            }
            $extra = is_array($node['extra'] ?? null) ? $node['extra'] : [];
            $extra[self::KEY] = substr(hash('sha256', implode("\0", $span)), 0, self::CHARS);
            $nodes[$index]['extra'] = $extra;
        }

        return $nodes;
    }

    /**
     * One span per qname: a name declared twice in a file is stored once, keep-first, so its
     * fingerprint covers every declaration — an edit to a later one is still seen.
     *
     * @param array<int, array<string, mixed>> $nodes
     * @return array<string, array{int, int}>
     */
    private static function qnameSpans(array $nodes): array
    {
        $spans = [];
        foreach ($nodes as $node) {
            $qname = $node['qualified_name'] ?? null;
            $start = $node['line_start'] ?? null;
            $end = $node['line_end'] ?? $start;
            if (!is_string($qname) || !is_int($start) || !is_int($end)) {
                continue;
            }
            [$low, $high] = $spans[$qname] ?? [$start, $end];
            $spans[$qname] = [min($low, $start), max($high, $end)];
        }

        return $spans;
    }

    /** @param list<int> $lines ascending */
    private static function firstAtOrAfter(array $lines, int $line): int
    {
        $low = 0;
        $high = count($lines);
        while ($low < $high) {
            $mid = intdiv($low + $high, 2);
            if ($lines[$mid] < $line) {
                $low = $mid + 1;
            } else {
                $high = $mid;
            }
        }

        return $low;
    }
}
