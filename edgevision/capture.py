"""Bounded, timestamped acquisition for non-hard-real-time applications.

Timestamps are host times after decode, NEVER hardware exposure timestamps.
"""
from dataclasses import dataclass
import threading
import time


@dataclass(frozen=True)
class FramePacket:
    sequence: int
    captured_ns: int
    frame: object

    def queue_wait_ms(self, *, now_ns=None):
        now = time.monotonic_ns() if now_ns is None else now_ns
        return max(0.0, (now - self.captured_ns) / 1e6)


class BoundedFrameQueue:
    def __init__(self, capacity):
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0:
            raise ValueError('capacity must be a positive integer')
        from collections import deque
        self.capacity = capacity
        self._items = deque()
        self._closed = False
        self._condition = threading.Condition()
        self.dropped_overflow = 0
        self.max_depth = 0

    @property
    def depth(self):
        with self._condition:
            return len(self._items)

    def put(self, item):
        with self._condition:
            if self._closed:
                return False
            if len(self._items) == self.capacity:
                self._items.popleft()
                self.dropped_overflow += 1
            self._items.append(item)
            self.max_depth = max(self.max_depth, len(self._items))
            self._condition.notify()
            return True

    def get(self):
        with self._condition:
            self._condition.wait_for(lambda: self._items or self._closed)
            if self._items:
                return self._items.popleft()
            return None

    def close(self):
        with self._condition:
            self._closed = True
            self._condition.notify_all()


class CaptureWorker:
    """Owns capture resource after start, releases it on worker exit."""

    def __init__(self, capture, *, capacity=3):
        self.queue = BoundedFrameQueue(capacity)
        self.capture = capture
        self.frames_read = 0
        self._stop = threading.Event()
        self._error = None
        self._thread = threading.Thread(target=self._run, name='edgevision-capture', daemon=False)

    def start(self):
        self._thread.start()
        return self

    def _run(self):
        try:
            while not self._stop.is_set():
                ok, frame = self.capture.read()
                if not ok:
                    break
                stamp = time.monotonic_ns()
                packet = FramePacket(self.frames_read, stamp, frame)
                self.frames_read += 1
                if not self.queue.put(packet):
                    break
        except Exception as exc:
            self._error = exc
        finally:
            try:
                self.capture.release()
            finally:
                self.queue.close()

    def frames(self):
        while True:
            packet = self.queue.get()
            if packet is None:
                if self._error is not None:
                    raise RuntimeError(f'Capture worker failed: {self._error}') from self._error
                break
            yield packet

    def stop(self):
        self._stop.set()
        # Wakes consumer and makes late pushes return False.
        self.queue.close()
        if self._thread.ident is not None:
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                raise RuntimeError('Capture worker did not stop; capture.read() may be blocking')

    @property
    def is_alive(self):
        return self._thread.is_alive()

    @property
    def dropped_overflow(self):
        return self.queue.dropped_overflow
