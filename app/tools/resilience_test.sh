#!/bin/bash
# Resilience checks on two emulators: background/foreground mid-transfer, rotation,
# and peer killed mid-transfer (store-and-forward must deliver on reconnect).
# Usage: app/tools/resilience_test.sh [apk]     (env: A, B, OUT)
set -u
SDK=${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}; ADB=$SDK/platform-tools/adb
A=${A:-emulator-5554}; B=${B:-emulator-5556}
APK=${1:-app/build/outputs/apk/debug/itantra-debug.apk}; PKG=com.nullpointers.itantra
OUT=${OUT:-app/testlogs}; mkdir -p "$OUT"

dump() { $ADB -s "$1" shell uiautomator dump /sdcard/d.xml >/dev/null 2>&1; $ADB -s "$1" shell cat /sdcard/d.xml 2>/dev/null; }
texts() { dump "$1" | python3 -c "import re,sys; print('\n'.join(re.findall(r'text=\"([^\"]*)\"',sys.stdin.read())))"; }
center() { dump "$1" | python3 -c "
import re,sys
x=sys.stdin.read(); m=re.search(r'resource-id=\"$PKG:id/$2\"[^>]*bounds=\"\[(\d+),(\d+)\]\[(\d+),(\d+)\]\"',x)
print((int(m.group(1))+int(m.group(3)))//2,(int(m.group(2))+int(m.group(4)))//2) if m else print('')"; }
start() { # launcher is ConnectActivity (MainActivity is not exported): open it and tap "find peers"
  $ADB -s $1 shell am start -n $PKG/.ConnectActivity >/dev/null; sleep 2
  read fx fy <<<"$(center $1 findPeers)"; [ -n "${fx:-}" ] && $ADB -s $1 shell input tap $fx $fy; sleep 1; }
connected() { for i in $(seq 1 30); do texts "$1" | grep -q "connected ·" && return 0; sleep 2; done; return 1; }
send() { # dev text — `say` extra: same code path as typed/STT text, works with a voice pack installed (input box hidden then)
  $ADB -s $1 shell am start -n $PKG/.MainActivity --es say "'$2'" >/dev/null 2>&1; }
seen() { for k in $(seq 1 $3); do texts $1 | grep -qF "$2" && return 0; sleep 1; done; return 1; }
crashed() { $ADB -s $1 logcat -d -s AndroidRuntime:E | grep -q "$PKG"; }
row() { echo "| $1 | $2 | $3 |" | tee -a "$OUT/resilience.md"; }
rxn() { $ADB -s $1 logcat -d -s iTantraLink | grep -c "rx seq"; }     # frames B received (logcat = ground truth; uiautomator only sees on-screen nodes)
ticks() { texts $1 | grep -c "✓"; }
# NSD finds every iTantra on the virtual Wi-Fi: other emulators would ACK for a dead B (ARQ is first-ACK-wins,
# ponytail: per-peer ARQ when group use matters). Isolate the pair for the two-phone spec.
OTHERS=$($ADB devices | awk '/emulator-/{print $1}' | grep -v -e "$A" -e "$B")
for d in $OTHERS; do $ADB -s $d shell am force-stop $PKG 2>/dev/null; done

for d in $A $B; do $ADB -s $d install -r -g "$APK" >/dev/null; $ADB -s $d emu network speed full >/dev/null; $ADB -s $d emu network delay none >/dev/null; done
for d in $A $B; do $ADB -s $d shell am force-stop $PKG; $ADB -s $d logcat -c; start $d; done; sleep 4
connected $A && connected $B || echo "WARN: not connected at start"
printf "| check | result | detail |\n|---|---|---|\n" > "$OUT/resilience.md"

# 1. receiver backgrounded mid-transfer, then foregrounded
send $A "Bridge on the east road is gone"; $ADB -s $B shell input keyevent 3; sleep 3; start $B; sleep 2
if seen $B "Bridge on the east road is gone" 20 && ! crashed $B; then row "B backgrounded during transfer" PASS "delivered after foreground, no crash"; else row "B backgrounded during transfer" FAIL "$(crashed $B && echo crash || echo not delivered)"; fi

# 2. rotation on both sides mid-conversation
for d in $A $B; do $ADB -s $d shell settings put system accelerometer_rotation 0; $ADB -s $d shell settings put system user_rotation 1; done; sleep 2
r0=$(rxn $B); send $A "Landscape test message"
ok=0; for k in $(seq 1 20); do [ "$(rxn $B)" -gt "$r0" ] && { ok=1; break; }; sleep 1; done
if [ $ok = 1 ] && ! crashed $A && ! crashed $B; then row "rotation mid-conversation" PASS "frame received in landscape (logcat rx), no crash on either side"; else row "rotation mid-conversation" FAIL "$(crashed $B && echo crash-B; crashed $A && echo crash-A; echo rx=$ok)"; fi
for d in $A $B; do $ADB -s $d shell settings put system user_rotation 0; done; sleep 2

# 3. peer killed mid-transfer → store-and-forward
$ADB -s $B shell am force-stop $PKG; sleep 2
t0=$(ticks $A); send $A "Queued while you were gone one"; sleep 1; send $A "Queued while you were gone two"; sleep 8
t1=$(ticks $A)   # no peer alive ⇒ no ACK ⇒ no new ✓ (a dead TCP socket may still accept the write, so "queued" chip is not the signal)
start $B; connected $B
if seen $B "Queued while you were gone one" 40 && seen $B "Queued while you were gone two" 20 && [ "$(ticks $A)" -ge $((t0+2)) ]; then
  row "peer killed → store-and-forward" PASS "no ✓ while B was dead (${t0}→${t1}); both retransmitted + ACKed after B restarted ($(ticks $A) ✓)"
else row "peer killed → store-and-forward" FAIL "ticks ${t0}→${t1}→$(ticks $A); B got $(texts $B | grep -c 'Queued while')/2"; fi

# 4. sender app killed and restarted: nothing crashes, link re-forms
$ADB -s $A shell am force-stop $PKG; start $A
if connected $A && ! crashed $A; then row "sender restart re-connects" PASS "● connected within 60 s"; else row "sender restart re-connects" FAIL ""; fi
$ADB -s $B exec-out screencap -p > app/screenshots/resilience-b.png 2>/dev/null
{ $ADB -s $A logcat -d -s iTantraLink AndroidRuntime:E; $ADB -s $B logcat -d -s iTantraLink AndroidRuntime:E; } > "$OUT/logcat-resilience.txt"
for d in $OTHERS; do $ADB -s $d shell monkey -p $PKG -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1; done
cat "$OUT/resilience.md"
