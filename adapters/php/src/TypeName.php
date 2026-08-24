<?php

declare(strict_types=1);

namespace CodeAtlas\Php;

use PhpParser\Node;

/**
 * One reading of a declared type, shared by everything that records or interprets one.
 *
 * Every declared type, not just class names: a scalar hint dropped to null reads as untyped.
 * NameResolver rewrites a resolvable name to FullyQualified, so a plain Name that survives it is
 * one of the relative class references the language keeps open — `self`, `static`, `parent` —
 * which name a class only once you know where they were written.
 */
final class TypeName
{
    public const SELF = 'self';
    public const STATIC_ = 'static';
    public const PARENT = 'parent';
    public const NULLABLE = '?';
    public const UNION = '|';
    public const INTERSECTION = '&';

    public static function of(?Node $type): ?string
    {
        if ($type instanceof Node\Name\FullyQualified) {
            return Qname::of($type);
        }
        if ($type instanceof Node\Name) {
            // `self` / `static` / `parent`: a class reference the file alone cannot qualify.
            return strtolower($type->toString());
        }
        if ($type instanceof Node\Identifier) {
            return $type->toString();
        }
        if ($type instanceof Node\NullableType) {
            $inner = self::of($type->type);

            return $inner === null ? null : self::NULLABLE . $inner;
        }
        if ($type instanceof Node\UnionType || $type instanceof Node\IntersectionType) {
            $glue = $type instanceof Node\UnionType ? self::UNION : self::INTERSECTION;

            return implode($glue, array_map(self::of(...), $type->types));
        }

        return null;
    }

    /**
     * The class-like alternatives a declared type names, in source order.
     *
     * A union is only evidence when exactly one alternative is a class: `Foo|int` says the
     * receiver is a Foo wherever a method is called on it, `Foo|Bar` does not say which.
     *
     * @return list<string>
     */
    public static function classAlternatives(?string $type): array
    {
        if ($type === null) {
            return [];
        }
        $found = [];
        foreach (preg_split('/[' . self::UNION . self::INTERSECTION . ']/', $type) ?: [] as $part) {
            $part = ltrim($part, self::NULLABLE);
            if ($part === 'null' || $part === '') {
                continue;
            }
            if (str_starts_with($part, Qname::ROOT) || self::isRelative($part)) {
                $found[] = $part;
            }
        }

        return array_values(array_unique($found));
    }

    public static function isRelative(string $type): bool
    {
        return $type === self::SELF || $type === self::STATIC_ || $type === self::PARENT;
    }
}
