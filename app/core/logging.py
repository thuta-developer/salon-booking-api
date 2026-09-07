"""Application-wide logging configuration."""
import logging
import sys

_CONFIGURED = False


class SQLStatementOnlyFilter(logging.Filter):
    """Keep only the actual application SQL statements — drop all other noise.

    SQLAlchemy logs each query as several records, e.g.:

        BEGIN (implicit)                 <-- transaction marker
        SELECT users.email FROM users    <-- the SQL we want
        [params]: ('admin@x.com',)       <-- bound parameters noise
        [cached since 0.1s ago]          <-- compilation cache noise
        COMMIT                            <-- transaction marker

    Additionally Python DBAPI/dialects emit on-connect queries
    (``select pg_catalog.version()``, ``show standard_conforming_strings``, …)
    every time a new pool connection is opened.  Those are also dropped so the
    terminal shows only the application's own queries.
    """

    _TRANSACTION_MARKERS = {"BEGIN", "BEGIN (implicit)", "COMMIT", "ROLLBACK"}

    # asyncpg/psycopg on-connect verification queries (lower-cased prefixes)
    _DIALECT_STARTUP_PATTERNS = (
        "select pg_catalog.version()",
        "select current_schema()",
        "show standard_conforming_strings",
        "select cast('test",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if msg.startswith("["):
            return False

        stripped = msg.strip()
        if stripped in self._TRANSACTION_MARKERS:
            return False

        lower = stripped.lower()
        if any(lower.startswith(p) for p in self._DIALECT_STARTUP_PATTERNS):
            return False

        return True


class SQLQueryFormatter(logging.Formatter):
    """Render SQL at the very front of the line — no prefix, no indentation.

    * First line  → leading whitespace removed so the SQL starts at column 0.
    * Later lines → trailing whitespace removed (inner indentation is kept).
    * After each  → the handler's ``terminator`` adds a blank line.

    Output example::

        SELECT count(*) FROM users
        <blank line>
    """

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        lines = message.splitlines() or [""]

        cleaned = [lines[0].lstrip()]
        cleaned.extend(line.rstrip() for line in lines[1:])

        formatted = "\n".join(cleaned)
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)
        return formatted


def _setup_sqlalchemy_logging(level: int = logging.INFO) -> None:
    """Print SQLAlchemy queries to stdout — SQL text only, blank line after.

    Output format per query::

        SELECT users.email FROM users
        <blank line>

    Should be enabled only for development/debug environments (see
    ``settings.DEBUG``).  Requires the engine to run with ``echo=False``
    (already set in ``app/core/database.py``).
    """
    engine_logger = logging.getLogger("sqlalchemy.engine")
    engine_logger.setLevel(level)

    # Generic root handlers (timestamp | level | name | message) က ဒီ logger
    # ရဲ့ params/transaction lines တွေပါ ထပ်ပြီး duplicate မဖြစ်စေရန်
    # root သို့ propagate ပြုလုပ်ခြင်းကို ပိတ်သည်။
    engine_logger.propagate = False

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(SQLQueryFormatter())
    handler.addFilter(SQLStatementOnlyFilter())
    # "\n" (query) + "\n" (blank line) — query တစ်ခုပြီးတိုင်း တစ်ကြောင်း ဆင်းပေးသည်
    handler.terminator = "\n\n"
    engine_logger.addHandler(handler)

    # Connection pool / dialect noise (connection info) ကို terminal မှာ
    # မ‌ပေါ်စေရန် ပိတ်ထားသည် — queries များသာ ပေါ်မည်။
    for name in ("sqlalchemy.pool", "sqlalchemy.dialects"):
        quiet = logging.getLogger(name)
        quiet.setLevel(logging.WARNING)
        quiet.propagate = False


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure the root logger once and return the `app` logger.

    Should be called from ``app.main`` before anything else logs.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return logging.getLogger("app")

    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root.addHandler(handler)

    # Development တွင် clean SQL query များ stdout ပေါ် ပြသရန်
    try:
        from app.core.config import settings

        if settings.DEBUG:
            _setup_sqlalchemy_logging(level=logging.INFO)
    except Exception:
        # Best-effort — SQL logging failure သည် app ကို မဖျက်ဆီးရပါ
        pass

    _CONFIGURED = True
    return logging.getLogger("app")


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger (automatically uses root config)."""
    return logging.getLogger(name)