<?php

declare(strict_types=1);

namespace App\Domain;

use App\Service\Bridge;

class Model
{
    public function build(Bridge $bridge): int
    {
        return $bridge->relay();
    }
}
