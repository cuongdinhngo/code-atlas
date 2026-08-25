<?php

declare(strict_types=1);

namespace App\Service;

use App\Http\Front;

class Bridge
{
    public function relay(Front $front): int
    {
        return $front->serve();
    }
}
