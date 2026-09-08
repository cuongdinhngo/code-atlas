<?php
namespace App;

class Db
{
    public function querySP(string $name): void
    {
    }
}

class ChangeLoader
{
    public function loadChange(Db $db): void
    {
        $db->querySP('getUnplannedChange');
    }
}
