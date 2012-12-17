import contextlib
import mmap
import string
import binascii
import re
import os

class InvalidSegmentException(Exception): pass

yenc42 = string.join(map(lambda x: chr((x-42) & 255), range(256)), "")
yenc64 = string.join(map(lambda x: chr((x-64) & 255), range(256)), "")

# Decode a YENC-encoded message into a list of string fragments.
def yenc_decode(lines):
    buffer = []
    for line in lines:
        # Trim mandatory returns from lines.
        if line[-2:] == "\r\n":
            line = line[:-2]
        elif line[-1:] in "\r\n":
            line = line[:-1]

        # Not even sure: http://effbot.org/zone/yenc-decoder.htm
        data = string.split(line, "=")
        buffer.append(string.translate(data[0], yenc42))
        for data in data[1:]:
            data = string.translate(data, yenc42)
            buffer.append(string.translate(data[0], yenc64))
            buffer.append(data[1:])
    return ''.join(buffer)

def read_segment_file(fp):
    # Check to make sure header is present
    lines = fp.readlines()
    if lines[0].strip() == '':
        lines.pop(0)
    line = lines[0]
    if not line.startswith('=ybegin'):
        #print line, len(line.strip())
        raise InvalidSegmentException('Not a Segment, =ybegin does not appear first')
    header = parse_yenc_header(line)

    # For us, we depend on the part header also.
    line = lines[1]
    if not line.startswith('=ypart'):
        raise InvalidSegmentException('Segment has no Part')
    part = parse_yenc_header(line)

    line = lines[-1]
    if not line.startswith('=yend'):
        raise InvalidSegmentException('Segment has no End')
    trail = parse_yenc_header(line)

    # Read rest of file.
    body = yenc_decode(lines[2:-1])
    return header, part, body, trail

def read_segment(filename):
    with open(filename, 'rb') as fp:
        return read_segment_file(fp)

def check_crc(trail, data):
    crc = binascii.crc32(data) & 0xffffffff
    crc_str = '%08x' % crc
    return crc_str == trail['pcrc32']

# Example: =ybegin part=1 line=128 size=123 name=-=DUMMY=- abc.par
YSPLIT_RE = re.compile(r'([a-zA-Z0-9]+)=')
def parse_yenc_header(line, splits=None):
    fields = {}

    if splits:
        parts = YSPLIT_RE.split(line, splits)[1:]
    else:
        parts = YSPLIT_RE.split(line)[1:]

    if len(parts) % 2:
        return fields

    for i in range(0, len(parts), 2):
        key, value = parts[i], parts[i+1]
        fields[key] = value.strip()

    return fields

def head(f, window=1):
    f.seek(0)
    data = [f.readline() for i in range(window)]
    return data

def tail(f, window=1):
    BUFFER_SIZE = 1024
    f.seek(0, os.SEEK_END)
    bytes = f.tell()
    size = window
    block = -1
    data = []
    while size > 0 and bytes > 0:
        if (bytes - BUFFER_SIZE > 0):
            f.seek(block * BUFFER_SIZE, os.SEEK_END) # Seek back one whole BUFSIZ
            data.append(f.read(BUFFER_SIZE)) # read BUFFER
        else:
            f.seek(0, os.SEEK_SET) # file too small, start from begining
            data.append(f.read(bytes)) # only read what was not read
        linesFound = data[-1].count('\n')
        size -= linesFound
        bytes -= BUFFER_SIZE
        block -= 1
    return '\n'.join(''.join(data).splitlines()[-window:])
