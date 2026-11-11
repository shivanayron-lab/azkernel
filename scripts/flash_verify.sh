#!/bin/bash
# Back up, write and verify one partition over adb (TWRP or a rooted/debug Android).
#   bash flash_verify.sh <serial> <block device> <image> [backup_dir]
# Example: bash flash_verify.sh <serial> /dev/block/mmcblk0p9 kernel.img backups/
# The image may be smaller than the partition: only its bytes are compared.
# ASK THE OWNER BEFORE RUNNING: this overwrites a partition.
set -eu
S="$1"; DEV="$2"; IMG="$3"; BK="${4:-.}"
A() { adb -s "$S" shell "$@" | tr -d '\r'; }
if [ "$(A id -u)" = "0" ]; then SU() { A "$@"; }
else SU() { A su -c "\"$*\""; }; fi
BB=""; for b in /sbin/busybox /system/xbin/busybox /system/bin/busybox; do
  [ "$(A "[ -x $b ] && echo y")" = y ] && { BB="$b "; break; }
done
N=$(stat -c %s "$IMG")
PSIZE=$(SU "${BB}blockdev --getsize64 $DEV")
[ "$N" -le "$PSIZE" ] || { echo "image $N > partition $PSIZE: abort"; exit 1; }
want=$(md5sum < "$IMG" | cut -d' ' -f1)
T=/data/local/tmp; [ "$(A "[ -d /tmp ] && [ -w /tmp ] && echo y")" = y ] && T=/tmp
name=$(basename "$DEV")
echo "== backup $DEV ($PSIZE bytes)"
mkdir -p "$BK"
SU "dd if=$DEV of=$T/bk-$name.img bs=1048576 2>/dev/null"
adb -s "$S" pull "$T/bk-$name.img" "$BK/$name-$(date +%Y%m%d-%H%M%S).img" >/dev/null
SU "rm -f $T/bk-$name.img"
echo "== push + write $IMG ($N bytes, md5 $want)"
adb -s "$S" push "$IMG" "$T/next.img" >/dev/null
got=$(SU "${BB}md5sum $T/next.img" | cut -d' ' -f1)
[ "$got" = "$want" ] || { echo "push corrupted ($got): abort, nothing written"; exit 1; }
SU "dd if=$T/next.img of=$DEV bs=1048576 2>/dev/null; sync"
got=$(SU "${BB}head -c $N $DEV | ${BB}md5sum" | cut -d' ' -f1)
SU "rm -f $T/next.img"
if [ "$got" = "$want" ]; then echo "OK: $DEV verified ($got)"
else echo "VERIFY FAILED ($got != $want). Do not reboot: rewrite or restore the backup in $BK"; exit 2; fi
