<?php

class Foo_Bar_Baz extends Legacy_Table
{
    public function fetch()
    {
        return new Legacy_Table();
    }
}
