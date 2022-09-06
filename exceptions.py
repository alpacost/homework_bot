from dataclasses import dataclass


@dataclass
class ErrorException(Exception):
    """Обработка лога."""

    message: str

    def __str__(self):
        return self.message

