_POLYNOMIAL = 0xEDB88320


def crc32(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ _POLYNOMIAL
            else:
                crc >>= 1
    return crc ^ 0xFFFFFFFF
