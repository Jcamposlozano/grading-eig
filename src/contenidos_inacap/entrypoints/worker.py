from __future__ import annotations

from collections.abc import Callable

from contenidos_inacap.ports.queue_port import QueuePort
from contenidos_inacap.shared.logger import get_logger
from contenidos_inacap.shared.shutdown import ShutdownSignal

log = get_logger("contenidos_inacap.worker")


def run_consume_loop(
    *,
    queue: QueuePort,
    handler: Callable[[dict], None],
    shutdown: ShutdownSignal,
    wait_seconds: int,
    max_messages: int,
    idle_sleep: float = 1.0,
) -> None:
    """Consume mensajes y los despacha al handler hasta que se pida shutdown.

    En éxito hace ``ack``; ante error NO hace ack, dejando que SQS reentregue
    (y eventualmente vaya a la DLQ).
    """
    while not shutdown.is_set():
        try:
            messages = queue.consume(max_messages=max_messages, wait_seconds=wait_seconds)
        except Exception:
            log.exception("Error consumiendo de la cola.")
            shutdown.wait(timeout=idle_sleep)
            continue

        if not messages:
            shutdown.wait(timeout=idle_sleep)
            continue

        for message in messages:
            try:
                handler(message.body)
                queue.ack(receipt_handle=message.receipt_handle)
            except Exception:
                log.exception("Error procesando mensaje; no se hace ack (reintento / DLQ).")


def main() -> None:
    from contenidos_inacap.shared.config import load_config

    cfg = load_config()
    if not cfg["worker"]["enabled"]:
        log.info("Worker deshabilitado por config.")
        return

    # Import diferido: evita cargar el container (y sus deps) al importar el módulo.
    from contenidos_inacap.shared.container import get_message_handler, get_queue

    queue = get_queue()
    handler = get_message_handler()
    shutdown = ShutdownSignal()
    log.info("Worker iniciado (consumiendo de la cola).")
    run_consume_loop(
        queue=queue,
        handler=handler,
        shutdown=shutdown,
        wait_seconds=cfg["queue"]["wait_seconds"],
        max_messages=cfg["queue"]["max_messages"],
    )
    log.info("Worker detenido (shutdown).")


if __name__ == "__main__":
    main()
