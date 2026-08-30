CREATE PROCEDURE dbo.TouchLedger
AS
    UPDATE dbo.Ledger SET Amount = 0, ChangeUser = suser_sname() WHERE LedgerId = 1;
