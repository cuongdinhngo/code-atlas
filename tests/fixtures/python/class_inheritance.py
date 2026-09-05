"""Single base class — inventory row ``class-inheritance``."""


class Animal:
    def speak(self) -> str:
        return "..."


class Dog(Animal):
    def speak(self) -> str:
        return "woof"
