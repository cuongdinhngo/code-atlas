<?php

declare(strict_types=1);

namespace App;

class User extends Base
{
    public function save(Repo $repo): void
    {
        $repo->put();
        \App\helper();
    }
}
