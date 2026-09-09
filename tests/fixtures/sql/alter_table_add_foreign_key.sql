-- A standalone constraint file (the `_fk_constraints.sql` shape, task 236): the table is defined
-- elsewhere; here it is only altered to add a foreign key. The constraint is its own node, never a
-- second Table row for the table it sits on.
ALTER TABLE [dbo].[MemberType]
    ADD CONSTRAINT [FK_MemberType_MemberParentTypeID]
    FOREIGN KEY ([MemberParentTypeId]) REFERENCES [dbo].[MemberParentType] ([Id]);
