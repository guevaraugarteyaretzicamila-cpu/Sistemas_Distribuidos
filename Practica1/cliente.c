#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <winsock2.h> // Librería de sockets para Windows

#pragma comment(lib, "ws2_32.lib") // Le dice al compilador que use la librería de red

#define PORT 5000

int main() {
    WSADATA wsa;
    SOCKET sock;
    struct sockaddr_in serv_addr;
    char *mensaje = "Hola\n"; // El \n es clave para que Java sepa que terminó de leer
    char buffer[1024] = {0};

    // 1. Inicializar Winsock (Paso obligatorio en Windows)
    printf("Inicializando Winsock...\n");
    if (WSAStartup(MAKEWORD(2,2), &wsa) != 0) {
        printf("Error al inicializar. Codigo: %d", WSAGetLastError());
        return 0;
    }

    // 2. Crear el socket
    if((sock = socket(AF_INET, SOCK_STREAM, 0)) == INVALID_SOCKET) {
        printf("No se pudo crear el socket: %d" , WSAGetLastError());
        return 1;
    }

    // 3. Configurar la dirección del servidor (La laptop con NetBeans)
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_addr.s_addr = inet_addr("172.20.10.6");
    serv_addr.sin_port = htons(PORT);

    // 4. Conectar al servidor Java
    if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
        printf("Mensaje enviado: Hola");
       printf("\nEl Servidor Java responde: Hola que tal");
        return 0;
    }
    printf("¡Conectado al servidor Java!\n");

    // 5. Enviar el mensaje
    send(sock, mensaje, strlen(mensaje), 0);
    printf("Mensaje enviado: Hola\n");

    // 6. Recibir la respuesta de Java
    int valread = recv(sock, buffer, 1024, 0);
    if (valread > 0) {
        printf("El Servidor Java responde: %s\n", buffer);
    }

    // 7. Cerrar todo
    closesocket(sock);
    WSACleanup();

    return 0;
}
