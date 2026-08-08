<?php
declare(strict_types=1);
namespace Entry;
require_once __DIR__ . '/lib.php';
function main(): void {
    $h = new \Lib\Helper();
    $h->go();
    (new \Lib\Service())->run();
}
