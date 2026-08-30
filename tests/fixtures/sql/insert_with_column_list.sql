CREATE PROCEDURE dbo.AddLedgerRow
AS
    INSERT INTO dbo.Ledger (LedgerId, Amount)
    VALUES (1, 2);
