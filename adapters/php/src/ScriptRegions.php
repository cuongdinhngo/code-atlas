<?php

declare(strict_types=1);

namespace CodeAtlas\Php;

/**
 * The `<script>` elements of a file's inline HTML, as byte spans another adapter can read (399).
 *
 * Read from the tokens, never a regex over the file: only `T_INLINE_HTML` is HTML, so a `<script`
 * inside a PHP string is no element, and PHP inside a script is a hole the spans step over.
 * Which scripts count is the HTML standard's rule, never a framework's.
 */
final class ScriptRegions
{
    /** The MIME Sniffing standard's JavaScript MIME type essences. */
    private const JS_TYPES = [
        'application/ecmascript', 'application/javascript', 'application/x-ecmascript',
        'application/x-javascript', 'text/ecmascript', 'text/javascript', 'text/javascript1.0',
        'text/javascript1.1', 'text/javascript1.2', 'text/javascript1.3', 'text/javascript1.4',
        'text/javascript1.5', 'text/jscript', 'text/livescript', 'text/x-ecmascript',
        'text/x-javascript',
    ];
    /** Elements whose content the HTML parser reads as text, so a `<script` inside is no tag. */
    private const RAW_TEXT = ['style', 'textarea', 'title'];
    private const CLASSIC = '.js';
    private const MODULE = '.mjs';

    /**
     * @return list<array{suffix: string, spans: list<array{int, int}>}> one entry per suffix, in order
     */
    public static function find(string $source): array
    {
        if (stripos($source, '<script') === false) {
            return [];
        }
        $html = [];
        foreach (\PhpToken::tokenize($source) as $token) {
            if ($token->id === T_INLINE_HTML) {
                $html[] = [$token->pos, $token->text];
            } else {
                $html[] = null;  // a PHP hole: it ends no tag and joins no span
            }
        }

        $found = [];
        $state = 'text';
        $tag = '';
        $suffix = null;
        foreach ($html as $piece) {
            if ($piece === null) {
                if ($state === 'tag') {
                    $tag .= ' ';
                }
                continue;
            }
            [$base, $text] = $piece;
            $at = 0;
            $length = strlen($text);
            while ($at < $length) {
                if ($state === 'comment') {
                    $end = strpos($text, '-->', $at);
                    if ($end === false) {
                        break;
                    }
                    $state = 'text';
                    $at = $end + 3;
                } elseif (str_starts_with($state, 'raw:')) {
                    $end = self::endTag($text, $at, substr($state, 4));
                    if ($end === null) {
                        break;
                    }
                    $state = 'text';
                    $at = $end + 2;
                } elseif ($state === 'tag') {
                    $close = self::tagEnd($text, $at, $tag);
                    if ($close === null) {
                        $tag .= substr($text, $at);
                        break;
                    }
                    $tag .= substr($text, $at, $close - $at);
                    $suffix = self::suffixOf($tag);
                    $state = 'script';
                    $at = $close + 1;
                } elseif ($state === 'script') {
                    $end = self::endTag($text, $at, 'script');
                    $stop = $end ?? $length;
                    if ($suffix !== null && $stop > $at) {
                        $found[$suffix][] = [$base + $at, $base + $stop];
                    }
                    if ($end === null) {
                        break;
                    }
                    $state = 'text';
                    $at = $end + 8;
                } else {
                    $next = self::startOf($text, $at);
                    if ($next === null) {
                        break;
                    }
                    [$kind, $offset] = $next;
                    if ($kind === 'comment') {
                        $state = 'comment';
                        $at = $offset + 4;
                    } elseif ($kind === 'script') {
                        $state = 'tag';
                        $tag = '';
                        $at = $offset + 7;
                    } else {
                        $state = 'raw:' . $kind;
                        $at = $offset + strlen($kind) + 1;
                    }
                }
            }
        }

        $regions = [];
        foreach ($found as $name => $spans) {
            $code = implode('', array_map(static fn (array $s): string => substr($source, $s[0], $s[1] - $s[0]), $spans));
            if (trim($code) !== '') {
                $regions[] = ['suffix' => (string) $name, 'spans' => $spans];
            }
        }

        return $regions;
    }

