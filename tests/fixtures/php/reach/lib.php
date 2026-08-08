<?php
declare(strict_types=1);
namespace Lib;
class Helper {
    public function go(): void {
        (new Child())->ping();
        (new Impl())->x();
    }
}
class Child extends Helper {
    public function ping(): void {}
}
interface IFace { public function x(): void; }
class Impl implements IFace {
    public function x(): void {}
}
class Service {
    public function run(): void {}
}
class Maybe {
    public function maybe(): void {}
}
