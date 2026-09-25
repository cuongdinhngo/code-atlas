<?php

namespace App;

class Repo
{
    public function save($db, $table, $a, $sfx)
    {
        $sql = "INSERT INTO dbo.T (a) VALUES (1)";
        $db->run("EXEC dbo.Gen @x = 1");
        $db->run("UPDATE {$table} SET a = 1");
        $db->run("see dbo.T");
        $db->run("DELETE FROM dbo.T WHERE a = " . $a);
        $db->run("UPDATE dbo.T" . $sfx . " SET a = 1");
        $db->run('Update settings');
        $q = <<<SQL
            MERGE INTO dbo.T AS t
            USING dbo.S s ON 1 = 1
            WHEN MATCHED THEN UPDATE SET a = 2;
            SQL;
        return $sql . $q;
    }

    public function more($db)
    {
        $db->run('EXEC @rc = dbo.Gen @x = 1');
        $db->run('Delete from dbo.T after archiving');
    }
}
