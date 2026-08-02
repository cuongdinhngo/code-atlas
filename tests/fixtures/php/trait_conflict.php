<?php
declare(strict_types=1);

namespace App\Traits;

trait Alpha
{
    public function shared(): void
    {
    }
}

trait Beta
{
    public function shared(): void
    {
    }
}

final class Host
{
    use Alpha, Beta {
        Alpha::shared insteadof Beta;
        Beta::shared as private betaShared;
    }
}
