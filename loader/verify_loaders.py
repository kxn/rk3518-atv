# SPDX-License-Identifier: Apache-2.0
"""Independent LDR parser: bounds, Rockchip CRC, payloads and DDR parameters."""
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent


def crc32_rockchip(data):
    table = []
    for byte in range(256):
        value = byte << 24
        for _ in range(8):
            value = ((value << 1) ^ (0x04C10DB7 if value & 0x80000000 else 0)) & 0xffffffff
        table.append(value)
    value = 0
    for byte in data:
        value = ((value << 8) ^ table[(value >> 24) ^ byte]) & 0xffffffff
    return value


def rc4(data):
    key = bytes([124, 78, 3, 4, 85, 5, 9, 7, 45, 44, 123, 56, 23, 13, 23, 17])
    state = list(range(256))
    j = 0
    for i in range(256):
        j = (j + state[i] + key[i % len(key)]) % 256
        state[i], state[j] = state[j], state[i]
    i = j = 0
    out = bytearray()
    for byte in data:
        i = (i + 1) % 256
        j = (j + state[i]) % 256
        state[i], state[j] = state[j], state[i]
        out.append(byte ^ state[(state[i] + state[j]) % 256])
    return bytes(out)


def params(path):
    return dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)


def main():
    delivery = ROOT / 'delivery'
    manifest = json.loads((delivery / 'manifest.json').read_text())
    report = []
    for item in manifest['loaders']:
        data = (delivery / item['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == item['sha256']
        assert data[:4] == b'LDR '
        assert struct.unpack_from('<H', data, 4)[0] == 102
        assert data[21:25] == b'8253'  # Official RK3528 container chip tag.
        stored_crc = struct.unpack_from('<I', data, len(data) - 4)[0]
        assert crc32_rockchip(data[:-4]) == stored_crc
        entries = []
        regions = []
        for group, position, expected_count in [(1, 25, 2), (2, 31, 1), (4, 37, 3)]:
            count, offset, stride = struct.unpack_from('<BIB', data, position)
            assert count == expected_count and stride == 57
            assert offset >= 102 and offset + count * stride <= 444
            for index in range(count):
                size, kind, name, start, length, delay = struct.unpack_from('<BI40sIII', data, offset + index * stride)
                name = name.decode('utf-16-le').rstrip('\0')
                assert size == 57 and kind == group
                assert start >= 444 and start + length <= len(data) - 4 and length % 2048 == 0
                regions.append((start, start + length))
                payload = data[start:start + length]
                if group == 4:
                    payload = b''.join(rc4(payload[n:n + 512]) for n in range(0, len(payload), 512))
                source = None
                if name in ['UsbHead', 'FlashHead']:
                    assert payload[:4] == b'RKNS'
                elif group == 1 or name == 'FlashData':
                    source = item['ddr_payload']
                elif group == 2:
                    source = 'bin/rk35/rk3528_usbplug_v1.04.bin'
                elif name == 'FlashBoot':
                    source = 'bin/rk35/rk3528_spl_v1.07.bin'
                else:
                    raise AssertionError(f'Unexpected entry {name}')
                if source:
                    original = (ROOT / 'upstream' / source).read_bytes()
                    assert payload[:len(original)] == original, f'Payload mismatch: {name}'
                    assert not any(payload[len(original):]), f'Nonzero padding: {name}'
                entries.append({'name': name, 'type': group, 'offset': start, 'size': length,
                                'delay_ms': delay, 'verified_source': source or 'RKNS header'})
        regions.sort()
        assert regions[0][0] == 444
        assert all(a[1] == b[0] for a, b in zip(regions, regions[1:]))
        assert regions[-1][1] == len(data) - 4
        original_config = ROOT / ('ddr111-parameters.txt' if '111' in item['variant'] else 'ddr-default-parameters.txt')
        before, after = params(original_config), params(delivery / f"{item['variant']}-parameters.txt")
        changed = {k: [before.get(k), v] for k, v in after.items() if before.get(k) != v}
        assert changed == {'lp3_freq': ['1056', '780']}, changed
        assert [after[k] for k in ['lp3_f1_freq_mhz', 'lp3_f2_freq_mhz', 'lp3_f3_freq_mhz']] == ['324', '528', '780']
        report.append({'file': item['file'], 'result': 'PASS', 'crc32': f'{stored_crc:08x}',
                       'ddr_parameter_changes': changed, 'entries': entries, 'hardware_tested': False})
        print('PASS', item['file'], f'CRC={stored_crc:08x}', 'all six entries and DDR parameters verified')
    (delivery / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
