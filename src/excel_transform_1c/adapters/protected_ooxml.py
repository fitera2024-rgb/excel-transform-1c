from __future__ import annotations

from pathlib import Path
from typing import Any

import msoffcrypto
from msoffcrypto import exceptions

from excel_transform_1c.adapters.workbook_repair import (
    OLE_COMPOUND_FILE_SIGNATURE,
    WorkbookFormat,
    detect_workbook_format,
)

UNKNOWN_DECRYPTION_MESSAGE = (
    "Не удалось расшифровать защищённый файл; выберите файл повторно"
)


class ProtectedWorkbookError(ValueError):
    """A protected workbook cannot be prepared for local processing."""


class ProtectedWorkbookPasswordRequired(ProtectedWorkbookError):
    pass


class ProtectedWorkbookPasswordInvalid(ProtectedWorkbookError):
    pass


def has_ole_signature(path: str | Path) -> bool:
    """Compatibility name: true only for OLE-wrapped encrypted OOXML."""

    return detect_workbook_format(path) is WorkbookFormat.ENCRYPTED_OOXML


def is_encrypted_ooxml(path: str | Path) -> bool:
    return has_ole_signature(path)


def decrypt_protected_ooxml(
    source_path: str | Path,
    target_path: str | Path,
    password: str,
) -> None:
    """Decrypt one encrypted OOXML file without retaining the password."""

    if not password:
        raise ProtectedWorkbookPasswordRequired(
            "Файл защищён. Укажите пароль и выберите файл повторно"
        )

    source_path = Path(source_path)
    target_path = Path(target_path)
    office_file: Any | None = None
    try:
        with source_path.open("rb") as source:
            office_file = msoffcrypto.OfficeFile(source)
            if (
                getattr(office_file, "format", None) != "ooxml"
                or not office_file.is_encrypted()
            ):
                raise ProtectedWorkbookError(
                    "Защищённый файл не распознан как поддерживаемая книга Excel; "
                    "выберите другой файл"
                )
            office_file.load_key(password=password, verify_password=True)
            with target_path.open("xb") as target:
                office_file.decrypt(target, verify_integrity=True)
    except exceptions.InvalidKeyError as exc:
        target_path.unlink(missing_ok=True)
        raise ProtectedWorkbookPasswordInvalid(
            "Пароль не подошёл. Проверьте пароль и выберите файл повторно"
        ) from exc
    except exceptions.FileFormatError as exc:
        target_path.unlink(missing_ok=True)
        raise ProtectedWorkbookError(
            "Защищённый файл не распознан как поддерживаемая книга Excel; "
            "выберите другой файл"
        ) from exc
    except exceptions.DecryptionError as exc:
        target_path.unlink(missing_ok=True)
        raise ProtectedWorkbookPasswordInvalid(
            "Пароль не подошёл. Проверьте пароль и выберите файл повторно"
        ) from exc
    except ProtectedWorkbookError:
        target_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        target_path.unlink(missing_ok=True)
        raise ProtectedWorkbookError(UNKNOWN_DECRYPTION_MESSAGE) from exc
    finally:
        container = getattr(office_file, "file", None)
        close = getattr(container, "close", None)
        if callable(close):
            close()
