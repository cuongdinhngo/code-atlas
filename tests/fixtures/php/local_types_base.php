<?php
declare(strict_types=1);

namespace App\Types;

interface Runner
{
    public function run(): void;
}

trait Logs
{
    public function log(): void
    {
    }
}

abstract class Machine implements Runner
{
    use Logs;

    public function boot(): void
    {
    }
}

final class Depot
{
    public function issue(): Machine
    {
        throw new \LogicException('fixture');
    }

    public function chain(): self
    {
        return $this;
    }

    /** No return type: the chain through it has nothing to walk. */
    public function untyped()
    {
        return $this;
    }

    /** Nullable: one string that names no single type, so the graph holds no node for it. */
    public function maybe(): ?Depot
    {
        return $this;
    }
}

abstract class Shape
{
}

final class Circle extends Shape
{
    public function area(): int
    {
        return 1;
    }
}

final class Square extends Shape
{
    public function area(): int
    {
        return 2;
    }
}
