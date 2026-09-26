
#include "calculadora.h"
#include <stdio.h>

int *
suma_1_svc(operandos *argp, struct svc_req *rqstp)
{
    static int result;
    result = argp->a + argp->b;
    printf("Se llamo a suma_1_svc: %d + %d = %d\n", argp->a, argp->b, result);
    return &result;
}

int *
resta_1_svc(operandos *argp, struct svc_req *rqstp)
{
    static int result;
    result = argp->a - argp->b;
    printf("Se llamo a resta_1_svc: %d - %d = %d\n", argp->a, argp->b, result);
    return &result;
}

int *
multiplica_1_svc(operandos *argp, struct svc_req *rqstp)
{
    static int result;
    result = argp->a * argp->b;
    printf("Se llamo a multiplica_1_svc: %d * %d = %d\n", argp->a, argp->b, result);
    return &result;
}

float *
divide_1_svc(operandos *argp, struct svc_req *rqstp)
{
    static float result;

    if (argp->b == 0) {
        printf("Error: division entre cero\n");
        result = 0;
    } else {
        result = (float)argp->a / (float)argp->b;
    }

    printf("Se llamo a divide_1_svc: %d / %d = %f\n", argp->a, argp->b, result);
    return &result;
}

