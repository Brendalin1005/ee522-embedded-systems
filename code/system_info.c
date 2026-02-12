#include <stdio.h>
#include <stdlib.h>

static void run(const char* cmd) {
    printf("\n$ %s\n", cmd);
    fflush(stdout);
    int ret = system(cmd);
    if (ret != 0) printf("  (command returned %d)\n", ret);
}

int main(void) {
    printf("=== Raspberry Pi 4 System Info ===\n");

    run("uname -a");
    run("cat /etc/os-release");
    run("cat /proc/cpuinfo | sed -n '1,60p'");
    run("lscpu | sed -n '1,80p'");
    run("free -h");
    run("df -h");
    run("gcc --version | head -n 2");

    printf("\nDone.\n");
    return 0;
}
