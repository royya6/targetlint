/*
 * sample.c — deliberately flawed firmware example for targetlint smoke testing.
 * This file intentionally contains patterns that trip all five rule modules.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* -----------------------------------------------------------------------
 * Issue: sizeof(int) assumed to be 4 (word-size assumption).
 * On a 64-bit target, sizeof(int) may still be 4, but sizeof(int*) is 8.
 * ----------------------------------------------------------------------- */
static int lookup_table[512 / 4];  /* assumes sizeof(int) == 4 */

/* -----------------------------------------------------------------------
 * Issue: large local array — 512 bytes on the stack.
 * On cortex-m0 the entire stack budget is 8192 bytes; this is 6% of it
 * and can easily overflow in a deep call tree.
 * ----------------------------------------------------------------------- */
void process_data(void) {
    char local_buf[512];   /* 512-byte local array — stack risk */
    memset(local_buf, 0, sizeof(local_buf));

    /* Issue: malloc() called without checking return value for NULL */
    char *heap_buf = malloc(256);
    /* BUG: return value of malloc not checked before use */
    memcpy(heap_buf, local_buf, 64);

    /* Issue: printf() used — assumes stdlib / hosted environment */
    printf("processed %zu bytes\n", sizeof(local_buf));

    free(heap_buf);
}

/* -----------------------------------------------------------------------
 * Issue: struct containing a float field — assumes hardware FPU.
 * On targets with has_fpu: false this triggers soft-float emulation,
 * which is slow and increases code size significantly.
 * ----------------------------------------------------------------------- */
typedef struct {
    int   sensor_id;
    float temperature;   /* float field — FPU assumption */
    float pressure;      /* float field — FPU assumption */
} SensorReading;

/* -----------------------------------------------------------------------
 * Issue: recursive function with no depth limit — stack risk.
 * On a device with only 8192 bytes of stack, deep recursion will overflow.
 * ----------------------------------------------------------------------- */
int fibonacci(int n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);  /* unbounded recursion */
}

/* -----------------------------------------------------------------------
 * Issue: busy-wait delay loop with hardcoded count that assumes 8 MHz clock.
 * The cortex-m0 target runs at 16 MHz, so this delay will be half as long
 * as intended — timing-sensitive code will behave incorrectly.
 * ----------------------------------------------------------------------- */
void delay_ms(int ms) {
    /* assumes 8MHz clock: 8000 iterations ≈ 1 ms at 8 MHz */
    for (volatile int i = 0; i < ms * 8000; i++) {
        /* busy-wait — no watchdog kick inside this long-running loop */
    }
}

/* -----------------------------------------------------------------------
 * Issue: no watchdog kick inside a long-running loop.
 * If watchdog_timeout_ms is 2000 and this loop runs longer than 2 seconds,
 * the watchdog will fire and reset the device unexpectedly.
 * ----------------------------------------------------------------------- */
void sensor_poll_loop(int iterations) {
    SensorReading reading;
    for (int i = 0; i < iterations; i++) {
        reading.sensor_id   = i;
        reading.temperature = 25.0f + (float)i * 0.1f;  /* float arithmetic */
        reading.pressure    = 101.3f;                     /* float arithmetic */

        process_data();
        /* BUG: no watchdog_kick() call — watchdog will fire on long runs */
    }
}

int main(void) {
    printf("targetlint sample — starting\n");  /* printf — stdlib assumption */

    sensor_poll_loop(1000);

    int fib = fibonacci(10);
    printf("fib(10) = %d\n", fib);  /* printf — stdlib assumption */

    return 0;
}
