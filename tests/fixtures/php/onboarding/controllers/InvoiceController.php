<?php

declare(strict_types=1);

namespace Shop\Controllers;

require_once '../services/InvoiceService.php';
require_once '../views/invoice_page.php';

use Shop\Services\InvoiceService;

class InvoiceController
{
    public function index(InvoiceService $service): int
    {
        return count($service->recent());
    }
}
