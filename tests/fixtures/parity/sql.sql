CREATE TABLE dbo.Repo (Owner nvarchar(50) NOT NULL);
GO
CREATE PROCEDURE dbo.Tag @name nvarchar(50), @n int = 3
AS
BEGIN
    UPDATE dbo.Repo SET Owner = @name;
END
GO
CREATE PROCEDURE dbo.Run
AS
BEGIN
    EXEC dbo.Tag @name = 'name', @n = 3;
END
GO
