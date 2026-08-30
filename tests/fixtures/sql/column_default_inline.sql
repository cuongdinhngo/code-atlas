CREATE TABLE dbo.Audit (
    ChangeUser varchar(50) DEFAULT (user_name())
);
