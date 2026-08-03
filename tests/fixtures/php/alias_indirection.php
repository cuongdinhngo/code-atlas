<?php
declare(strict_types=1);

namespace App\Alias;

final class Real
{
    public static function ping(): void
    {
    }
}

function register(): void
{
    class_alias('\\App\\Alias\\Real', '\\App\\Alias\\Aka');
}

function callerAgainstAlias(): void
{
    // Written against the alias — remap must surface this under Real.
    new \App\Alias\Aka();
    \App\Alias\Aka::ping();
}
