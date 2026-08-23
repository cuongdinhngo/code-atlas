<?php

declare(strict_types=1);

namespace Shop\Repositories;

require_once '../lib/Clock.php';
require_once '../models/Invoice.php';

use Shop\Lib\Clock;
use Shop\Models\Invoice;

class InvoiceRepository
{
    public function findRecent(Clock $clock): array
    {
        $clock->now();

        return [new Invoice()];
    }
}
