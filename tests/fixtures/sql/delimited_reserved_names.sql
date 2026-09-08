-- Delimiting is SQL's own way to name an object after a keyword, so every name here is real.
CREATE TABLE [dbo].[Key] (
    [Table] int NOT NULL,
    [Column] nvarchar(50) NULL,
    "constraint" int NULL,
    plain_col int NULL
);

CREATE TABLE [Constraint] (
    id int NOT NULL,
    [Key] int NULL
);

CREATE PROCEDURE [dbo].[Exists] AS SELECT 1;
