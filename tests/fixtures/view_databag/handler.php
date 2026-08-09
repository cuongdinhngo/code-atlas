<?php
namespace App;

class ViewBag
{
    public function assign(string $key, mixed $value): void
    {
    }

    public function put(mixed $bag, string $key, mixed $value): void
    {
    }

    public function setData(array $data): void
    {
    }
}

class OrderController
{
    public function index(ViewBag $view): void
    {
        $items = [];
        $view->assign('items', $items);
        $view->assign('title', 'Orders');
        $bag = null;
        $view->put($bag, 'extra', 1);
        $dyn = 'skip';
        $view->setData(['items' => $items, $dyn => 1, 'title' => 'Orders']);
    }
}
