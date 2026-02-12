#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>

int main(int argc, char **argv) {
    int seconds = 60;
    if (argc >= 2) seconds = atoi(argv[1]);
    if (seconds <= 0) seconds = 60;

    double x = 0.1;
    time_t start = time(NULL);

    printf("CPU burn for %d seconds...\n", seconds);
    while (time(NULL) - start < seconds) {
        for (int i = 0; i < 2000000; i++) {
            x += sin(x) * cos(x);
        }
    }
    printf("Done. x=%f\n", x);
    return 0;
}
