<?php
declare(strict_types=1);

namespace App\Closures;

final class Factory
{
    public function make(): void
    {
        $closure = function (int $n): int {
            return $n;
        };
        $arrow = fn (int $n): int => $n;
        $closure(1);
        $arrow(2);
    }
}
