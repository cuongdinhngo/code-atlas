<?php

declare(strict_types=1);

namespace CodeAtlas\Php;

use PhpParser\Node;

/** The convention anchors every qualified name at the global namespace (CONVENTION §3). */
final class Qname
{
    public const ROOT = '\\';
    public const MEMBER = '::';

    public static function of(Node\Name|string $name): string
    {
        return self::ROOT . ltrim((string) $name, self::ROOT);
    }

    public static function member(string $container, string $member): string
    {
        return $container . self::MEMBER . $member;
    }
}
