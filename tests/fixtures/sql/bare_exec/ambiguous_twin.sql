-- AC2/AC3: two schemas declare the same bare name; EXEC must not pick one.
CREATE PROCEDURE dbo.Twin
AS
BEGIN
    SELECT 1;
END
GO
CREATE PROCEDURE sales.Twin
AS
BEGIN
    SELECT 2;
END
GO
CREATE PROCEDURE dbo.TwinCaller
AS
BEGIN
    EXEC Twin;
END
