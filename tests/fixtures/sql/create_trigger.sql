CREATE TRIGGER dbo.TR_Ledger ON dbo.Ledger AFTER INSERT AS
    UPDATE dbo.Ledger SET ChangeUser = suser_sname();
