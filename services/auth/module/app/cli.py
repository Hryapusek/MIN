import argparse
import asyncio
import json

from sqlalchemy import select

from app.auth.key_registry import SigningKeyRegistry
from app.auth.provider_factory import build_configured_signing_provider
from app.auth.types import SigningBackend
from app.core.config import get_settings
from app.models.signing_key import SigningKey


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Messenger auth administration commands")
    commands = parser.add_subparsers(dest="command", required=True)

    signing_keys = commands.add_parser("signing-keys", help="manage signing-key material and registry")
    signing_commands = signing_keys.add_subparsers(dest="signing_command", required=True)
    signing_commands.add_parser("bootstrap", help="prepare configured local key material")
    signing_commands.add_parser("sync", help="reconcile provider keys into PostgreSQL")
    signing_commands.add_parser("list", help="show registered signing-key metadata")
    return parser


async def _bootstrap() -> int:
    settings = get_settings()
    if settings.token_signing_backend != SigningBackend.LOCAL:
        raise RuntimeError("local key bootstrap is available only with TOKEN_SIGNING_BACKEND=local")

    configured = build_configured_signing_provider(settings, run_bootstrap=True)
    result = configured.bootstrap_result
    assert result is not None
    print(
        json.dumps(
            {
                "generated": result.generated,
                "manifest_path": str(result.manifest_path),
                "key_reference": result.key_reference,
                "provider_version": result.provider_version,
            },
            indent=2,
        )
    )
    return 0


async def _sync() -> int:
    from app.db.session import SessionFactory

    settings = get_settings()
    configured = build_configured_signing_provider(settings, run_bootstrap=True)
    descriptors = await configured.provider.list_keys()

    with SessionFactory.begin() as session:
        result = SigningKeyRegistry().reconcile(
            session,
            provider=configured.provider,
            descriptors=descriptors,
            initial_activation_policy=settings.initial_key_activation_policy,
        )

    print(
        json.dumps(
            {
                "provider_name": result.provider_name,
                "discovered": result.discovered,
                "inserted": result.inserted,
                "updated": result.updated,
                "missing": result.missing,
                "activated_kid": result.activated_kid,
            },
            indent=2,
        )
    )
    return 0


def _list_registered() -> int:
    from app.db.session import SessionFactory

    with SessionFactory() as session:
        rows = list(session.scalars(select(SigningKey).order_by(SigningKey.created_at.asc())))

    print(
        json.dumps(
            [
                {
                    "kid": row.kid,
                    "provider_name": row.provider_name,
                    "backend": row.backend.value,
                    "external_reference": row.external_reference,
                    "provider_version": row.provider_version,
                    "purpose": row.purpose.value,
                    "algorithm": row.algorithm,
                    "status": row.status.value,
                    "last_seen_at": row.last_seen_at.isoformat(),
                    "unavailable_since": (
                        row.unavailable_since.isoformat() if row.unavailable_since is not None else None
                    ),
                }
                for row in rows
            ],
            indent=2,
        )
    )
    return 0


async def _run(args: argparse.Namespace) -> int:
    if args.command == "signing-keys" and args.signing_command == "bootstrap":
        return await _bootstrap()
    if args.command == "signing-keys" and args.signing_command == "sync":
        return await _sync()
    if args.command == "signing-keys" and args.signing_command == "list":
        return _list_registered()
    raise RuntimeError("unknown command")


def main() -> None:
    args = _build_parser().parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
