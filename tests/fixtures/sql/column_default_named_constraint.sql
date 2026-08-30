CREATE TABLE dbo.Stamped (
    CreatedAt datetime2 NOT NULL
);
GO
ALTER TABLE dbo.Stamped ADD CONSTRAINT DF_Stamped_CreatedAt DEFAULT (sysdatetime()) FOR CreatedAt;
