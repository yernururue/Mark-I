"""Small in-memory Firestore doubles used by unit and PICT scenario tests."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import count
from typing import Any, Iterable


@dataclass
class FakeSnapshot:
    id: str
    _data: dict[str, Any] | None

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict[str, Any] | None:
        return None if self._data is None else dict(self._data)


@dataclass
class FakeCountValue:
    value: int


class FakeCountQuery:
    def __init__(self, query: "FakeQuery") -> None:
        self._query = query

    def get(self) -> list[list[FakeCountValue]]:
        return [[FakeCountValue(len(self._query.get()))]]


class FakeQuery:
    def __init__(
        self,
        db: "FakeFirestore",
        path: tuple[str, ...],
        filters: tuple[tuple[str, str, Any], ...] = (),
        order: tuple[str, str] | None = None,
        limit_value: int | None = None,
        limit_last: bool = False,
    ) -> None:
        self._db = db
        self._path = path
        self._filters = filters
        self._order = order
        self._limit = limit_value
        self._limit_last = limit_last

    def _clone(self, **changes: Any) -> "FakeQuery":
        values = {
            "db": self._db,
            "path": self._path,
            "filters": self._filters,
            "order": self._order,
            "limit_value": self._limit,
            "limit_last": self._limit_last,
        }
        values.update(changes)
        return FakeQuery(**values)

    def where(self, *, filter: tuple[str, str, Any]) -> "FakeQuery":
        return self._clone(filters=(*self._filters, filter))

    def order_by(self, field: str, direction: str = "ASCENDING") -> "FakeQuery":
        return self._clone(order=(field, direction))

    def limit(self, value: int) -> "FakeQuery":
        return self._clone(limit_value=value, limit_last=False)

    def limit_to_last(self, value: int) -> "FakeQuery":
        return self._clone(limit_value=value, limit_last=True)

    def _snapshots(self) -> list[FakeSnapshot]:
        depth = len(self._path) + 1
        rows = [
            FakeSnapshot(path[-1], data)
            for path, data in self._db.documents.items()
            if len(path) == depth and path[:-1] == self._path
        ]
        for field, operator, expected in self._filters:
            if operator != "==":
                raise NotImplementedError(operator)
            rows = [row for row in rows if (row._data or {}).get(field) == expected]
        if self._order:
            field, direction = self._order
            rows.sort(
                key=lambda row: (row._data or {}).get(field),
                reverse=str(direction).upper().endswith("DESCENDING"),
            )
        if self._limit is not None:
            rows = rows[-self._limit :] if self._limit_last else rows[: self._limit]
        return rows

    def get(self) -> list[FakeSnapshot]:
        return self._snapshots()

    def stream(self) -> Iterable[FakeSnapshot]:
        return iter(self._snapshots())

    def count(self) -> FakeCountQuery:
        return FakeCountQuery(self)


class FakeCollection(FakeQuery):
    def document(self, document_id: str | None = None) -> "FakeDocument":
        if document_id is None:
            document_id = f"auto-{next(self._db.ids)}"
        return FakeDocument(self._db, (*self._path, document_id))


class FakeDocument:
    def __init__(self, db: "FakeFirestore", path: tuple[str, ...]) -> None:
        self._db = db
        self._path = path

    @property
    def id(self) -> str:
        return self._path[-1]

    def get(self, transaction: Any = None) -> FakeSnapshot:
        del transaction
        data = self._db.documents.get(self._path)
        return FakeSnapshot(self.id, None if data is None else dict(data))

    def set(self, data: dict[str, Any]) -> None:
        self._db.documents[self._path] = dict(data)

    def update(self, data: dict[str, Any]) -> None:
        current = self._db.documents.setdefault(self._path, {})
        for key, value in data.items():
            if "." not in key:
                current[key] = value
                continue
            parent, child = key.split(".", 1)
            current.setdefault(parent, {})[child] = value

    def delete(self) -> None:
        self._db.documents.pop(self._path, None)

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self._db, (*self._path, name))


class FakeTransaction:
    def update(self, document: FakeDocument, data: dict[str, Any]) -> None:
        document.update(data)


class FakeFirestore:
    def __init__(self) -> None:
        self.documents: dict[tuple[str, ...], dict[str, Any]] = {}
        self.ids = count(1)

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self, (name,))

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    def transactional(self, function):
        """Test double for the intent of SkillService's transaction wrapper."""

        return function

