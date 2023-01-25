def chunk_read(file, chunk_size=4096, mode='rb'):
    while True:
        dat = file.read(chunk_size)

        if not dat:
            break

        yield dat
