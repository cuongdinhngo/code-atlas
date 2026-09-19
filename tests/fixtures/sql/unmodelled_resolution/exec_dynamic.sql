CREATE PROCEDURE dbo.DynamicCaller
AS
BEGIN
    DECLARE @sql NVARCHAR(MAX) = N'SELECT 1';
    EXEC (@sql);
    EXEC sp_executesql @sql;
    EXEC @ProcName;
END
