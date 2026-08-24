<?php
declare(strict_types=1);
namespace Fx;

use Fx\Billing\Invoice;

/** Outside every module directory: the rollup must say so, never invent a home for it. */
class Bootstrap
{
    public function run(Invoice $invoice): int
    {
        return $invoice->total();
    }
}
