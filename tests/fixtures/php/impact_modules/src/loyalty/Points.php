<?php
declare(strict_types=1);
namespace Fx\Loyalty;

use Fx\Billing\Invoice;

class Points
{
    public function award(Invoice $invoice): int
    {
        return $invoice->total();
    }
}
