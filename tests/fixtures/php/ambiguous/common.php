<?php

declare(strict_types=1);

// Load-order-dependent redefinition: which definition binds is not knowable from the graph (R4).
if (!function_exists('getActiveStatus')) {
    function getActiveStatus(): string
    {
        return 'common';
    }
}

function formatDate(): string
{
    return 'y-m-d';
}

function callerCommon(): string
{
    return getActiveStatus() . formatDate();
}
