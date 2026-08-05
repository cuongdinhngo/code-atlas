<?php
namespace App;

use Lib\Facades\Cache;

class Runner
{
    public function run(): void
    {
        Cache::get('k');
    }
}

class Hooks
{
    public static function register(): void
    {
        // Framework-shaped indirections the PHP adapter cannot emit as CALLS.
        $string_cb = 'App\\on_save';
        $array_cb = [Controller::class, 'store'];
    }
}

function on_save(): void
{
}

class Controller
{
    public function store(): void
    {
    }
}
