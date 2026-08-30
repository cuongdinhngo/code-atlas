CREATE PROCEDURE dbo.QuotesOnly
AS
BEGIN
    DECLARE @note NVARCHAR(200) = N'EXEC dbo.NotACall and it''s still not one';
    SELECT @note;
END
