#!/usr/bin/env bash
# Build MRiscoC ProUI for the Voxelab Aquila X2 (HC32F460, env HC32F460C_aquila_101).
# Usage: ./build.sh <cfg> [sufijo] [nota]    <cfg> = folder in "configurations/Voxelab Aquila HC32/"; [nota] replaces the bin name in out/SIZES.md
set -euo pipefail
CFG=${1:?usage: ./build.sh <cfg> [sufijo] [nota]}
SUFIJO=${2:-}
NOTA=${3:-}
PIOENV=HC32F460C_aquila_101
MAX=212992  # 256 KiB flash minus the 48 KiB bootloader (app starts at 0xC000)
cd "$(dirname "$0")"
. .venv/bin/activate
export PLATFORMIO_CORE_DIR="$PWD/.pio-core"
# random-bin.py runs xdg-open on the build dir: with no display and no known desktop it opens nothing
export DISPLAY= WAYLAND_DISPLAY= XDG_CURRENT_DESKTOP=X-Generic

# Always restore the tracked copies in Marlin/, whether the build succeeds or fails
trap 'git checkout -- Marlin/Configuration.h Marlin/Configuration_adv.h Marlin/Version.h' EXIT
cp "configurations/Voxelab Aquila HC32/$CFG/"{Configuration.h,Configuration_adv.h,Version.h} Marlin/

mkdir -p out
rm -rf ".pio/build/$PIOENV"
pio run -e "$PIOENV" 2>&1 | tee "out/build-$CFG.log"

BINS=(".pio/build/$PIOENV"/firmware-*.bin)
[ ${#BINS[@]} -eq 1 ] && [ -f "${BINS[0]}" ] || { echo "expected exactly one firmware-*.bin"; exit 1; }
BIN=${BINS[0]}
SIZE=$(stat -c%s "$BIN")
[ "$SIZE" -le "$MAX" ] || { echo "FLASH OVERFLOW $SIZE"; exit 1; }

# ProUI-EX on HC32 links the GD32F10 (Maple HAL) libproui.a: fail if the Maple-layout code that custom_gcodes.cpp replaces got linked
if grep -q '^ *#define PROUI_EX' Marlin/Configuration.h; then
  TC="$PLATFORMIO_CORE_DIR/packages/toolchain-gccarmnoneeabi/bin"; ELF="${BIN%.bin}.elf"
  BAD=$("$TC/arm-none-eabi-nm" -C "$ELF" | grep -E 'ProUIClass::C(29|412|562|810)(_report)?\(' || true)
  for S in _Z17serial_echopair_PIsEvPKcT_ _Z19serial_echolnpair_PIsEvPKcT_ _ZN18FilamentSensorBase16poll_runout_pinsEv _Z11SERIAL_ECHOIfEvT_ _Z11SERIAL_ECHOIPcEvT_; do
    A=$("$TC/arm-none-eabi-nm" "$ELF" | awk -v s="$S" '$3 == s { print $1 }')
    [ -z "$A" ] || [[ $("$TC/arm-none-eabi-addr2line" -e "$ELF" "0x$A") == */Marlin/src/* ]] || BAD+=$'\n'"$S at 0x$A is not from Marlin/src"
  done
  [ -z "$BAD" ] || { printf 'HC32 libproui checks: FAILED\n%s\n' "$BAD"; exit 1; }
  echo "HC32 libproui checks: OK"
fi

"$PLATFORMIO_CORE_DIR/packages/toolchain-gccarmnoneeabi/bin/arm-none-eabi-size" "${BIN%.bin}.elf"
OUT="out/HC32_${CFG}${SUFIJO}-$(date +%Y%m%d).bin"
cp "$BIN" "$OUT"
LIBRES=$((MAX - SIZE))
echo "$OUT: $SIZE bytes, libres=$LIBRES"
[ -f out/SIZES.md ] || printf '| fecha | cfg | bytes | libres | nota |\n|---|---|---|---|---|\n' > out/SIZES.md
echo "| $(date '+%Y-%m-%d %H:%M') | $CFG | $SIZE | $LIBRES | ${NOTA:-$(basename "$OUT")} |" >> out/SIZES.md
