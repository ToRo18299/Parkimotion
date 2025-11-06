#include "motor_test.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include <stdio.h>

#define STEP1_PIN    GPIO_NUM_19
#define DIR1_PIN     GPIO_NUM_23

#define STEP2_PIN    GPIO_NUM_18
#define DIR2_PIN     GPIO_NUM_5

#define ENABLE_PIN   GPIO_NUM_4

extern float freq_estimada;
extern float motor_input;

const int steps_per_cycle = 20;

float Kp = 1.17f;
float Ki = 40.1f;
float Kd = 0.00851f;
float Ts = 0.025f;
float *user_freq_ptr = NULL;

void set_user_freq_ptr(float* ptr) {
    user_freq_ptr = ptr;
}

void motor_step_task(void *pvParameters) {
    gpio_set_direction(STEP1_PIN, GPIO_MODE_OUTPUT);
    gpio_set_direction(DIR1_PIN, GPIO_MODE_OUTPUT);
    gpio_set_direction(STEP2_PIN, GPIO_MODE_OUTPUT);
    gpio_set_direction(DIR2_PIN, GPIO_MODE_OUTPUT);
    gpio_set_direction(ENABLE_PIN, GPIO_MODE_OUTPUT);

    gpio_set_level(ENABLE_PIN, 0);   // Habilita drivers
    gpio_set_level(DIR1_PIN, 1);     // Dirección inicial motor 1
    gpio_set_level(DIR2_PIN, 1);     // Dirección inicial motor 2

    int dir = 1;
    int step = 0;
    int pulse_state = 0;

    while (1) {
        float step_freq = motor_input * steps_per_cycle;

        if (step_freq < 1.0f) {
            vTaskDelay(pdMS_TO_TICKS(10));
            continue;
        }

        int periodo_us = (int)(1e6 / step_freq);
        int delay_ticks = pdMS_TO_TICKS(periodo_us / 1000);
        if (delay_ticks < 1) delay_ticks = 1;

        // Alternar pulso para ambos motores
        gpio_set_level(STEP1_PIN, pulse_state);
        gpio_set_level(STEP2_PIN, pulse_state);
        pulse_state = !pulse_state;

        if (pulse_state == 0) {
            step++;
            if (step >= steps_per_cycle) {
                step = 0;
                dir = !dir;
                gpio_set_level(DIR1_PIN, dir);
                gpio_set_level(DIR2_PIN, dir);
            }
        }

        vTaskDelay(delay_ticks);
    }
}

void motor_pid_control_task(void *pvParameters) {
    float e_k = 0, e_k_1 = 0, e_k_2 = 0;
    float u_k = 0.0f;
    float u_k_1 = 2.0f;

    while (1) {
        float y_k = freq_estimada;
        float r_k = (user_freq_ptr != NULL) ? *user_freq_ptr : 2.0f;

        printf(" user_freq actual (PID): %.2f Hz\n", r_k);

        e_k = r_k - y_k;
        float delta_u = Kp * (e_k - e_k_1)
                      + Ki * Ts * e_k
                      + Kd * (e_k - 2 * e_k_1 + e_k_2) / Ts;

        u_k = u_k_1 + delta_u;

        if (u_k < 2.0f) u_k = 2.0f;
        if (u_k > 10.0f) u_k = 10.0f;

        motor_input = u_k;

       printf("PID: Ref=%.2f Hz | Est=%.2f Hz | Err=%.2f | Out=%.2f Hz | Δu=%.2f\n",
               r_k, y_k, e_k, u_k, delta_u); 

        e_k_2 = e_k_1;
        e_k_1 = e_k;
        u_k_1 = u_k;

        vTaskDelay(pdMS_TO_TICKS((int)(Ts * 1000)));
    }
}

void start_motor_test_task(void) {
    xTaskCreate(motor_step_task, "motor_step_task", 4096, NULL, 5, NULL);
    xTaskCreate(motor_pid_control_task, "motor_pid_control_task", 4096, NULL, 5, NULL);
}
