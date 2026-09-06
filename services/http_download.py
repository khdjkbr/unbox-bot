import os


async def save_response(response, path):
    """Remove incomplete downloads on failure, including cancellation."""
    size = 0
    try:
        response.raise_for_status()
        with open(path, 'wb') as output:
            async for chunk in response.content.iter_chunked(64 * 1024):
                size += len(chunk)
                if size > 50 * 1024 * 1024:
                    raise ValueError('Media exceeds 50 MB')
                output.write(chunk)
        if not size:
            raise ValueError('Empty media response')
        return path
    except BaseException:
        if os.path.exists(path):
            os.remove(path)
        raise
