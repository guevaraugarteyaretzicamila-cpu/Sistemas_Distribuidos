#include "calculadora.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void calc_prog_1(char *host, char *operacion, int a, int b)
{
    CLIENT *clnt;
    operandos ops;
    int *res_int;
    float *res_float;

    clnt = clnt_create(host, CALC_PROG, CALC_VERS, "udp");
    if (clnt == NULL) {
        clnt_pcreateerror(host);
        exit(1);
    }

    ops.a = a;
    ops.b = b;

    if (strcmp(operacion, "suma") == 0) {
        res_int = suma_1(&ops, clnt);
        if (res_int == NULL) {
            clnt_perror(clnt, "call failed");
            exit(1);
        }
        printf("Resultado: %d\n", *res_int);
    }
    else if (strcmp(operacion, "resta") == 0) {
        res_int = resta_1(&ops, clnt);
        if (res_int == NULL) {
            clnt_perror(clnt, "call failed");
            exit(1);
        }
        printf("Resultado: %d\n", *res_int);
    }
    else if (strcmp(operacion, "multiplica") == 0) {
        res_int = multiplica_1(&ops, clnt);
        if (res_int == NULL) {
            clnt_perror(clnt, "call failed");
            exit(1);
        }
        printf("Resultado: %d\n", *res_int);
    }
    else if (strcmp(operacion, "divide") == 0) {
        res_float = divide_1(&ops, clnt);
        if (res_float == NULL) {
            clnt_perror(clnt, "call failed");
            exit(1);
        }
        printf("Resultado: %f\n", *res_float);
    }
    else {
        printf("Operacion no valida. Use: suma, resta, multiplica o divide\n");
    }

    clnt_destroy(clnt);
}

int main(int argc, char *argv[])
{
    char *host;
    char *operacion;
    int a, b;

    if (argc != 5) {
        printf("Uso: %s servidor operacion num1 num2\n", argv[0]);
        printf("Ejemplo: %s localhost suma 8 3\n", argv[0]);
        exit(1);
    }

    host = argv[1];
    operacion = argv[2];
    a = atoi(argv[3]);
    b = atoi(argv[4]);

    calc_prog_1(host, operacion, a, b);

    return 0;
}
