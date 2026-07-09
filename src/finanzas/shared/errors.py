"""Jerarquía base de errores de la aplicación (docs/08)."""


class AppError(Exception):
    """Error base: todo error propio del sistema hereda de aquí."""

    code = "app_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigError(AppError):
    code = "config_error"


class NotFoundError(AppError):
    code = "not_found"


class UnknownFlagError(ConfigError):
    """Se leyó/escribió un flag no declarado en el catálogo (docs/11 §2)."""

    code = "unknown_flag"


class InvalidFlagValueError(ConfigError):
    """Valor de flag con tipo incompatible con su declaración."""

    code = "invalid_flag_value"


class ParserError(AppError):
    """El archivo fue reconocido pero su contenido es inválido/ambiguo.

    Tolerancia cero (docs/05 §3): ante duda, fallar con mensaje claro es
    correcto; insertar datos dudosos es un bug.
    """

    code = "parser_error"


class UnsupportedFormatError(AppError):
    """Ningún parser reconoce el archivo. NO es un fallo del sistema:
    el wizard lo comunica y registra el archivo para facilitar el parser nuevo."""

    code = "unsupported_format"


class AlreadyImportedError(AppError):
    """El mismo archivo (sha256) ya fue importado en esta cuenta."""

    code = "already_imported"
