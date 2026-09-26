/* calculadora.x */

struct operandos {
    int a;
    int b;
};

program CALC_PROG {
    version CALC_VERS {
        int SUMA(operandos) = 1;
        int RESTA(operandos) = 2;
        int MULTIPLICA(operandos) = 3;
        float DIVIDE(operandos) = 4;
    } = 1;
} = 0x31234567;


