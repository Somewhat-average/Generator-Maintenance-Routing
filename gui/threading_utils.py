import threading
import queue


def run_in_background(widget, func, on_done, *args, **kwargs):
    """Run func(*args, **kwargs) on a daemon thread. When it finishes, schedule
    on_done(status, payload) on the Tk main thread via widget.after().
    status is "ok" (payload=return value) or "error" (payload=Exception)."""
    result_queue = queue.Queue()

    def worker():
        try:
            result_queue.put(("ok", func(*args, **kwargs)))
        except Exception as exc:
            result_queue.put(("error", exc))

    threading.Thread(target=worker, daemon=True).start()

    def poll():
        try:
            status, payload = result_queue.get_nowait()
        except queue.Empty:
            widget.after(100, poll)
            return
        on_done(status, payload)

    widget.after(100, poll)
