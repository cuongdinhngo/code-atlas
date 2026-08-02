<?php
declare(strict_types=1);

namespace App\Calls;

final class Service
{
    public static function make(): self
    {
        return new self();
    }

    public function run(): void
    {
        self::make();
        Service::make();
        $this->run();
        $other = new Service();
        $other->run();
    }
}
