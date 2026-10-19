CREATE OR ALTER VIEW [dbo].[ActiveOrders] AS SELECT Id FROM dbo.Orders WHERE Active = 1
GO
ALTER VIEW dbo.OpenOrders
AS
SELECT Id FROM dbo.Orders WHERE Closed = 0
GO