    /**
     * The first `<!--`, `<script` or raw-text start tag at or after `$at`.
     *
     * @return array{string, int}|null the kind (`comment`, `script` or an element name) and offset
     */
    private static function startOf(string $text, int $at): ?array
    {
        $first = null;
        $comment = strpos($text, '<!--', $at);
        if ($comment !== false) {
            $first = ['comment', $comment];
        }
        foreach (['script', ...self::RAW_TEXT] as $name) {
            $open = self::openTag($text, $at, $name);
            if ($open !== null && ($first === null || $open < $first[1])) {
                $first = [$name, $open];
            }
        }

        return $first;
    }

    /** Where a `<name` start tag begins (followed by whitespace, `/` or `>`), or null. */
    private static function openTag(string $text, int $at, string $name): ?int
    {
        $width = strlen($name) + 1;
        while (($open = stripos($text, '<' . $name, $at)) !== false) {
            $after = $text[$open + $width] ?? '';
            if ($after === '' || $after === '>' || $after === '/' || ctype_space($after)) {
                return $open;
            }
            $at = $open + $width;
        }

        return null;
    }

    /** The `>` that closes a start tag, outside a quoted attribute value; null when this piece holds none. */
    private static function tagEnd(string $text, int $at, string $sofar): ?int
    {
        $quote = self::openQuote($sofar);
        for ($i = $at, $n = strlen($text); $i < $n; $i++) {
            $char = $text[$i];
            if ($quote !== null) {
                $quote = $char === $quote ? null : $quote;
            } elseif ($char === '"' || $char === "'") {
                $quote = $char;
            } elseif ($char === '>') {
                return $i;
            }
        }

        return null;
    }

    /** The quote a start tag read so far leaves open, if any. */
    private static function openQuote(string $tag): ?string
    {
        $quote = null;
        for ($i = 0, $n = strlen($tag); $i < $n; $i++) {
            $char = $tag[$i];
            if ($quote !== null) {
                $quote = $char === $quote ? null : $quote;
            } elseif ($char === '"' || $char === "'") {
                $quote = $char;
            }
        }

        return $quote;
    }

    /** Where `</name` ends the element (followed by whitespace, `/` or `>`), or null. */
    private static function endTag(string $text, int $at, string $name): ?int
    {
        $width = strlen($name) + 2;
        while (($end = stripos($text, '</' . $name, $at)) !== false) {
            $after = $text[$end + $width] ?? '';
            if ($after === '' || $after === '>' || $after === '/' || ctype_space($after)) {
                return $end;
            }
            $at = $end + $width;
        }

        return null;
    }

    /** The suffix a start tag's script is read as, or null for a data block or an external script. */
    private static function suffixOf(string $attributes): ?string
    {
        preg_match_all('/([^\s=\/>"\']+)(?:\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+))?/', $attributes, $matches, PREG_SET_ORDER);
        $attrs = [];
        foreach ($matches as $match) {
            $name = strtolower($match[1]);
            if (!array_key_exists($name, $attrs)) {
                $attrs[$name] = trim($match[2] ?? '', "\"'");
            }
        }
        if (array_key_exists('src', $attrs)) {
            return null;  // the content of an external script is never run
        }
        if (array_key_exists('type', $attrs)) {
            $type = strtolower(trim($attrs['type']));
        } elseif (($attrs['language'] ?? '') !== '') {
            $type = 'text/' . strtolower(trim($attrs['language']));
        } else {
            return self::CLASSIC;
        }
        if ($type === 'module') {
            return self::MODULE;
        }
        $essence = trim(explode(';', $type)[0]);

        return $type === '' || in_array($essence, self::JS_TYPES, true) ? self::CLASSIC : null;
    }
}
