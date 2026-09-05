-- AC1: schema-unqualified EXEC against a single dbo declaration.
CREATE PROCEDURE dbo.BareTarget
AS
BEGIN
    SELECT 1;
END
GO
CREATE PROCEDURE dbo.BareCaller
AS
BEGIN
    EXEC BareTarget;
END
GO
CREATE PROCEDURE dbo.BareExecuteCaller
AS
BEGIN
    EXECUTE BareTarget;
END
