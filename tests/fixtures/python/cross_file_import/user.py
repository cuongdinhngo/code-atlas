"""Importer: base, annotation, decorator — all from another file."""

from cross_file_import.entities import Entity, audit


class User(Entity):
    def save(self, e: Entity) -> None:
        return None


@audit
class Decorated:
    pass
