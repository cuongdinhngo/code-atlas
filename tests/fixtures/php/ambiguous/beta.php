<?php

declare(strict_types=1);

function getActiveStatus(): string
{
    return 'beta';
}

function callerNz(): string
{
    return getActiveStatus();
}
