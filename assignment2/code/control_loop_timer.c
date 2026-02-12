#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <unistd.h>

static inline uint64_t nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec*1000000000ULL + (uint64_t)ts.tv_nsec;
}

static int cmp_u64(const void *a, const void *b) {
    uint64_t x = *(const uint64_t*)a, y = *(const uint64_t*)b;
    return (x > y) - (x < y);
}

// add nanoseconds to timespec (normalized)
static struct timespec ts_add_ns(struct timespec t, long ns) {
    t.tv_nsec += ns;
    while (t.tv_nsec >= 1000000000L) { t.tv_nsec -= 1000000000L; t.tv_sec++; }
    while (t.tv_nsec < 0) { t.tv_nsec += 1000000000L; t.tv_sec--; }
    return t;
}

int main(int argc, char **argv) {
    int hz = 200;          // control frequency
    int seconds = 10;      // duration
    int work = 0;          // dummy work (0..100, bigger = heavier)

    if (argc >= 2) hz = atoi(argv[1]);
    if (argc >= 3) seconds = atoi(argv[2]);
    if (argc >= 4) work = atoi(argv[3]);

    if (hz < 1) hz = 1;
    if (seconds < 1) seconds = 1;
    if (work < 0) work = 0;

    int iters = hz * seconds;
    long period_ns = (long)(1000000000L / hz);

    uint64_t *late_ns = (uint64_t*)calloc((size_t)iters, sizeof(uint64_t));
    if (!late_ns) { perror("calloc"); return 1; }

    struct timespec next;
    clock_gettime(CLOCK_MONOTONIC, &next);
    next = ts_add_ns(next, period_ns);

    printf("Control loop timer: %d Hz, %d s, iters=%d, dummy_work=%d\n", hz, seconds, iters, work);

    for (int i = 0; i < iters; i++) {
        // sleep until absolute time (best practice for periodic loops)
        clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next, NULL);

        uint64_t now = nsec_now();
        uint64_t target = (uint64_t)next.tv_sec*1000000000ULL + (uint64_t)next.tv_nsec;

        // lateness (how late we woke up) in ns
        late_ns[i] = (now > target) ? (now - target) : 0;

        // dummy compute to simulate control math / kinematics
        volatile double x = 0.1;
        for (int k = 0; k < work * 2000; k++) {
            x = x * 1.0000001 + 0.0000003;
        }

        next = ts_add_ns(next, period_ns);
    }

    // stats
    uint64_t *sorted = (uint64_t*)malloc((size_t)iters * sizeof(uint64_t));
    for (int i = 0; i < iters; i++) sorted[i] = late_ns[i];
    qsort(sorted, (size_t)iters, sizeof(uint64_t), cmp_u64);

    uint64_t min = sorted[0];
    uint64_t max = sorted[iters - 1];
    uint64_t p50 = sorted[(int)(0.50 * (iters - 1))];
    uint64_t p95 = sorted[(int)(0.95 * (iters - 1))];
    uint64_t p99 = sorted[(int)(0.99 * (iters - 1))];

    long double sum = 0.0;
    for (int i = 0; i < iters; i++) sum += (long double)late_ns[i];
    long double avg = sum / (long double)iters;

    printf("Wakeup lateness (ns): min=%llu p50=%llu p95=%llu p99=%llu max=%llu avg=%.0Lf\n",
           (unsigned long long)min, (unsigned long long)p50, (unsigned long long)p95,
           (unsigned long long)p99, (unsigned long long)max, avg);

    printf("Wakeup lateness (us): min=%.3f p50=%.3f p95=%.3f p99=%.3f max=%.3f avg=%.3f\n",
           min/1000.0, p50/1000.0, p95/1000.0, p99/1000.0, max/1000.0, (double)avg/1000.0);

    free(sorted);
    free(late_ns);
    return 0;
}
