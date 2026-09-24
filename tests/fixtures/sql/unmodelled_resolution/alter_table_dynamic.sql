-- A migration that re-points a DEFAULT through sp_executesql (task 321): the table name exists only
-- inside the string, so the ALTERS claim is DYNAMIC. The SELECT names the table without a DDL verb.
DECLARE @sql nvarchar(max) = N'ALTER TABLE dbo.Stamped ADD CONSTRAINT DF_Stamped_At
    DEFAULT (sysdatetime()) FOR CreatedAt';
EXEC sp_executesql @sql;
EXEC (N'SELECT CreatedAt FROM dbo.Stamped');
