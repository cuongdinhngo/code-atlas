<?php
declare(strict_types=1);

namespace App\Dyn;

final class Foo
{
    public static function bar(): void
    {
    }
}

function literals(string $runtimeVar, string $method): void
{
    call_user_func('App\\Dyn\\Foo::bar');
    call_user_func(['App\\Dyn\\Foo', 'bar']);
    Foo::{'bar'}();

    $literal = '\\App\\Dyn\\Foo';
    new $literal();

    new $runtimeVar();
    $obj = new Foo();
    $obj->$method();
}
