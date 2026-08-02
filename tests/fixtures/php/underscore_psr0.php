<?php

class Foo_Bar_Baz extends Legacy_Table
{
    const TABLE = 'foo';

    protected $rows = [];

    public function fetchRow($id)
    {
        return Legacy_Registry::get($id);
    }
}

function foo_helper()
{
    return new Foo_Bar_Baz();
}
