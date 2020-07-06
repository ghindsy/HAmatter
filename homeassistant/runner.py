"""Run Home Assistant."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import dataclasses
import logging
import sys
from typing import Any, Dict, Optional

import yarl

from homeassistant import bootstrap
from homeassistant.core import callback
from homeassistant.helpers.frame import warn_use


@dataclasses.dataclass
class RuntimeConfig:
    """Class to hold the information for running Home Assistant."""

    config_dir: str
    skip_pip: bool = False
    safe_mode: bool = False

    verbose: bool = False

    log_rotate_days: Optional[int] = None
    log_file: Optional[str] = None
    log_no_color: bool = False

    debug: bool = False
    open_ui: bool = False


def setup_loop(runtime_config: RuntimeConfig) -> asyncio.AbstractEventLoop:
    """Create the event loop."""
    # In Python 3.8+ proactor policy is the default on Windows
    if sys.platform == "win32" and sys.version_info[:3] < (3, 8):
        policy_base = asyncio.WindowsProactorEventLoopPolicy()
    else:
        policy_base = asyncio.DefaultEventLoopPolicy

    class HassEventLoopPolicy(policy_base):
        def get_event_loop(self):
            """Get the event loop."""
            loop = super().get_event_loop()
            loop.set_exception_handler(async_loop_exception_handler)
            if runtime_config.debug:
                loop.set_debug(True)
            return loop

    asyncio.set_event_loop_policy(HassEventLoopPolicy())


def setup_executor(loop: asyncio.AbstractEventLoop):
    """Set up an executor on the loop.

    Async friendly.
    """
    executor = ThreadPoolExecutor(thread_name_prefix="SyncWorker")
    loop.set_default_executor(executor)
    loop.set_default_executor = warn_use(  # type: ignore
        loop.set_default_executor, "sets default executor on the event loop"
    )
    return executor


@callback
def async_loop_exception_handler(_: Any, context: Dict) -> None:
    """Handle all exception inside the core loop."""
    kwargs = {}
    exception = context.get("exception")
    if exception:
        kwargs["exc_info"] = (type(exception), exception, exception.__traceback__)

    logging.getLogger(__package__).error(
        "Error doing job: %s", context["message"], **kwargs  # type: ignore
    )


async def setup_and_run_hass(runtime_config: RuntimeConfig,) -> int:
    """Set up Home Assistant and run."""
    loop = asyncio.get_running_loop()
    hass = await bootstrap.async_setup_hass(
        loop=loop, executor=setup_executor(loop), runtime_config=runtime_config
    )

    if hass is None:
        return 1

    if runtime_config.open_ui:
        import webbrowser  # pylint: disable=import-outside-toplevel

        if hass.config.api is not None:
            scheme = "https" if hass.config.api.use_ssl else "http"
            url = str(
                yarl.URL.build(
                    scheme=scheme, host="127.0.0.1", port=hass.config.api.port
                )
            )
            hass.add_job(webbrowser.open, url)

    return await hass.async_run()


def run(runtime_config: RuntimeConfig) -> int:
    """Run Home Assistant."""
    setup_loop(runtime_config)
    return asyncio.run(setup_and_run_hass(runtime_config))
