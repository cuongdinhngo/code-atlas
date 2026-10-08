<?php

namespace Parity;

class User
{
}

class Repo
{
    public const TIMEOUT = 30;

    private User $owner;

    private static int $count = 0;

    public function find(User $u): User
    {
        return $u;
    }

    private static function tag(string $name, int $n): string
    {
        return $name;
    }

    public function run(): string
    {
        self::$count = self::$count + 1;

        return self::tag("name", 3);
    }
}
