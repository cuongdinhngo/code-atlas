<?php

declare(strict_types=1);

namespace App\Grammar;

use App\Other\Helper as Help;
use function strlen as str_len;
use const PHP_EOL as EOL;
use App\Mix\{Thing, function mix_fn, const MIX_CONST};

#[Attr(1)]
final class Sample
{
    use Alpha, Beta {
        Alpha::shared insteadof Beta;
        Beta::shared as private betaShared;
    }

    public string $typed = '';

    public string $hooked {
        get => $this->typed;
    }

    public final const string FLAG = 'x';

    public function __construct(private int $id)
    {
    }

    public function run(mixed $v): void
    {
        $closure = function (int $n): int {
            return $n;
        };
        $arrow = fn (int $n): int => $n;
        $fcc = strlen(...);
        $v?->ping();
        $anon = new class {
            public function x(): void
            {
            }
        };
        $dyn = new $v;
    }
}

enum Suit: string
{
    case Hearts = 'H';
}

enum Pure
{
    case Only;
}

const GLOBAL_FLAG = 1;
