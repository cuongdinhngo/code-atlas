<?php
declare(strict_types=1);

class Greeter
{
    public function hello(): string
    {
        return 'hi';
    }
}

function greet(): string
{
    return (new Greeter())->hello();
}
