<?php
declare(strict_types=1);

namespace App\Enums;

enum Suit: string
{
    case Hearts = 'H';
    case Spades = 'S';
}

enum Pure
{
    case Only;
}
