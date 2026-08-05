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
