<?php
declare(strict_types=1);
namespace Fx\Catalog;

use Fx\Billing\Invoice;

class Product
{
    public function price(Invoice $invoice): int
    {
        return $invoice->total();
    }
}
