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
    // Nested closure must not wipe the outer string local (Bugbot).
    $ignore = static function (): void {
    };
    new $literal();

    new $runtimeVar();
    $obj = new Foo();
    $obj->$method();
}

final class SelfString
{
    public static function bar(): void
    {
    }

    public static function viaSelf(): void
    {
        // Must rewrite to SelfString::bar, not \self::bar (Bugbot).
        self::{'bar'}();
    }
}
