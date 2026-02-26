import java.io.*;
import java.net.*;
import java.util.Scanner;

public class ClienteEnteros {
    public static void main(String[] args) {
        String ipServidor = "172.20.10.6";
        int puerto = 50000;

        try (Socket socket = new Socket(ipServidor, puerto);
             DataOutputStream salida = new DataOutputStream(socket.getOutputStream());
             DataInputStream entrada = new DataInputStream(socket.getInputStream());
             Scanner teclado = new Scanner(System.in)) {

            int numero = -1;
            while (numero != 0) {
                System.out.print("Escribe un numero entero (0 para salir): ");
                numero = teclado.nextInt();

                // Enviar el numero al servidor en C
                salida.writeInt(numero); 
                salida.flush();

                if (numero != 0) {
                    // Recibir el numero incrementado
                    int respuesta = entrada.readInt();
                    System.out.println("El servidor C respondio: " + respuesta);
                }
            }
        } catch (IOException e) {
            System.out.println("Error: " + e.getMessage());
        }
    }
}