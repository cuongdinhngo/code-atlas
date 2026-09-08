"""One literal-argument call per resolution tier — ticket 231.

Every arm of the CALLS emitter must carry `args`, including the local-type-table arm 227 added
after 231's capture was written. A tier that resolves better must not record less.
"""


class Bag:
    def set(self, key, value):
        pass


class Base:
    def run(self, key):
        pass


def helper(key, n):
    return key


class Handler(Base):
    bag: Bag

    def module_function(self):
        return helper("a", 1)

    def resolved_receiver(self):
        bag = Bag()
        return bag.set("b", 2)

    def annotated_receiver(self):
        return self.bag.set("c", 3)

    def own_method(self):
        return self.module_function()

    def super_call(self):
        return super().run("d")

    def unknown_receiver(self, other):
        return other.set("e", 5)
