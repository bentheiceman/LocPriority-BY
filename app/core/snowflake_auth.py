from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SnowflakeAuthConfig:
    account: str = "HDSUPPLY-DATA"
    authenticator: str = "externalbrowser"


class SnowflakeAuthError(RuntimeError):
    pass


def authenticate(*, email: str, insecure_mode: bool, config: SnowflakeAuthConfig | None = None) -> None:
    """Authenticate to Snowflake via SSO external browser.

    This performs a connection attempt and immediately closes it on success.
    """

    email = (email or "").strip()
    if not email or "@" not in email:
        raise SnowflakeAuthError("Enter a valid HD Supply email address (e.g., name@hdsupply.com).")

    cfg = config or SnowflakeAuthConfig()

    try:
        import snowflake.connector as sc  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise SnowflakeAuthError(
            "Snowflake connector is not available. Install dependencies or use the packaged EXE."
        ) from exc

    try:
        con = sc.connect(
            user=email,
            account=cfg.account,
            authenticator=cfg.authenticator,
            insecure_mode=bool(insecure_mode),
        )
    except Exception as exc:  # noqa: BLE001
        raise SnowflakeAuthError(str(exc)) from exc
    finally:
        try:
            con.close()  # type: ignore[has-type]
        except Exception:
            pass
