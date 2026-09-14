#!/bin/bash
# Automated two-emulator walkie-talkie loop test under emulator network shaping.
# For each speed preset: fresh app start on A and B → wait for NSD connection → A sends
# N messages (last one ALERT) → B must show exactly N bubbles, correct text, ALERT chip,
# no duplicates. Latency = host clock between the PTT release and the bubble appearing on B,
# plus the precise device-side tx/rx epoch stamps from the iTantraLink logcat tag.
# Usage: app/tools/loop_test.sh [apk]      (env: A, B, SPEEDS, OUT)
set -u
SDK=${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}
ADB=$SDK/platform-tools/adb
A=${A:-emulator-5554}; B=${B:-emulator-5556}
APK=${1:-app/build/outputs/apk/debug/itantra-debug.apk}
PKG=com.nullpointers.itantra
# emulator presets: speed name or up:down kbps; delay name or min:max ms
SPEEDS=${SPEEDS:-"full:none gsm:gsm edge:edge 1:1000"}
OUT=${OUT:-app/testlogs}; mkdir -p "$OUT" app/screenshots
MSGS=("Water rising near the bridge" "Send boats to ward 7" "Cyclone landfall in 2 hours evacuate")
ALERT_IDX=2

dump() { $ADB -s "$1" shell uiautomator dump /sdcard/d.xml >/dev/null 2>&1; $ADB -s "$1" shell cat /sdcard/d.xml 2>/dev/null; }
center() { # dev resource-id → "x y"
  dump "$1" | python3 -c "
import re,sys
x=sys.stdin.read(); m=re.search(r'resource-id=\"$PKG:id/$2\"[^>]*bounds=\"\[(\d+),(\d+)\]\[(\d+),(\d+)\]\"',x)
print((int(m.group(1))+int(m.group(3)))//2,(int(m.group(2))+int(m.group(4)))//2) if m else print('')"
}
texts() { dump "$1" | python3 -c "import re,sys; print('\n'.join(re.findall(r'text=\"([^\"]*)\"',sys.stdin.read())))"; }
start() { # launcher is ConnectActivity (MainActivity is not exported): open it and tap "find peers"
  $ADB -s $1 shell am start -n $PKG/.ConnectActivity >/dev/null; sleep 2
  read fx fy <<<"$(center $1 findPeers)"; [ -n "${fx:-}" ] && $ADB -s $1 shell input tap $fx $fy; sleep 1; }
restart() { for d in $A $B; do $ADB -s $d shell am force-stop $PKG; start $d; done; sleep 3; }
shape() { for d in $A $B; do $ADB -s $d emu network speed "$1" >/dev/null; $ADB -s $d emu network delay "$2" >/dev/null; done; }
connected() { for i in $(seq 1 30); do texts "$1" | grep -q "connected" && return 0; sleep 2; done; return 1; }

echo "== install"; for d in $A $B; do $ADB -s $d install -r -g "$APK" >/dev/null && echo "  $d ok"; done
for d in $A $B; do $ADB -s $d shell settings put secure user_setup_complete 1 >/dev/null 2>&1; done

printf "\n| speed:delay | connected | bubbles on B | dupes | ALERT chip | latency host (ms) | latency logcat (ms) | result |\n|---|---|---|---|---|---|---|---|\n" | tee "$OUT/summary.md"
for sd in $SPEEDS; do
  spd=${sd%%:*}; dly=${sd#*:}
  shape "$spd" "$dly"; restart
  for d in $A $B; do $ADB -s $d logcat -c; done
  conn="✗"; connected $B && connected $A && conn="✓"
  lats=(); fail=0
  read ax ay <<<"$(center $A alert)"
  for i in "${!MSGS[@]}"; do
    m=${MSGS[$i]}
    [ $i -eq $ALERT_IDX ] && $ADB -s $A shell input tap $ax $ay
    t0=$(python3 -c 'import time;print(int(time.time()*1000))')
    # the `say` extra sends text exactly as the typed/STT path would (works with or without a voice pack; `input text` can't type Devanagari)
    $ADB -s $A shell am start -n $PKG/.MainActivity --es say "'$m'" >/dev/null
    got=0; for k in $(seq 1 60); do texts $B | grep -qF "$m" && { got=1; break; }; sleep 0.5; done
    t1=$(python3 -c 'import time;print(int(time.time()*1000))')
    [ $got = 1 ] && lats+=($((t1-t0))) || { lats+=("timeout"); fail=1; }
  done
  bt=$(texts $B); n=0; dup=0
  for m in "${MSGS[@]}"; do c=$(grep -cF "$m" <<<"$bt"); n=$((n+c)); [ $c -gt 1 ] && dup=$((dup+c-1)); done
  alert="✗"; grep -q "ALERT" <<<"$bt" && alert="✓"
  # device-side: pair tx seq on A with rx seq on B via logcat epoch stamps (emulators share the host clock)
  lc=$( { $ADB -s $A logcat -d -s iTantraLink; $ADB -s $B logcat -d -s iTantraLink; } | python3 -c "
import re,sys
tx={};rx={}
for l in sys.stdin:
    m=re.search(r'(tx|rx) seq=(\d+) bytes=\d+ t=(\d+)',l)
    if m: (tx if m.group(1)=='tx' else rx)[int(m.group(2))]=int(m.group(3))
d=[rx[s]-tx[s] for s in tx if s in rx]
print(','.join(map(str,d)) if d else '-')")
  res="PASS"; [ $fail = 1 ] || [ $n -ne ${#MSGS[@]} ] || [ $dup -ne 0 ] || [ $alert = "✗" ] || [ $conn = "✗" ] && res="FAIL"
  echo "| $sd | $conn | $n/${#MSGS[@]} | $dup | $alert | ${lats[*]} | $lc | $res |" | tee -a "$OUT/summary.md"
  $ADB -s $B exec-out screencap -p > "app/screenshots/loop-${spd}.png" 2>/dev/null
  { echo "### $sd"; $ADB -s $A logcat -d -s iTantraLink AndroidRuntime:E; $ADB -s $B logcat -d -s iTantraLink AndroidRuntime:E; } > "$OUT/logcat-${spd}.txt"
done
shape full none
echo; grep -c FAIL "$OUT/summary.md" | xargs -I{} sh -c '[ {} = 0 ] && echo "ALL PASS" || echo "{} FAILED"'
