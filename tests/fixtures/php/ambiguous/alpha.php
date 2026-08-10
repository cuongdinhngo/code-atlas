<?php

declare(strict_types=1);

function getActiveStatus(): string
{
    return 'alpha';
}

function callerAus(): string
{
    return getActiveStatus();
}
