-- A T-SQL parameter list wrapped across lines — ticket 231.
CREATE PROCEDURE dbo.Pay
    @amount int,
    @who nvarchar(50) = 'x'
AS
BEGIN
    SELECT @amount;
END
GO

CREATE PROCEDURE dbo.Settle @ref uniqueidentifier
AS
BEGIN
    EXEC dbo.Pay @amount = 5, @who = 'bob';
END
GO

CREATE TABLE dbo.Bill (Total decimal(10,2) NOT NULL);
GO
