#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>

static void run_cmd(FILE *out, const char *cmd) {
    FILE *fp = popen(cmd, "r");
    if (!fp) { fprintf(out, "cmd_fail: %s\n", cmd); return; }
    char buf[256];
    if (fgets(buf, sizeof(buf), fp)) fputs(buf, out);
    pclose(fp);
}

int main(int argc, char **argv) {
    int seconds = 90;      // total duration
    int interval = 1;      // seconds
    const char *outpath = "results/telemetry_thermal.txt";

    if (argc >= 2) seconds = atoi(argv[1]);
    if (argc >= 3) interval = atoi(argv[2]);
    if (argc >= 4) outpath = argv[3];
    if (seconds <= 0) seconds = 90;
    if (interval <= 0) interval = 1;

    FILE *out = fopen(outpath, "w");
    if (!out) { perror("fopen"); return 1; }

    fprintf(out, "telemetry_log seconds=%d interval=%d\n\n", seconds, interval);
    fflush(out);

    for (int t = 0; t < seconds; t += interval) {
        time_t now = time(NULL);
        fprintf(out, "=== %s", ctime(&now));
        run_cmd(out, "vcgencmd measure_temp");
        run_cmd(out, "vcgencmd measure_clock arm");
        run_cmd(out, "vcgencmd get_throttled");
        fputc('\n', out);
        fflush(out);
        sleep(interval);
    }

    fclose(out);
    printf("Wrote %s\n", outpath);
    return 0;
}
