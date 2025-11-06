idf_component_register(
    SRCS 
        "main.c"
        "imu_reader.c"
        "motor_test.c"
        "uart_comm.c"
    INCLUDE_DIRS "."
    PRIV_REQUIRES driver
)
