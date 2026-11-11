#!/bin/bash
# Helpers to edit an ext4 system/vendor image while keeping SELinux labels.
# Use as root, inside your ROM build script:
#
#   source sysimg.sh
#   prep  base/system.ext4 out/system.ext4 1507852288   # copy, fsck, resize to the partition size
#   mnt   out/system.ext4 /mnt/sys                      # loop mount
#   put   overlay/camera.so  /mnt/sys/lib/hw/camera.so  # overwrite in place (keeps inode + label)
#   add   overlay/new.bin    /mnt/sys/etc/firmware/new.bin 644   # new file, label copied from its folder
#   label_like /mnt/sys/etc/x.conf /mnt/sys/etc/y.conf  # copy the label of a reference file
#   finish /mnt/sys out/system.ext4                      # label check, sync, umount, fsck
#
# Every sed -i / cp / mv creates a NEW inode without a label: after one, call
#   relabel <file>        (copies the label of the parent folder's other files, or system_file)
set -e

_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

getlabel() { python3 -I -c "import os,sys
try: print(os.getxattr(sys.argv[1],'security.selinux',follow_symlinks=False).rstrip(b'\0').decode())
except OSError: pass" "$1"; }

setlabel() { python3 -I -c "import os,sys; os.setxattr(sys.argv[1],'security.selinux',sys.argv[2].encode()+b'\0',follow_symlinks=False)" "$1" "$2"; }

# label_like <target> <reference>: give target the same label as reference.
label_like() { local l; l="$(getlabel "$2")"; [ -n "$l" ] || { echo "no label on $2" >&2; return 1; }; setlabel "$1" "$l"; }

# relabel <file>: label from a labelled sibling, else u:object_r:system_file:s0.
relabel() {
  local f="$1" d s l=""
  d="$(dirname "$f")"
  for s in "$d"/*; do
    [ "$s" = "$f" ] && continue
    [ -f "$s" ] || [ -d "$s" ] || continue
    l="$(getlabel "$s")"; [ -n "$l" ] && break
  done
  setlabel "$f" "${l:-u:object_r:system_file:s0}"
}

# prep <source.ext4|sparse.img> <dest.ext4> <partition_bytes>
prep() {
  local src="$1" dst="$2" size="$3" bs blocks
  if [ "$(head -c4 "$src" | od -An -tx1 | tr -d ' ')" = "3aff26ed" ]; then
    simg2img "$src" "$dst"        # sparse image
  else
    cp "$src" "$dst"
  fi
  e2fsck -fy "$dst" >/dev/null || [ $? -le 1 ]
  bs=$(dumpe2fs -h "$dst" 2>/dev/null | awk -F: '/^Block size/{gsub(/ /,"",$2);print $2}')
  blocks=$((size / bs))
  resize2fs "$dst" "$blocks"
  truncate -s "$size" "$dst"
  echo "prep: $dst = $size bytes ($blocks blocks of $bs)"
}

mnt() { mkdir -p "$2"; umount "$2" 2>/dev/null || true; mount -o loop "$1" "$2"; }

# put <src> <dst>: overwrite an existing file in place (inode and label kept).
put() {
  [ -e "$2" ] || { echo "put: $2 does not exist, use add" >&2; return 1; }
  cat "$1" > "$2"
  echo "  put $2 $(md5sum < "$2" | cut -c1-8)"
}

# add <src> <dst> [mode]: new file (or replace), owner 0:0, label from a sibling.
add() {
  mkdir -p "$(dirname "$2")"
  if [ -e "$2" ]; then cat "$1" > "$2"; else cp "$1" "$2"; fi
  chown 0:0 "$2"; chmod "${3:-644}" "$2"; relabel "$2"
  echo "  add $2 $(getlabel "$2")"
}

# finish <mountpoint> <image>
finish() {
  python3 -I "$_HERE/labelchk.py" "$1"
  sync; umount "$1"
  e2fsck -fn "$2" | tail -2
  ls -l "$2"
}
