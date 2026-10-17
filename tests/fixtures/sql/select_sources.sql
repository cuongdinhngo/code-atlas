CREATE PROCEDURE dbo.ReportOrders
AS
    WITH recent AS (SELECT Id FROM dbo.Orders)
    SELECT o.Id, c.Name
      FROM recent r
      JOIN dbo.Orders o ON o.Id = r.Id
      LEFT JOIN dbo.Customers c ON c.Id = o.CustomerId
      JOIN #scratch s ON s.Id = o.Id;
