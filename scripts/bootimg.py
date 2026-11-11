#!/usr/bin/env python3
"""Android boot/recovery image tool (header v0, v1, v2 and legacy Samsung/QCOM dt).

  bootimg.py info   <boot.img>
  bootimg.py unpack <boot.img> <outdir>
  bootimg.py repack --orig <boot.img> [--kernel F] [--ramdisk F] [--second F] [--dt F]
                    [--name S] [--cmdline S] [--pad BYTES] [--no-trailer] --out <new.img>

repack keeps every header field of the original (addresses, page size, os_version,
cmdline) unless overridden, keeps the extra sections (dt, recovery_dtbo, dtb) and the
Samsung SEANDROIDENFORCE trailer, recomputes sizes and the SHA-1 id like mkbootimg.
Header v3/v4 (Android 11+, vendor_boot) is not supported: use magiskboot.
Run with: python3 -I bootimg.py ...
"""
import argparse, hashlib, json, os, struct, sys

MAGIC = b'ANDROID!'
TRAILER = b'SEANDROIDENFORCE'


def align(n, page):
    return (n + page - 1) // page * page


def compression(data):
    sigs = [(b'\x1f\x8b', 'gzip'), (b'\x02\x21\x4c\x18', 'lz4-legacy'), (b'\x04\x22\x4d\x18', 'lz4'),
            (b'\xfd7zXZ', 'xz'), (b'\x5d\x00\x00', 'lzma'), (b'BZh', 'bzip2'), (b'070701', 'cpio')]
    for s, n in sigs:
        if data.startswith(s):
            return n
    return 'unknown'


def parse(b):
    if b[:8] != MAGIC:
        sys.exit('not an Android boot image (no ANDROID! magic)')
    ksz, kaddr, rsz, raddr, ssz, saddr, tags, page, hv, osv = struct.unpack_from('<10I', b, 8)
    if hv in (3, 4):
        sys.exit(f'header v{hv} not supported: use magiskboot')
    h = dict(kernel_addr=kaddr, ramdisk_addr=raddr, second_addr=saddr, tags_addr=tags,
             page_size=page, header_version=hv, os_version=osv,
             name=b[48:64].rstrip(b'\0').decode('latin1'),
             cmdline=(b[64:576].rstrip(b'\0') + b[608:1632].rstrip(b'\0')).decode('latin1'),
             id=b[576:608].hex())
    sizes = [('kernel', ksz), ('ramdisk', rsz), ('second', ssz)]
    if hv in (1, 2):
        dtbo_sz, = struct.unpack_from('<I', b, 1632)
        sizes.append(('recovery_dtbo', dtbo_sz))
        h['header_size'], = struct.unpack_from('<I', b, 1644)
        if hv == 2:
            dtb_sz, = struct.unpack_from('<I', b, 1648)
            h['dtb_addr'], = struct.unpack_from('<Q', b, 1652)
            sizes.append(('dtb', dtb_sz))
    elif hv > 4:
        # Legacy: this field held the dt.img size (old Samsung/QCOM).
        sizes.append(('dt', hv))
        h['legacy_dt'] = True
    off = page
    sec = {}
    for n, sz in sizes:
        sec[n] = b[off:off + sz]
        off += align(sz, page)
    h['end'] = off
    rest = b[off:]
    h['trailer'] = rest.startswith(TRAILER)
    h['image_size'] = len(b)
    return h, sec


def cmd_info(a):
    b = open(a.img, 'rb').read()
    h, sec = parse(b)
    h['sections'] = {n: {'size': len(d), 'format': compression(d) if d else '-'} for n, d in sec.items()}
    print(json.dumps(h, indent=2))


def cmd_unpack(a):
    b = open(a.img, 'rb').read()
    h, sec = parse(b)
    os.makedirs(a.outdir, exist_ok=True)
    for n, d in sec.items():
        if d:
            open(os.path.join(a.outdir, n), 'wb').write(d)
    open(os.path.join(a.outdir, 'header.bin'), 'wb').write(b[:h['page_size']])
    h['sections'] = {n: {'size': len(d), 'format': compression(d) if d else '-'} for n, d in sec.items()}
    json.dump(h, open(os.path.join(a.outdir, 'info.json'), 'w'), indent=2)
    print(f"unpacked to {a.outdir}: " + ', '.join(f'{n}={len(d)}' for n, d in sec.items() if d))
    print('ramdisk format:', h['sections']['ramdisk']['format'])


