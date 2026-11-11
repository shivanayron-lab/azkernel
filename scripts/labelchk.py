#!/usr/bin/env python3
"""List files in a mounted system/vendor image that have no SELinux label (or 'unlabeled').

  python3 -I labelchk.py <mountpoint>
Exit code 1 if any file is unlabeled. Run as root.
"""
import os, sys

root = sys.argv[1].rstrip('/')
bad = 0
for d, dirs, files in os.walk(root):
    for n in dirs + files:
        p = os.path.join(d, n)
        try:
            label = os.getxattr(p, 'security.selinux', follow_symlinks=False)
        except OSError:
            label = b''
        if not label or b'unlabeled' in label:
            print('UNLABELED', p[len(root):] or '/')
            bad += 1
print('unlabeled:', bad)
sys.exit(1 if bad else 0)
