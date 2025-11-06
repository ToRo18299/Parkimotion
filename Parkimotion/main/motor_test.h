#ifndef MOTOR_TEST_H
#define MOTOR_TEST_H

extern float* user_freq_ptr;               //  Declaración global
void set_user_freq_ptr(float* ptr);        //  Declaración de función
void start_motor_test_task(void);
extern float freq_estimada;
extern float motor_input;

#endif
