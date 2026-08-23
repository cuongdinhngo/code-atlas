<?php

declare(strict_types=1);

namespace Shop\Legacy;

require_once '../lib/Clock.php';

use Shop\Lib\Clock;

class RetiredExporter
{
    public function dump(Clock $clock): int
    {
        return $clock->now();
    }
}
