<?php
declare(strict_types=1);

/** Compile-stage reject on every PHP runtime; the AST parser may still accept it (280). */
abstract class BrokenAbstract
{
    abstract public function run(): void
    {
        echo "body";
    }
}
