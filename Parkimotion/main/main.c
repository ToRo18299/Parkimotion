#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"

#include "driver/gpio.h"
#include "motor_test.h"
#include "imu_reader.h"
#include "uart_comm.h"

// Variable global compartida entre tareas
volatile float user_freq = 7.0f;
float motor_input = 0.0f;

//  Cola global para recibir frecuencia desde UART
QueueHandle_t freq_queue;

extern void set_user_freq_ptr(float *ptr);

void app_main(void)
{
    freq_queue = xQueueCreate(1, sizeof(float));
    if (freq_queue == NULL)
    {
        printf("❌ Error creando la cola\n");
        return;
    }

    //  Pasa la dirección directamente, sin definir un nuevo puntero
    set_user_freq_ptr((float *)&user_freq);

    start_uart_listener();   // UART que escribirá vía puntero
    start_motor_test_task(); // PID leerá desde el puntero
    start_imu_reader_task(); 
}
