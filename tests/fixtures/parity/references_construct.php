<?php

declare(strict_types=1);

namespace App\Parity;

class User
{
}

class Repo
{
    public User $owner;

    public function get(): User
    {
        return $this->owner;
    }
}
