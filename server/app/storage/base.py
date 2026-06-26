from typing import BinaryIO, Protocol, runtime_checkable


@runtime_checkable
class Storage(Protocol):
    def save(self, key: str, data: bytes) -> None: ...

    def open(self, key: str) -> BinaryIO: ...

    def delete(self, key: str) -> None: ...
