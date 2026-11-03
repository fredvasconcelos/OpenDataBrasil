"""Escrita e leitura Delta Lake da plataforma."""

from odb_lakehouse.disk import DiskCapacityError, DiskLevel, DiskStatus, disk_status
from odb_lakehouse.locking import InProcessLock, LockUnavailableError, TableWriteLock, lock_key
from odb_lakehouse.protocol import ProtocolViolationError, validate_schema, validate_table
from odb_lakehouse.tables import DeltaReader, DeltaWriter, TableWriteError, WriteResult

__all__ = [
    "DeltaReader",
    "DeltaWriter",
    "DiskCapacityError",
    "DiskLevel",
    "DiskStatus",
    "InProcessLock",
    "LockUnavailableError",
    "ProtocolViolationError",
    "TableWriteError",
    "TableWriteLock",
    "WriteResult",
    "disk_status",
    "lock_key",
    "validate_schema",
    "validate_table",
]
