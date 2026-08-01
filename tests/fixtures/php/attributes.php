<?php

declare(strict_types=1);

namespace App\Attributes;

#[Marker('fn')]
function tagged(): void
{
}

#[Marker('class')]
final class Tagged
{
    #[Marker('const')]
    public const FLAG = 'x';

    #[Marker('prop')]
    public int $field = 0;

    public function __construct(#[Marker('promoted')] private int $id)
    {
    }

    #[Marker('method')]
    public function run(): void
    {
        $closure = #[Marker('closure')] function (): void {};
        $arrow = #[Marker('arrow')] fn (): int => 1;
        $anon = new #[Marker('anon')] class {};
    }
}

enum Flag
{
    #[Marker('case')]
    case On;
}
