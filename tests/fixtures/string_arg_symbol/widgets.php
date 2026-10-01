<?php
namespace App\Widgets;

class Widget
{
    public static function make(string $name): object
    {
        return new $name();
    }
}

class SaveButton
{
    public function render(): string
    {
        return 'x';
    }
}
