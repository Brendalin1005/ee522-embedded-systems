#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

#define SIZE 1024
#define ITEMS 500000

int buffer[SIZE];
int count = 0;
int in = 0;
int out = 0;

pthread_mutex_t lock;
pthread_cond_t not_full;
pthread_cond_t not_empty;

void* producer(void* arg) {
    for(int i=0;i<ITEMS;i++) {
        pthread_mutex_lock(&lock);

        while(count == SIZE)
            pthread_cond_wait(&not_full, &lock);

        buffer[in] = i;
        in = (in+1)%SIZE;
        count++;

        pthread_cond_signal(&not_empty);
        pthread_mutex_unlock(&lock);
    }
    return NULL;
}

void* consumer(void* arg) {
    (void)arg;
    unsigned long long sum = 0;

    for(int i=0;i<ITEMS;i++) {
        pthread_mutex_lock(&lock);

        while(count == 0)
            pthread_cond_wait(&not_empty, &lock);

        sum += (unsigned long long)buffer[out];
        out = (out+1)%SIZE;
        count--;

        pthread_cond_signal(&not_full);
        pthread_mutex_unlock(&lock);
    }

    unsigned long long expected =
        (unsigned long long)ITEMS * (unsigned long long)(ITEMS - 1) / 2ULL;

    printf("Consumed sum=%llu\n", sum);
    printf("Expected sum=%llu\n", expected);
    printf("Match? %s\n", (sum == expected) ? "YES" : "NO");

    return NULL;
}


int main() {
    pthread_t p,c;

    pthread_mutex_init(&lock,NULL);
    pthread_cond_init(&not_full,NULL);
    pthread_cond_init(&not_empty,NULL);

    pthread_create(&p,NULL,producer,NULL);
    pthread_create(&c,NULL,consumer,NULL);

    pthread_join(p,NULL);
    pthread_join(c,NULL);

    return 0;
}
