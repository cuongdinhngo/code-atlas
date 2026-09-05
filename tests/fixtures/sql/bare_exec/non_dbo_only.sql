-- AC4: the only declaration lives in sales — bare EXEC must not invent dbo.
CREATE PROCEDURE sales.OnlyOne
AS
BEGIN
    SELECT 1;
END
GO
CREATE PROCEDURE sales.OnlyCaller
AS
BEGIN
    EXEC OnlyOne;
END
