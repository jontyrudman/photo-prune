import asyncio
from concurrent.futures import Future
import logging
import threading


class AsyncThread():
    _loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
    futures: dict[str, Future] = {}

    def start_async(self):
        threading.Thread(target=self._loop.run_forever).start()

    # Submits awaitable to the event loop, but *doesn't* wait for it to
    # complete. Returns a concurrent.futures.Future which *may* be used to
    # wait for and retrieve the result (or exception, if one was raised)
    def submit_async(self, awaitable, key: str) -> Future:
        if key in self.futures:
            logging.debug(f"Awaitable already submitted: {key}")
            return self.futures[key]

        future = asyncio.run_coroutine_threadsafe(awaitable, self._loop)

        def callback(_):
            if key in self.futures:
                del self.futures[key]
            logging.debug(f"Awaitable deleted: {key}")

        self.futures[key] = future
        future.add_done_callback(callback)
        return future

    def stop_async(self):
        self._loop.call_soon_threadsafe(self._loop.stop)


thread = AsyncThread()
