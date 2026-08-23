<?php

declare(strict_types=1);

namespace Shop\Services;

require_once '../repositories/InvoiceRepository.php';

use Shop\Lib\Clock;
use Shop\Repositories\InvoiceRepository;

class InvoiceService
{
    public function recent(InvoiceRepository $repo, Clock $clock): array
    {
        $clock->now();

        return $repo->findRecent($clock);
    }
}
