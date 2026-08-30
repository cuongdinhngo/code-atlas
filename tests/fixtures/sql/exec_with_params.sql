CREATE PROCEDURE dbo.WithArgs
AS
BEGIN
    EXEC dbo.Receiver @First = 1, @Second = N'text';
END
