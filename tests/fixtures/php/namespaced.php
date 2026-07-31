<?php

declare(strict_types=1);

namespace App\Models;

use App\Contracts\Jsonable as J;

interface Storable
{
    public function store(): bool;
}

trait Timestamps
{
    public function touch(): void
    {
    }
}

enum Status
{
    case Active;
}

class User extends Base implements J, Storable
{
    public const ROLE = 'member';

    private string $name = '';

    public function save(Repo $repo): bool
    {
        return $repo->put($this);
    }

    public function store(): bool
    {
        return true;
    }

    public function rename(string $to, ?int $version = null): void
    {
    }
}

function helper(): User
{
    return new User();
}
