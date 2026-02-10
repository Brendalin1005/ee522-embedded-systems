#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>

static double now() {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

static volatile uint64_t sink = 0;

// Simple byte copy (forces real memory traffic)
static void copy_bytes(uint8_t* dst, const uint8_t* src, size_t n) {
    for (size_t i = 0; i < n; i++) {
        dst[i] = src[i];
    }
}

// Full-buffer checksum so compiler can't skip work
static uint64_t checksum(const uint8_t* buf, size_t n) {
    uint64_t s = 0;
    for (size_t i = 0; i < n; i++) {
        s += buf[i];
    }
    return s;
}

static void bench(size_t bytes, int iters) {
    uint8_t *src = (uint8_t*)malloc(bytes);
    uint8_t *dst = (uint8_t*)malloc(bytes);
    if (!src || !dst) { perror("malloc"); exit(1); }

    for (size_t i = 0; i < bytes; i++) src[i] = (uint8_t)(i * 131u + 7u);

    // warmup
    copy_bytes(dst, src, bytes);
    sink += checksum(dst, bytes);

    double t0 = now();
    for (int i = 0; i < iters; i++) {
        copy_bytes(dst, src, bytes);
        sink += checksum(dst, bytes); // touches every byte
    }
    double t1 = now();

    double sec = (t1 - t0);
    double gb = ((double)bytes * (double)iters) / 1e9;
    printf("%zu bytes, iters=%d, time=%.6f s -> %.3f GB/s (sink=%llu)\n",
           bytes, iters, sec, gb/sec, (unsigned long long)sink);

    free(src);
    free(dst);
}

int main() {
    printf("RAM Copy Benchmark (manual copy + full checksum)\n");

    bench(1024, 20000);        // 1KB
    bench(1024*1024, 200);     // 1MB

    // 1GB can be too big; use 256MB to be safe and still meaningful
    bench((size_t)256*1024*1024, 5); // 256MB

    return 0;
}
