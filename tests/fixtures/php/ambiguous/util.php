<?php

declare(strict_types=1);

function formatDate(): string
{
    return 'd/m/y';
}

// Unique qname: its callers' payload must stay byte-identical to today's (AC2).
function uniqueHelper(): string
{
    return formatDate();
}
