#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>

int main(int argc, char *argv[])
{
    FILE *log = fopen("telemetry_log.txt", "w");
    if (!log) {
        perror("fopen");
        return 1;
    }

    printf("Logging telemetry... Ctrl+C to stop\n");

    while (1)
    {
        FILE *fp;
        char buffer[256];
        time_t now = time(NULL);

        fprintf(log, "=== %s", ctime(&now));

        // temperature
        fp = popen("vcgencmd measure_temp", "r");
        fgets(buffer, sizeof(buffer), fp);
        fprintf(log, "%s", buffer);
        pclose(fp);

        // clock
        fp = popen("vcgencmd measure_clock arm", "r");
        fgets(buffer, sizeof(buffer), fp);
        fprintf(log, "%s", buffer);
        pclose(fp);

        // throttled
        fp = popen("vcgencmd get_throttled", "r");
        fgets(buffer, sizeof(buffer), fp);
        fprintf(log, "%s", buffer);
        pclose(fp);

        fprintf(log, "\n");
        fflush(log);

        sleep(1);
    }

    fclose(log);
    return 0;
}
