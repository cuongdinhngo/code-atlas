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
    call_user_func($runtimeVar);
    Foo::{'bar'}();

    $literal = '\\App\\Dyn\\Foo';
    // Nested closure must not wipe the outer string local (Bugbot).
    $ignore = static function (): void {
    };
    new $literal();

    // Arrow inherits outer string locals by value (finding 9).
    $fn = fn () => new $literal();
    $fn();

    new $runtimeVar();
    $obj = new Foo();
    $obj->$method();
}

function staleBinding(): void
{
    $a = '\\App\\Dyn\\Foo';
    $a .= 'x';
    new $a();

    $b = '\\App\\Dyn\\Foo';
    foreach ([] as $b) {
    }
    new $b();
}

function afterStale(): void
{
    // Must not see staleBinding's $a/$b — leave clears stringLocals (finding 2).
    new $a();
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
