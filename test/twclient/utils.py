'''
Utilities for twclient tests
'''

def chunk_read(file, chunk_size=4096):
    '''
    Yield successive chunks of a file-like object
    '''

    while True:
        dat = file.read(chunk_size)

        if not dat:
            break

        yield dat
