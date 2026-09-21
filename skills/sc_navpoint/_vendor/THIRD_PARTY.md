# OpenCV dependency notice

OpenCV Python 5.0.0.93 supplies image resizing for NavPoint's OCR preprocessing.
Its license and third-party notices are included with the library.

The Python loader `cv2/__init__.py` was modified on 2026-09-15: when the legacy
`numpy.core.multiarray` import (or its parent) is absent, it falls back to
`numpy._core.multiarray`. Unrelated import errors still propagate. This supports
Wingman's frozen NumPy 2 environment without global module aliases. The native
OpenCV binary and image interpolation are unchanged.

This selection omits development typing stubs and the optional FFmpeg video
plugin. NavPoint uses screen capture and image resizing, not OpenCV video I/O.
