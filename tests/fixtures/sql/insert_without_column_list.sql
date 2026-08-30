CREATE PROCEDURE dbo.CopyLedger
AS
    INSERT INTO dbo.Ledger SELECT * FROM staging.Ledger;
