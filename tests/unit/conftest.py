"""
Carga ordenada de modelos SQLAlchemy para pruebas unitarias (relaciones string-based).
"""

from __future__ import annotations


def pytest_configure(config) -> None:
    import app.models.user  # noqa: F401
    import app.models.profile  # noqa: F401
    import app.models.place  # noqa: F401
    import app.models.review  # noqa: F401
    import app.models.recommendation  # noqa: F401
    import app.models.pyme  # noqa: F401
    import app.models.auth_token  # noqa: F401
