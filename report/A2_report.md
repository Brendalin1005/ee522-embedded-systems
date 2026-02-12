# Assignment 2 — Exploration

**Target Board:** Raspberry Pi 4 Model B Rev 1.5

---

## 0. C Proficiency

My proficiency in C is **intermediate**.
I am comfortable compiling and debugging embedded-oriented programs, but this assignment served to deepen my understanding of system-level performance characterization.

---

## 1. Objective

The objective of this assignment was to establish a theoretical and experimental baseline of hardware and software capabilities of a Raspberry Pi 4 target board. The exploration focused on identifying performance characteristics, limitations, and suitability for embedded deployment by implementing C programs and analyzing observed behavior. 

---

## 2. System Characterization

### Operating System

* Raspbian GNU/Linux 13 (trixie)
* Kernel: Linux 6.12 PREEMPT aarch64

This indicates a modern Debian-based environment with a preemptible scheduler suitable for soft real-time workloads but not deterministic hard real-time execution.

---

### Processor

* CPU: Cortex-A72
* Architecture: ARMv8-A (64-bit)
* Cores: 4
* Frequency: 600–1800 MHz scaling

#### Cache hierarchy

* L1d: 128 KiB (per core)
* L1i: 192 KiB (per core)
* L2: 1 MiB shared

SIMD (NEON) and floating-point support enable efficient numeric computation.

---

### Memory

* RAM: 906 MiB usable
* Swap: 905 MiB
* Available: ~599 MiB

---

### Storage

* Root filesystem: microSD (`/dev/mmcblk0p2`)
* Capacity: 29 GB

Temporary directory (`/tmp`) is **tmpfs (RAM-backed)**
→ Only ~454 MB available

This directly affected benchmarking experiments.

---

### Toolchain

* GCC version: 14.2.0

Modern compiler optimization features were available and influenced benchmark behavior (see Section 4).

---

## 3. RAM Copy Performance

Measured using manual byte copy with checksum verification to prevent compiler optimization elimination.

| Size   | Throughput |
| ------ | ---------- |
| 1 KB   | 0.302 GB/s |
| 1 MB   | 0.623 GB/s |
| 256 MB | 0.627 GB/s |

### Observations

* Throughput stabilizes at larger sizes
* Indicates memory bandwidth ceiling around **0.6 GB/s**
* Small transfers affected by cache behavior

### Experimental Insight

Initial benchmarks using `memcpy()` produced unrealistic multi-million GB/s results due to compiler optimization.
This required redesigning the test to enforce observable memory usage — demonstrating the importance of validating experimental methodology. 

---

## 4. Filesystem Copy Performance

| Size   | Time    | Throughput |
| ------ | ------- | ---------- |
| 1 MB   | 0.021 s | ~47 MB/s   |
| 100 MB | 0.120 s | ~833 MB/s  |

### Observations

* Large apparent throughput due to Linux page cache
* Data remained in RAM rather than committed to SD card
* Demonstrates filesystem timing **non-determinism**

### Limitation

1 GB test failed:

* `/tmp` limited to RAM tmpfs
* Insufficient space

This highlights real embedded constraints and was documented rather than ignored.

---

## 5. Multithreaded Producer-Consumer

A pthread-based implementation with mutex and condition variables verified:

* Synchronization correctness
* Multi-core scheduling behavior

Result:

```
Consumed sum = 124999750000
Expected sum = 124999750000
Match? YES
```

### Observations

* Correct synchronization confirmed
* Demonstrates Linux thread scheduling across cores
* Useful baseline for real-time pipeline design

---

## 6. Production Considerations

### Small Production (~1000 units)

* SD card quality variation affects reliability
* Thermal testing recommended
* Hardware protection for GPIO

### Mass Production (~10000 units)

* Consider eMMC or industrial storage
* Manufacturing test fixtures required
* OTA update infrastructure
* Supply chain variability risk

---

## 7. Impact of Modern Tools on Embedded Systems

Modern AI-assisted tools accelerate:

* Benchmark development
* Debugging workflows
* System exploration

However results must always be validated experimentally.
Blind reliance risks incorrect engineering conclusions. 

---

## 8. Conclusion

This exploration established a practical performance baseline for Raspberry Pi 4 embedded use. The platform demonstrates strong flexibility and multicore capability, but nondeterministic filesystem behavior and limited memory bandwidth highlight constraints for real-time systems. Experimental iteration and validation proved essential to obtaining reliable measurements.

---

## 9. References

Assignment specification document
