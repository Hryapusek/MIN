import argparse
import asyncio
import logging
import signal

from messenger.shared.core.config import get_settings
from messenger.services.key_manager.factory import build_configured_key_manager
from messenger.services.key_manager.service import KeyManagerRunResult, KeyManagerService


logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synchronize signing-key metadata")
    parser.add_argument("--once", action="store_true", help="run one synchronization cycle and exit")
    return parser


def _log_result(result: KeyManagerRunResult) -> None:
    reconciliation = result.reconciliation
    logger.info(
        "key synchronization complete: provider=%s discovered=%d inserted=%d updated=%d missing=%d activated=%s",
        reconciliation.provider_name,
        reconciliation.discovered,
        reconciliation.inserted,
        reconciliation.updated,
        reconciliation.missing,
        reconciliation.activated_kid,
    )


async def _run_cycle(service: KeyManagerService) -> None:
    try:
        _log_result(await service.run_once())
    except Exception:
        logger.exception("key synchronization failed")
        raise


async def run_polling(
    service: KeyManagerService,
    *,
    interval_seconds: int,
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set():
        try:
            await _run_cycle(service)
        except Exception:
            # The service already rolled back. Keep the singleton process alive
            # and retry on the next configured interval.
            pass

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue


async def _run(*, once: bool) -> int:
    settings = get_settings()
    configured = build_configured_key_manager(settings)

    from messenger.shared.db.session import SessionFactory

    service = KeyManagerService(
        session_factory=SessionFactory,
        discovery_provider=configured.discovery_provider,
        bootstrapper=configured.bootstrapper,
        initial_activation_policy=settings.initial_key_activation_policy,
    )

    if once:
        await _run_cycle(service)
        return 0

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signal_number in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_number, stop_event.set)
        except NotImplementedError:
            # add_signal_handler is unavailable on some platforms, including
            # the default Windows event loop. KeyboardInterrupt still works.
            pass

    await run_polling(
        service,
        interval_seconds=settings.key_manager_sync_interval_seconds,
        stop_event=stop_event,
    )
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = _build_parser().parse_args()
    raise SystemExit(asyncio.run(_run(once=args.once)))


if __name__ == "__main__":
    main()
