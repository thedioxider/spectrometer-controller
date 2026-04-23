"""Context manager that persists motor state on abnormal exit (Ctrl+C / exception)."""


class persist_motor_state_on_exit:
    """Save state for the given motors when the block exits with an exception.

    Usage:
        with persist_motor_state_on_exit(motor_a, motor_b):
            run_the_program()

    On normal (exception-free) exit nothing is written. On KeyboardInterrupt or
    any other exception, each motor's save_state() is called before the
    exception propagates. Save failures are logged and swallowed so that one
    broken motor cannot mask the original exception.
    """

    def __init__(self, *motors):
        self._motors = motors

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is None:
            return False
        reason = exc_type.__name__
        for motor in self._motors:
            try:
                motor.save_state()
            except Exception as err:
                print(f"Failed to save motor state ({reason}): {err}")
        # Treat Ctrl+C as a clean shutdown; let every other exception propagate.
        if issubclass(exc_type, KeyboardInterrupt):
            print("Interrupted; motor state saved")
            return True
        return False
