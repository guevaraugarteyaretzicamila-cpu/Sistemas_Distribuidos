#include <stdio.h>
#include <winsock2.h> // Libreria de red para Windows

#pragma comment(lib, "ws2_32.lib") // Indica que use la libreria de sockets

int main() {
    WSADATA wsa;
    SOCKET servidor_fd, nuevo_socket;
    struct sockaddr_in direccion;
    int addrlen = sizeof(direccion);
    int numero_recibido;

    // Inicializar Winsock (Solo necesario en Windows)
    WSAStartup(MAKEWORD(2,2), &wsa);

    // Crear socket
    servidor_fd = socket(AF_INET, SOCK_STREAM, 0);
    
    direccion.sin_family = AF_INET;
    direccion.sin_addr.s_addr = INADDR_ANY;
    direccion.sin_port = htons(50000);

    bind(servidor_fd, (struct sockaddr *)&direccion, sizeof(direccion));
    listen(servidor_fd, 3);

    printf("Servidor C (Windows) esperando numeros en el puerto 50000...\n");

    nuevo_socket = accept(servidor_fd, (struct sockaddr *)&direccion, &addrlen);

    while(1) {
        // Recibir el numero del cliente Java
        int bytes = recv(nuevo_socket, (char*)&numero_recibido, sizeof(int), 0);
        if (bytes <= 0) break;

        numero_recibido = ntohl(numero_recibido); // Convertir formato de red a host
        printf("Cliente envio: %d\n", numero_recibido);

        if (numero_recibido == 0) break;

        // Incrementar y mandar de vuelta
        numero_recibido++;
        int respuesta = htonl(numero_recibido);
        send(nuevo_socket, (char*)&respuesta, sizeof(int), 0);
    }

    closesocket(nuevo_socket);
    closesocket(servidor_fd);
    WSACleanup();
    return 0;
}