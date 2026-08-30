CREATE TABLE dbo.Ledger (
    LedgerId int NOT NULL,
    CONSTRAINT PK_Ledger PRIMARY KEY (LedgerId),
    INDEX IX_Ledger NONCLUSTERED (LedgerId)
);
