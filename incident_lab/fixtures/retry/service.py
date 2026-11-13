async def charge(send, max_attempts=3):
    """Retry transient payment timeouts within the configured attempt budget."""
    attempt = 0
    while attempt <= max_attempts:
        attempt += 1
        try:
            return await send()
        except TimeoutError:
            if attempt > max_attempts:
                raise
