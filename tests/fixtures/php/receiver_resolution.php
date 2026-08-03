<?php
declare(strict_types=1);

namespace App\Recv;

trait HasHook
{
    public function hook(): void
    {
        // Must resolve to the trait, not invent a using class (ticket 029 AC2).
        $this->hook();
    }
}

final class Child extends Base
{
    use HasHook;

    public function go(object $x, string $m): void
    {
        parent::fromBase();
        $this->go($x, $m);
        self::go($x, $m);
        static::go($x, $m);
        $this?->go($x, $m);
        $x->go($x, $m);
        $x->$m($x, $m);
    }
}

final class NestedOuter extends Base
{
    public function nest(): void
    {
        // Anonymous class with no extends — parent:: must NOT inherit NestedOuter's Base.
        $inner = new class {
            public function g(): void
            {
                parent::fromBase();
            }
        };
    }
}
