"""v0.3 black-box contractual tests written BEFORE the queue implementation."""
import threading
import time

import numpy as np
import pytest

from edgevision.capture import BoundedFrameQueue, CaptureWorker, FramePacket


def packet(seq, stamp=100):
    return FramePacket(sequence=seq, captured_ns=stamp, frame=np.zeros((2, 2, 3), dtype=np.uint8))


def test_drop_oldest_and_fifo_order():
    q = BoundedFrameQueue(2)
    assert q.put(packet(0))
    assert q.put(packet(1))
    assert q.put(packet(2))
    assert [q.get().sequence, q.get().sequence] == [1, 2]
    assert q.dropped_overflow == 1
    assert q.max_depth == 2
    q.close()
    assert q.get() is None


def test_overload_remains_bounded():
    q = BoundedFrameQueue(1)
    for n in range(100):
        q.put(packet(n))
        assert q.depth <= 1
    assert q.dropped_overflow == 99
    assert q.get().sequence == 99


def test_packets_are_ordered_and_queue_residence_uses_monotonic_clock():
    with pytest.raises(ValueError):
        BoundedFrameQueue(0)
    q = BoundedFrameQueue(3)
    q.put(packet(7, 1_000_000))
    q.put(packet(8, 2_000_000))
    first = q.get()
    second = q.get()
    assert [first.sequence, second.sequence] == [7, 8]
    assert first.queue_wait_ms(now_ns=3_000_000) == 2.0
    assert second.queue_wait_ms(now_ns=3_000_000) == 1.0
    assert first.queue_wait_ms(now_ns=0) == 0.0


def test_close_wakes_waiter_drains_and_rejects_push():
    q = BoundedFrameQueue(2)
    output = []
    consumer = threading.Thread(target=lambda: output.append(q.get()))
    consumer.start()
    q.close()
    consumer.join(timeout=1)
    assert not consumer.is_alive()
    assert output == [None]
    assert not q.put(packet(4))
    another = BoundedFrameQueue(2)
    another.put(packet(3))
    another.close()
    assert another.get().sequence == 3
    assert another.get() is None


class FiniteCapture:
    def __init__(self, count=4, fail=False):
        self.count = count
        self.fail = fail
        self.released = False

    def read(self):
        if self.fail:
            raise RuntimeError('sensor disconnected')
        if self.count == 0:
            return False, None
        self.count -= 1
        return True, np.zeros((8, 8, 3), dtype=np.uint8)

    def release(self):
        self.released = True


def test_capture_worker_eof_and_join():
    source = FiniteCapture(3)
    worker = CaptureWorker(source, capacity=10)
    worker.start()
    packets = list(worker.frames())
    worker.stop()
    assert [p.sequence for p in packets] == [0, 1, 2]
    assert worker.frames_read == 3
    assert worker.dropped_overflow == 0
    assert source.released
    assert not worker.is_alive


def test_capture_worker_propagates_failure():
    source = FiniteCapture(fail=True)
    worker = CaptureWorker(source, capacity=2)
    worker.start()
    with pytest.raises(RuntimeError, match='sensor disconnected'):
        list(worker.frames())
    worker.stop()
    assert source.released
    assert not worker.is_alive


def test_worker_early_stop_joins():
    class SlowCapture(FiniteCapture):
        def read(self):
            time.sleep(0.005)
            return super().read()

    source = SlowCapture(100)
    worker = CaptureWorker(source, capacity=2)
    worker.start()
    assert next(worker.frames()).sequence >= 0
    worker.stop()
    assert not worker.is_alive
    assert source.released
