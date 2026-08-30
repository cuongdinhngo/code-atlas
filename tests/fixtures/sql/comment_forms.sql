-- EXEC dbo.CommentedOut
CREATE PROCEDURE dbo.Commented
AS
BEGIN
    /* EXEC dbo.BlockCommented
       still inside the block */
    SELECT 1; -- EXEC dbo.TrailingComment
END
