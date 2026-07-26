# Sanitizers

All verified 2026-07-26 against deliberately-broken programs — each one below
actually trapped its bug on this machine.

Sanitizers are **runtime** tools. They find bugs on code paths your tests
actually execute; they prove nothing about paths you never run. Pair with
coverage.

## Availability

| Sanitizer | gcc 15 | clang 21 | Rust (nightly) | Catches |
|---|---|---|---|---|
| ASan | yes | yes | yes | use-after-free, buffer overflow, double-free |
| LSan | yes | yes | yes | memory leaks (bundled into ASan) |
| UBSan | yes | yes | — | UB: overflow, bad shift, misaligned, null deref |
| TSan | yes | yes | yes | data races, lock-order inversion |
| MSan | **no** | yes | yes | reads of uninitialized memory |
| Integer | no | yes | — | unsigned wraparound, lossy truncation |

MSan is clang-only — gcc has never implemented it.

## Build flags

```bash
# ASan + LSan + UBSan — the default pairing for a debug/test build.
# ASan and TSan cannot be combined; they use incompatible shadow memory.
g++ -fsanitize=address,undefined -fno-sanitize-recover=all \
    -fno-omit-frame-pointer -g -O1 prog.cpp -o prog

# TSan — separate build.
g++ -fsanitize=thread -fno-omit-frame-pointer -g -O1 prog.cpp -o prog

# MSan — clang only, and see the caveat below.
clang++ -fsanitize=memory -fsanitize-memory-track-origins=2 \
        -fPIE -pie -fno-omit-frame-pointer -g -O1 prog.cpp -o prog
```

`-fno-sanitize-recover=all` is what makes UBSan **abort** instead of printing
and continuing. Without it a UBSan finding does not fail your test run.

`-O1` and `-fno-omit-frame-pointer` give usable stack traces. `-O0` works but
runs slower; `-O2`+ inlines away frames you want to see.

## Runtime options

```bash
export ASAN_OPTIONS=detect_leaks=1:abort_on_error=1:strict_string_checks=1:detect_stack_use_after_return=1:check_initialization_order=1
export UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1
export TSAN_OPTIONS=halt_on_error=1:second_deadlock_stack=1
export LSAN_OPTIONS=suppressions=.lsan-suppressions.txt
```

`detect_stack_use_after_return=1` catches a whole bug class off by default.

## CMake preset

```cmake
option(ENABLE_SANITIZERS "Build with ASan+UBSan" OFF)
if(ENABLE_SANITIZERS)
  add_compile_options(-fsanitize=address,undefined -fno-sanitize-recover=all
                      -fno-omit-frame-pointer -g)
  add_link_options(-fsanitize=address,undefined)
endif()
```

Then `cmake -DENABLE_SANITIZERS=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo ..`

## Rust

Needs nightly (installed) plus `-Zbuild-std`, because the shipped `std` is not
instrumented and you get false negatives without rebuilding it.

```bash
RUSTFLAGS="-Zsanitizer=address" \
  cargo +nightly test -Zbuild-std --target x86_64-unknown-linux-gnu
```

Swap `address` for `thread`, `memory`, or `leak`. The explicit `--target` is
required — `-Zbuild-std` is ignored on the host triple without it.

## Caveats

- **ASan and TSan are mutually exclusive.** Two separate builds, two CI jobs.
- **MSan needs the *entire* program instrumented, including libstdc++/libc++.**
  Ubuntu does not ship an instrumented standard library, so MSan on real C++
  code (anything touching `std::string`, `std::vector`, iostreams) produces
  false positives from uninstrumented library internals. The trivial test above
  passes because it touches no library code. To use MSan seriously you must
  build libc++ with `-fsanitize=memory` yourself. For most C++ work, ASan +
  UBSan + valgrind is the practical set.
- **Sanitizers change timing.** TSan in particular can hide or expose races
  differently from production. A clean TSan run is evidence, not proof.
- **Memory cost**: ASan ~3x RAM and ~2x slowdown; TSan ~5-10x RAM. Size CI
  runners accordingly.
- **valgrind vs ASan**: valgrind (installed) needs no rebuild and catches some
  things ASan misses, but is ~20x slower. ASan is the default choice when you
  control the build; valgrind for third-party binaries you cannot recompile.
- **`.NET` and Python have no equivalent.** For C# use the built-in analyzers
  plus `dotnet-counters`/`dotnet-dump`; for Python, `tracemalloc` and
  `faulthandler`.
