<?php

declare(strict_types=1);

namespace Shop\Reports;

require_once '../repositories/InvoiceRepository.php';

use Shop\Lib\Clock;
use Shop\Repositories\InvoiceRepository;

class InvoiceReport
{
    public function render(InvoiceRepository $repo, Clock $clock): int
    {
        $clock->now();

        return count($repo->findRecent($clock));
    }
}
