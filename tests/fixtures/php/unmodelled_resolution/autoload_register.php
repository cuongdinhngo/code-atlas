<?php
declare(strict_types=1);

spl_autoload_register(static function (string $class): void {
    // Language-standard autoload registration — no include edge for loaded classes (279).
});

class AutoloadProbe
{
    public function ping(): void
    {
    }
}
