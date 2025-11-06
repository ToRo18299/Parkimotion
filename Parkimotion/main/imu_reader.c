#include "imu_reader.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/i2c.h"
#include "esp_log.h"
#include <stdio.h>

#define I2C_MASTER_SCL_IO           22
#define I2C_MASTER_SDA_IO           21
#define I2C_MASTER_NUM              I2C_NUM_0
#define I2C_MASTER_FREQ_HZ          100000
#define I2C_MASTER_TX_BUF_DISABLE   0
#define I2C_MASTER_RX_BUF_DISABLE   0

#define MPU6050_ADDR                0x68
#define MPU6050_PWR_MGMT_1          0x6B

extern volatile float user_freq;
extern float motor_input;
float freq_estimada = 4.0f;

// Filtro Butterworth pasa banda 2–10 Hz, fs = 40 Hz, orden 2
float b[5] = {0.1804, 0.0, -0.3609, 0.0, 0.1804};
float a[5] = {1.0, -1.5016, 1.1683, -0.3872, 0.0794};

float x_hist[5] = {0};
float y_hist[5] = {0};

esp_err_t i2c_master_init(void) {
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_MASTER_SDA_IO,
        .scl_io_num = I2C_MASTER_SCL_IO,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_MASTER_FREQ_HZ,
    };
    i2c_param_config(I2C_MASTER_NUM, &conf);
    return i2c_driver_install(I2C_MASTER_NUM, conf.mode,
                              I2C_MASTER_RX_BUF_DISABLE, I2C_MASTER_TX_BUF_DISABLE, 0);
}

esp_err_t mpu6050_write_byte(uint8_t reg_addr, uint8_t data) {
    uint8_t buffer[2] = {reg_addr, data};
    return i2c_master_write_to_device(I2C_MASTER_NUM, MPU6050_ADDR, buffer, 2, pdMS_TO_TICKS(1000));
}

esp_err_t mpu6050_read_bytes(uint8_t reg_addr, uint8_t *data, size_t len) {
    return i2c_master_write_read_device(I2C_MASTER_NUM, MPU6050_ADDR, &reg_addr, 1, data, len, pdMS_TO_TICKS(1000));
}

float aplicar_filtro(float acc_z) {
    for (int i = 4; i > 0; i--) {
        x_hist[i] = x_hist[i - 1];
        y_hist[i] = y_hist[i - 1];
    }
    x_hist[0] = acc_z;

    float y = 0.0f;
    for (int i = 0; i < 5; i++) {
        y += b[i] * x_hist[i];
    }
    for (int i = 1; i < 5; i++) {
        y -= a[i] * y_hist[i];
    }

    y_hist[0] = y;
    return y;
}

void imu_task(void *pvParameters) {
    ESP_ERROR_CHECK(i2c_master_init());
    ESP_ERROR_CHECK(mpu6050_write_byte(MPU6050_PWR_MGMT_1, 0x00));

    const TickType_t sampling_interval = pdMS_TO_TICKS(25); // 40Hz
    TickType_t last_wake_time = xTaskGetTickCount();

    float last_acc_z = 0;
    int cruce_cero_count = 0;
    const float ventana_tiempo = 1.0f;
    const int muestras_por_ventana = (int)(ventana_tiempo / 0.025f);
    int muestra_actual = 0;

    while (1) {
        uint8_t raw_data[6 * 3];
        esp_err_t res = mpu6050_read_bytes(0x3B, raw_data, 6 * 3);

        if (res == ESP_OK) {
            int16_t acc_x_raw = (raw_data[0] << 8) | raw_data[1];
            int16_t acc_y_raw = (raw_data[2] << 8) | raw_data[3];
            int16_t acc_z_raw = (raw_data[4] << 8) | raw_data[5];

            float acc_x = acc_x_raw / 16384.0f;
            float acc_y = acc_y_raw / 16384.0f;
            float acc_z = acc_z_raw / 16384.0f - 1.0f;

            float acc_z_filtrado = aplicar_filtro(acc_z);

            if ((last_acc_z <= 0 && acc_z_filtrado > 0) || (last_acc_z >= 0 && acc_z_filtrado < 0)) {
                cruce_cero_count++;
            }

            last_acc_z = acc_z_filtrado;
            muestra_actual++;

            if (muestra_actual >= muestras_por_ventana) {
                freq_estimada = cruce_cero_count / 2.0f;
                cruce_cero_count = 0;
                muestra_actual = 0;

                //  Verificar valor de referencia actual
                printf(" Actual Ref usada en IMU (user_freq): %.2f Hz\n", user_freq);
            }

            printf("ACC_X: %.3f, ACC_Y: %.3f, ACC_Z: %.3f | F_Z(filt): %.3f | Freq: %.2f Hz | Ref: %.2f | Motor: %.2f\n",
                   acc_x, acc_y, acc_z, acc_z_filtrado, freq_estimada, user_freq, motor_input);
        } else {
            printf("❌ Error leyendo IMU\n");
        }

        vTaskDelayUntil(&last_wake_time, sampling_interval);
    }
}

void start_imu_reader_task(void) {
    xTaskCreate(imu_task, "imu_reader_task", 4096, NULL, 5, NULL);
}