<?php

declare(strict_types=1);

namespace Shop\Views;

function render_invoice_page(array $rows): string
{
    return (string) count($rows);
}
