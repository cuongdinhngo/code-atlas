<?php
declare(strict_types=1);
namespace Fx\Billing;

class Money
{
    public function sum(Invoice $invoice): int
    {
        return $invoice->total();
    }
}
