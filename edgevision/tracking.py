"""ctypes wrapper for C++17 tracker; no Python tracking fallback."""
import ctypes as C
from pathlib import Path


class Detection(C.Structure):
    _fields_ = [(k, C.c_double) for k in ('x', 'y', 'w', 'h')]


class Track(C.Structure):
    _fields_ = [('id', C.c_int)] + [(k, C.c_double) for k in ('x', 'y', 'w', 'h')] + [('missed', C.c_int)]


class CppTracker:
    def __init__(self, max_distance=65.0, max_missed=8, library=None):
        path = Path(library) if library else Path(__file__).resolve().parents[1] / 'build' / 'libedgevision_tracker.so'
        if not path.is_file():
            raise FileNotFoundError(f'C++ tracking library missing: {path}. Run bash scripts/build.sh')
        self.lib = C.CDLL(str(path))
        self.lib.ev_tracker_create.argtypes = [C.c_double, C.c_int]
        self.lib.ev_tracker_create.restype = C.c_void_p
        self.lib.ev_tracker_destroy.argtypes = [C.c_void_p]
        self.lib.ev_tracker_destroy.restype = None
        self.lib.ev_tracker_update.argtypes = [C.c_void_p, C.POINTER(Detection), C.c_int, C.POINTER(Track), C.c_int]
        self.lib.ev_tracker_update.restype = C.c_int
        self.handle = self.lib.ev_tracker_create(max_distance, max_missed)
        if not self.handle:
            raise ValueError('Invalid tracker configuration')

    def update(self, boxes):
        if self.handle is None:
            raise RuntimeError('Tracker closed')
        n = len(boxes)
        arr = (Detection * n)(*(Detection(*map(float, b)) for b in boxes))
        # Tracks cannot exceed detections seen across the session; grow on demand using retry.
        # Allocate at least the total detections ever seen; the number of live tracks
        # can never exceed that count, including after occlusion.
        self._capacity = getattr(self, '_capacity', 0) + n
        cap = max(1, self._capacity)
        out = (Track * cap)()
        result = self.lib.ev_tracker_update(self.handle, arr, n, out, cap)
        if result < 0:
            raise ValueError(f'C++ tracker update failed, status={result}')
        return [dict(id=t.id, box=(t.x, t.y, t.w, t.h), missed=t.missed) for t in out[:result]]

    def close(self):
        if self.handle is not None:
            self.lib.ev_tracker_destroy(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
