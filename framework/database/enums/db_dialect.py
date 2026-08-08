from enum import StrEnum


class DbDialect(StrEnum):
    """Every database engine this framework can target. Selecting a dialect
    is a config change (`database.<key>.dialect` in `config/environments/*.yaml`)
    — nothing in `framework/database` branches on a hardcoded engine name, so
    adding support for a new SQLAlchemy-backed dialect never touches a test.
    """

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    MSSQL = "mssql"
    SQLITE = "sqlite"
