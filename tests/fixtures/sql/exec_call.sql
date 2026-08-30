CREATE PROCEDURE dbo.Caller
AS
BEGIN
    EXEC dbo.Callee;
END
