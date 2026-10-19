CREATE VIEW dbo.ActiveOrders
AS
SELECT o.Id, c.Name
  FROM dbo.Orders o
  JOIN dbo.Customers c ON c.Id = o.CustomerId
 WHERE o.Active = 1;
GO
