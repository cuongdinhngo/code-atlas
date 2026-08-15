<?php

namespace App\Wire;

class Foo
{
    public function run(): void
    {
    }
}

class Bar
{
}

class BaseRouter
{
}

class Router extends BaseRouter
{
    public function dispatch(string $action): void
    {
        $table = ['a' => Foo::class, 'b' => Bar::class];
        $also = Foo::class;
        $own = self::class;
        $late = static::class;
        $up = parent::class;
        $this->$action();
    }
}
