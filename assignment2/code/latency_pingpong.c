#define _GNU_SOURCE
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

static inline uint64_t nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

typedef struct {
    pthread_mutex_t mtx;
    pthread_cond_t  cv;
    int turn;     // 0 -> A runs, 1 -> B runs
    int stop;
    int iters;
    uint64_t *rt; // round-trip ns: A->B->A
} shared_t;

static void pin_to_cpu0_best_effort(void) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(0, &set);
    (void)pthread_setaffinity_np(pthread_self(), sizeof(set), &set);
}

static int cmp_u64(const void *a, const void *b) {
    uint64_t x = *(const uint64_t*)a, y = *(const uint64_t*)b;
    return (x > y) - (x < y);
}

static void *thread_b(void *arg) {
    shared_t *S = (shared_t*)arg;
    pin_to_cpu0_best_effort();

    pthread_mutex_lock(&S->mtx);
    while (!S->stop) {
        while (!S->stop && S->turn != 1)
            pthread_cond_wait(&S->cv, &S->mtx);
        if (S->stop) break;

        // respond immediately
        S->turn = 0;
        pthread_cond_signal(&S->cv);
    }
    pthread_mutex_unlock(&S->mtx);
    return NULL;
}

int main(int argc, char **argv) {
    int iters = 200000;
    if (argc >= 2) iters = atoi(argv[1]);
    if (iters < 1000) iters = 1000;

    shared_t S;
    S.turn = 0;
    S.stop = 0;
    S.iters = iters;
    S.rt = (uint64_t*)calloc((size_t)iters, sizeof(uint64_t));
    if (!S.rt) { perror("calloc"); return 1; }

    pthread_mutex_init(&S.mtx, NULL);
    pthread_cond_init(&S.cv, NULL);

    pthread_t tb;
    if (pthread_create(&tb, NULL, thread_b, &S) != 0) {
        perror("pthread_create");
        return 1;
    }

    pin_to_cpu0_best_effort();
    usleep(10000); // warmup

    pthread_mutex_lock(&S.mtx);
    for (int i = 0; i < iters; i++) {
        uint64_t t0 = nsec_now();

        S.turn = 1;
        pthread_cond_signal(&S.cv);

        while (S.turn != 0)
            pthread_cond_wait(&S.cv, &S.mtx);

        uint64_t t1 = nsec_now();
        S.rt[i] = (t1 - t0);
    }
    S.stop = 1;
    pthread_cond_signal(&S.cv);
    pthread_mutex_unlock(&S.mtx);

    pthread_join(tb, NULL);

    // Stats
    uint64_t *sorted = (uint64_t*)malloc((size_t)iters * sizeof(uint64_t));
    if (!sorted) { perror("malloc"); return 1; }
    for (int i = 0; i < iters; i++) sorted[i] = S.rt[i];
    qsort(sorted, (size_t)iters, sizeof(uint64_t), cmp_u64);

    uint64_t min = sorted[0];
    uint64_t max = sorted[iters - 1];
    uint64_t p50 = sorted[(int)(0.50 * (iters - 1))];
    uint64_t p95 = sorted[(int)(0.95 * (iters - 1))];
    uint64_t p99 = sorted[(int)(0.99 * (iters - 1))];

    long double sum = 0.0;
    for (int i = 0; i < iters; i++) sum += (long double)S.rt[i];
    long double avg = sum / (long double)iters;

    printf("Ping-pong round-trip latency (A->B->A), iters=%d\n", iters);
    printf("min: %.3f us\n", (double)min / 1000.0);
    printf("p50: %.3f us\n", (double)p50 / 1000.0);
    printf("p95: %.3f us\n", (double)p95 / 1000.0);
    printf("p99: %.3f us\n", (double)p99 / 1000.0);
    printf("max: %.3f us\n", (double)max / 1000.0);
    printf("avg: %.3f us\n", (double)avg / 1000.0);

    free(sorted);
    free(S.rt);
    return 0;
}
