<?php

namespace Parity;

class User
{
}

class Repo
{
    public const TIMEOUT = 30;

    private User $owner;

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
        return self::tag("name", 3);
    }
}
