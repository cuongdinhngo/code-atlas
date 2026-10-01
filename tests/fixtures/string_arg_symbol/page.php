<?php
namespace App\Pages;

use App\Widgets\Widget;

class Page
{
    public function build(string $dyn): void
    {
        Widget::make('SaveButton');
        Widget::make('App\Widgets\SaveButton');
        Widget::make('Nowhere');
        Widget::make($dyn);
        Widget::make('Save' . $dyn);
        Widget::lookup('Nowhere')->make('SaveButton');
    }
}