def cmd_repack(a):
    b = open(a.orig, 'rb').read()
    h, sec = parse(b)
    page = h['page_size']
    for n in ('kernel', 'ramdisk', 'second', 'dt'):
        f = getattr(a, n)
        if f:
            if n == 'dt' and 'dt' not in sec:
                sys.exit('original image has no legacy dt section')
            sec[n] = open(f, 'rb').read()
    hdr = bytearray(b[:page])
    struct.pack_into('<I', hdr, 8, len(sec['kernel']))
    struct.pack_into('<I', hdr, 16, len(sec['ramdisk']))
    struct.pack_into('<I', hdr, 24, len(sec['second']))
    if h.get('legacy_dt'):
        struct.pack_into('<I', hdr, 40, len(sec['dt']))
    if 'recovery_dtbo' in sec:
        struct.pack_into('<I', hdr, 1632, len(sec['recovery_dtbo']))
    if 'dtb' in sec:
        struct.pack_into('<I', hdr, 1648, len(sec['dtb']))
    if a.name is not None:
        hdr[48:64] = a.name.encode()[:15].ljust(16, b'\0')
    if a.cmdline is not None:
        c = a.cmdline.encode()
        if len(c) > 512 + 1023:
            sys.exit('cmdline too long')
        # Like mkbootimg: first 512 bytes in cmdline, the rest in extra_cmdline.
        hdr[64:576] = c[:512].ljust(512, b'\0')
        hdr[608:1632] = c[512:].ljust(1024, b'\0')
    # id = SHA-1 over each section and its size (as mkbootimg does)
    sha = hashlib.sha1()
    for n in ('kernel', 'ramdisk', 'second'):
        sha.update(sec[n]); sha.update(struct.pack('<I', len(sec[n])))
    if h.get('legacy_dt'):
        sha.update(sec['dt']); sha.update(struct.pack('<I', len(sec['dt'])))
    if 'recovery_dtbo' in sec:
        sha.update(sec['recovery_dtbo']); sha.update(struct.pack('<I', len(sec['recovery_dtbo'])))
    if 'dtb' in sec:
        sha.update(sec['dtb']); sha.update(struct.pack('<I', len(sec['dtb'])))
    hdr[576:608] = sha.digest().ljust(32, b'\0')
    out = bytes(hdr)
    for n, d in sec.items():
        out += d + bytes(align(len(d), page) - len(d))
    if h['trailer'] and not a.no_trailer:
        out += TRAILER
    if a.pad:
        if len(out) > a.pad:
            sys.exit(f'image {len(out)} bytes is larger than --pad {a.pad} (partition size)')
        out = out.ljust(a.pad, b'\0')
    open(a.out, 'wb').write(out)
    print(f"{a.out}: {len(out)} bytes, kernel {len(sec['kernel'])}, ramdisk {len(sec['ramdisk'])} "
          f"({compression(sec['ramdisk'])}), md5 {hashlib.md5(out).hexdigest()}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest='cmd', required=True)
    i = s.add_parser('info'); i.add_argument('img'); i.set_defaults(f=cmd_info)
    u = s.add_parser('unpack'); u.add_argument('img'); u.add_argument('outdir'); u.set_defaults(f=cmd_unpack)
    r = s.add_parser('repack')
    r.add_argument('--orig', required=True); r.add_argument('--out', required=True)
    for n in ('kernel', 'ramdisk', 'second', 'dt', 'name', 'cmdline'):
        r.add_argument('--' + n)
    r.add_argument('--pad', type=int, help='pad to this size (partition size); fails if larger')
    r.add_argument('--no-trailer', action='store_true', help='drop the Samsung SEANDROIDENFORCE trailer')
    r.set_defaults(f=cmd_repack)
    a = p.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
