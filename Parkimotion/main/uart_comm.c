 #include "uart_comm.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

extern QueueHandle_t freq_queue;

//  Solo declaración del puntero (no definición)
extern float* user_freq_ptr;

// Solo declaramos (definida en motor_test.c)
extern void set_user_freq_ptr(float* ptr);

#define UART_NUM        UART_NUM_1
#define UART_RX_PIN     GPIO_NUM_16
#define BUF_SIZE        128

void uart_receive_task(void *pvParameters) {
    uint8_t data[BUF_SIZE];
    while (1) {
        int len = uart_read_bytes(UART_NUM, data, BUF_SIZE - 1, pdMS_TO_TICKS(100));
        if (len > 0) {
            data[len] = '\0';
            printf("📨 Recibido por UART: %s\n", data);

            float freq = atof((char *)data);
            if (freq >= 2.0f && freq <= 10.0f) {
                if (xQueueSend(freq_queue, &freq, 0) != pdPASS) {
                    printf("⚠️ Cola llena, no se pudo enviar frecuencia\n");
                } else {
                    printf("Frecuencia UART recibida: %.2f Hz\n", freq);
                }
            } else {
                printf(" Frecuencia fuera de rango (%.2f Hz)\n", freq);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

void freq_updater_task(void *pvParameters) {
    float nueva_freq = 0;
    while (1) {
        if (xQueueReceive(freq_queue, &nueva_freq, portMAX_DELAY)) {
            if (user_freq_ptr != NULL) {
                *user_freq_ptr = nueva_freq;
                printf(" user_freq actualizada vía puntero: %.2f Hz\n", *user_freq_ptr);
            } else {
                printf(" user_freq_ptr no inicializado\n");
            }
        }
    }
}

void start_uart_listener(void) {
    uart_config_t config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE
    };
    uart_param_config(UART_NUM, &config);
    uart_set_pin(UART_NUM, UART_PIN_NO_CHANGE, UART_RX_PIN, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    uart_driver_install(UART_NUM, BUF_SIZE * 2, 0, 0, NULL, 0);

    printf("📡 UART listener inicializado. user_freq_ptr = %p\n", (void*)user_freq_ptr);

    xTaskCreate(uart_receive_task, "uart_receive_task", 2048, NULL, 5, NULL);
    xTaskCreate(freq_updater_task, "freq_updater_task", 2048, NULL, 5, NULL);
}
