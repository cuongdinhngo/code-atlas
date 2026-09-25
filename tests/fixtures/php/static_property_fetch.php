<?php

namespace App;

class Cfg { public static $flag = false; public function me() { return self::$flag; } }
class Db
{
    public function init() { if (Cfg::$flag) { return 2; } }
    public function dyn($cls, $n) { return $cls::$flag . Cfg::$$n; }
}
class Use1 { public function f(Cfg $c) { return 1; } }
