<?php

declare(strict_types=1);

namespace Shop\Jobs;

require_once '../services/InvoiceService.php';

use Shop\Lib\Clock;
use Shop\Repositories\InvoiceRepository;
use Shop\Services\InvoiceService;

class ReminderJob
{
    public function run(InvoiceService $service, InvoiceRepository $repo, Clock $clock): int
    {
        return count($service->recent($repo, $clock));
    }
}
