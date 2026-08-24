<?php
declare(strict_types=1);
namespace Fx\Shipping;

use Fx\Billing\Invoice;

class Rate
{
    public function quote(Invoice $invoice): int
    {
        return $invoice->total();
    }
}
