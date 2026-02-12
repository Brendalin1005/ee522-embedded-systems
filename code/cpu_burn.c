#include <stdio.h>
#include <math.h>
#include <time.h>

int main()
{
    double x = 0.1;
    time_t start = time(NULL);

    printf("Running CPU burn for 60 seconds...\n");

    while (time(NULL) - start < 60)
    {
        for (int i=0;i<1000000;i++)
        {
            x += sin(x) * cos(x);
        }
    }

    printf("Done. Result=%f\n", x);
    return 0;
}
