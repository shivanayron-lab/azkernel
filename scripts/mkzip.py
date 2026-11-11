#!/usr/bin/env python3
"""Build a TWRP flashable zip from raw partition images, driven by a JSON config.

  python3 -I mkzip.py config.json

The installer (update-binary, plain sh + TWRP busybox):
  1. refuses listed models, warns on similar ones;
  2. checks every partition's by-name link AND size before writing anything;
  3. checks the sha256 of each image inside the zip;
  4. writes, reads back and compares (retries the write once);
  5. never touches recovery or data.
See references/05-empacotar-instalar.md for the config format.
"""
import datetime, gzip, hashlib, json, os, shutil, stat, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(sys.argv[1]))
date = datetime.date.today().strftime('%Y%m%d')
release = cfg['release']
out_dir = cfg.get('out_dir', '.')
os.makedirs(out_dir, exist_ok=True)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def q(s):  # single-quote for sh
    return "'" + str(s).replace("'", "'\\''") + "'"


tmp = tempfile.mkdtemp()
parts, meta_parts, sums = [], {}, ''
for p in cfg['partitions']:
    img = p['image']
    n = os.path.getsize(img)
    assert n <= p['size'], f"{img}: {n} bytes > partition {p['name']} {p['size']}"
    raw_sha = sha(img)
    payload = img
    if p.get('gzip'):
        payload = os.path.join(tmp, p['entry'])
        with open(img, 'rb') as fi, gzip.open(payload, 'wb', 6) as fo:
            shutil.copyfileobj(fi, fo, 1 << 20)
    entry_sha = sha(payload)
    parts.append(dict(p, bytes=n, raw_sha=raw_sha, entry_sha=entry_sha, payload=payload))
    meta_parts[p['name']] = {'dev': p['dev'], 'size': p['size'], 'image_bytes': n,
                             'image_sha256': raw_sha, 'entry': p['entry'], 'entry_sha256': entry_sha}
    sums += f"{entry_sha}  {p['entry']}\n"

# update-binary ---------------------------------------------------------------
ub = open(os.path.join(HERE, 'update-binary.tmpl')).read().replace('\r\n', '\n')
case = ''
for r in cfg.get('refuse', []):
    case += f"    {r['match']}) abort {q(r['msg'])} ;;\n"
for w in cfg.get('warn', []):
    case += f"    {w['match']}) ui_print \"! ${{MODEL:-$DEVICE}}: \"{q(w['msg'])} ;;\n"
checks = ''.join(f"check_part {q(p['by_name'])} {q(p['dev'])} {p['size']}\n" for p in parts)
pkg = ''.join(f"check_entry {q(p['entry'])} {p['entry_sha']}\n" for p in parts)
flash = ''.join(f"flash_part {q(p['name'])} {q(p['dev'])} {q(p['entry'])} {1 if p.get('gzip') else 0} "
                f"{p['bytes']} {p['raw_sha']}\n" for p in parts)
notes = ''.join(f"ui_print {q(n)}\n" for n in cfg.get('after_notes', []))
for k, v in {'@ROM_NAME@': cfg['rom_name'], '@DEVICE_TITLE@': cfg['device_title'], '@RELEASE@': release,
             '@MODEL_CASE@': case, '@PART_CHECKS@': checks, '@PKG_CHECKS@': pkg, '@FLASH@': flash,
             '@NOTES@': notes}.items():
    assert ub.count(k) >= 1, k
    ub = ub.replace(k, v)
assert '@' not in ''.join(l for l in ub.splitlines() if l.startswith('@')), 'unfilled placeholder'

meta = {'rom': cfg['rom_name'], 'device': cfg['device_title'], 'release': release, 'date': date,
        'partitions': meta_parts}
zip_name = cfg.get('zip_name', 'rom-{date}-{release}.zip').format(date=date, release=release)
out = os.path.join(out_dir, zip_name)
y, m, d = int(date[:4]), int(date[4:6]), int(date[6:])
entries = [(p['entry'], p['payload'], zipfile.ZIP_STORED if p.get('gzip') else zipfile.ZIP_DEFLATED, 0o644)
           for p in parts]
entries += [
    ('META-INF/com/google/android/update-binary', ub.encode(), zipfile.ZIP_DEFLATED, 0o755),
    ('META-INF/com/google/android/updater-script', b'# Installation logic is in update-binary.\n',
     zipfile.ZIP_DEFLATED, 0o644),
    ('release-metadata.json', (json.dumps(meta, indent=2) + '\n').encode(), zipfile.ZIP_DEFLATED, 0o644),
    ('SHA256SUMS', sums.encode(), zipfile.ZIP_DEFLATED, 0o644),
]
if cfg.get('readme'):
    entries.append(('README.md', open(cfg['readme'], 'rb').read(), zipfile.ZIP_DEFLATED, 0o644))
with zipfile.ZipFile(out, 'w', allowZip64=True) as z:
    for name, data, method, mode in entries:
        info = zipfile.ZipInfo(name, (y, m, d, 0, 0, 0))
        info.compress_type = method
        info.external_attr = (stat.S_IFREG | mode) << 16
        if isinstance(data, bytes):
            z.writestr(info, data)
        else:
            with open(data, 'rb') as fi, z.open(info, 'w', force_zip64=True) as fo:
                shutil.copyfileobj(fi, fo, 1 << 20)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
shutil.rmtree(tmp)
print(json.dumps({'zip': out, 'bytes': os.path.getsize(out), 'sha256': sha(out), **meta}, indent=2))
