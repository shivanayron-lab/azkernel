#!/bin/bash
# Device survey over adb, read-only. Works on Android or in TWRP; more data with root.
#   bash recon.sh <serial> [report.txt]
# Nothing is written to the device.
set -u
S="${1:?usage: recon.sh <serial> [report.txt]}"
OUT="${2:-recon-$S.txt}"
A() { adb -s "$S" shell "$@" 2>&1 | tr -d '\r'; }
# Root shell if available (su, or already root in recovery).
if [ "$(A id -u)" = "0" ]; then R() { A "$@"; }
elif A su -c id 2>/dev/null | grep -q 'uid=0'; then R() { A su -c "\"$*\""; }
else R() { A "$@"; }; fi
sec() { printf '\n===== %s\n' "$1"; }
{
sec "adb / state"; adb -s "$S" get-state; A id; A getenforce
sec "identity"
for p in ro.product.model ro.product.device ro.product.name ro.product.board ro.product.brand \
         ro.hardware ro.board.platform ro.build.fingerprint ro.build.version.release \
         ro.build.version.sdk ro.build.version.security_patch ro.bootloader ro.boot.bootloader \
         ro.boot.slot_suffix ro.boot.dynamic_partitions ro.treble.enabled ro.boot.verifiedbootstate \
         ro.boot.flash.locked ro.secure ro.debuggable ro.product.cpu.abilist; do
  printf '%s=%s\n' "$p" "$(A getprop $p)"
done
sec "kernel"; A cat /proc/version; echo; A cat /proc/cmdline
A 'ls /proc/config.gz 2>/dev/null && echo "(/proc/config.gz present: adb exec-out cat /proc/config.gz > config.gz)"'
sec "cpu"; A cat /proc/cpuinfo
A 'for c in /sys/devices/system/cpu/cpu[0-9]*; do echo "$c $(cat $c/cpufreq/cpuinfo_min_freq $c/cpufreq/cpuinfo_max_freq $c/cpufreq/scaling_governor 2>/dev/null)"; done'
A cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_frequencies
sec "memory"; A cat /proc/meminfo | head -5
sec "partitions"; R cat /proc/partitions
R 'for d in /dev/block/platform/*/by-name /dev/block/platform/*/*/by-name /dev/block/by-name; do [ -d $d ] && echo "--- $d" && ls -l $d; done'
R 'for b in /sys/class/block/*; do n=${b##*/}; s=$(cat $b/size 2>/dev/null); pn=$(grep -s PARTNAME $b/uevent | cut -d= -f2); echo "$n $((s*512)) $pn"; done'
sec "mounts / fstab"; A cat /proc/mounts; R 'ls /fstab* /vendor/etc/fstab* /odm/etc/fstab* 2>/dev/null; cat /fstab.* /vendor/etc/fstab.* 2>/dev/null'
sec "i2c devices"; A 'for d in /sys/bus/i2c/devices/*; do echo "${d##*/} $(cat $d/name 2>/dev/null)"; done'
sec "input devices"; A cat /proc/bus/input/devices
sec "sound"; A cat /proc/asound/cards; A ls /dev/snd
sec "video / camera"; A 'ls -l /dev/video* 2>/dev/null; for v in /sys/class/video4linux/*; do echo "${v##*/} $(cat $v/name 2>/dev/null)"; done'
sec "display"; A 'cat /sys/class/graphics/fb0/{name,modes,virtual_size,bits_per_pixel} 2>/dev/null'; A wm size; A wm density
sec "modules"; A cat /proc/modules; A 'ls /system/lib/modules /vendor/lib/modules 2>/dev/null'
sec "firmware dirs"; A 'ls -R /system/etc/firmware /vendor/firmware /system/vendor/firmware 2>/dev/null | head -150'
sec "wifi / bt"; A 'getprop | grep -iE "wifi|wlan|bluetooth|bt\." | head -40'; A 'ls /sys/class/net; cat /sys/class/net/lo/operstate'
sec "hal libs"; A 'ls /system/lib/hw /vendor/lib/hw /system/vendor/lib/hw 2>/dev/null'
sec "init rc files"; A 'ls / | grep -E "rc$|fstab|prop$"'
sec "root"; A 'which su; su -v 2>/dev/null; ls -l /system/xbin/su /system/bin/su /sbin/su 2>/dev/null'
sec "dmesg (first 400 lines)"; R dmesg | head -400
} > "$OUT"
echo "report: $OUT ($(wc -l < "$OUT") lines)"
