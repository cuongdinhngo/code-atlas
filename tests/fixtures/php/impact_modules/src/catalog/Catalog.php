<?php
declare(strict_types=1);
namespace Fx\Catalog;

class Catalog
{
    public function all(): array
    {
        return [];
    }

    /** Untyped receiver: nothing in the file says what $any is, so the edge stays a guess. */
    public function report($any): int
    {
        return $any->total();
    }
}
