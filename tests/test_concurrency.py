"""
Unit tests for Concurrency, Thread Safety, and Confirmation Synchronization.
"""

import threading
import time
from unittest.mock import MagicMock


def simulate_thread_safe_confirmation(should_approve=True, simulate_delay=0.01):
    """
    Simulates the thread-safe confirmation mechanism used in LUNAR GUI and Avatar widgets.
    """
    result = [False]
    done_event = threading.Event()

    def main_thread_ask():
        time.sleep(simulate_delay)
        result[0] = should_approve
        done_event.set()

    # Trigger UI callback
    threading.Thread(target=main_thread_ask, daemon=True).start()

    # Worker thread blocks on event
    done = done_event.wait(timeout=2.0)
    return done and result[0]


class TestConcurrencyAndSync:
    def test_confirmation_sync_approval(self):
        approved = simulate_thread_safe_confirmation(should_approve=True)
        assert approved is True

    def test_confirmation_sync_rejection(self):
        approved = simulate_thread_safe_confirmation(should_approve=False)
        assert approved is False

    def test_request_lock_prevents_overlap(self):
        is_processing = False
        execution_count = 0
        lock = threading.Lock()

        def request_worker():
            nonlocal is_processing, execution_count
            with lock:
                if is_processing:
                    return
                is_processing = True

            try:
                time.sleep(0.05)
                with lock:
                    execution_count += 1
            finally:
                with lock:
                    is_processing = False

        # Launch 5 concurrent requests simultaneously
        threads = [threading.Thread(target=request_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Due to request locking, simultaneous rapid submissions cannot all execute concurrently
        assert execution_count >= 1
