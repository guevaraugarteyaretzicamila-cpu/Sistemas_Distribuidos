# bittorrent_project/peer.py
import socket
import threading
import json
import os
import time
from tqdm import tqdm
import urllib.request
import random
import base64

from file_manager import load_progress, save_progress, get_progress, remove_progress, CHUNK_SIZE
from network_utils import send_json, start_listener, register_or_update_peer, get_peers_with_file, get_network_status

PEER_ID = os.getenv("PEER_ID", "DefaultPeer")
PEER_PORT = int(os.getenv("PEER_PORT", 8000))
PEER_ADVERTISED_IP = os.getenv("PEER_ADVERTISED_IP", "127.0.0.1")
PEER_BIND_IP = "0.0.0.0" 
TRACKER_IP = os.getenv("TRACKER_IP", "tracker")
TRACKER_PORT = int(os.getenv("TRACKER_PORT", 8080))

SHARED_DIR = "sample_files"
RECEIVED_DIR = "received_files"

os.makedirs(SHARED_DIR, exist_ok=True)
os.makedirs(RECEIVED_DIR, exist_ok=True)

load_progress()

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def heartbeat_to_tracker(interval=10):
    while True:
        success = register_or_update_peer(TRACKER_IP, TRACKER_PORT, PEER_ID, PEER_ADVERTISED_IP, PEER_PORT, SHARED_DIR, RECEIVED_DIR, initial_registration=False)
        if success:
            pass 
        else:
            print(f"[PEER] Falló el envío del heartbeat al tracker. Reintentando...")
        time.sleep(interval)

def serve_file_handler(conn, addr):
    try:
        data = conn.recv(4096).decode()
        if not data:
            print(f"[PEER LISTENER] Conexión cerrada por {addr}.")
            return

        request = json.loads(data)
        command = request.get("command")

        if command == "GET_FILE_INFO":
            filename = request["filename"]
            filepath_shared = os.path.join(SHARED_DIR, filename)
            filepath_received = os.path.join(RECEIVED_DIR, filename)

            file_path = None
            if os.path.exists(filepath_shared):
                file_path = filepath_shared
            elif os.path.exists(filepath_received):
                file_path = filepath_received

            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                num_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
                response = {"status": "success", "file_size": file_size, "num_chunks": num_chunks}
                conn.sendall(json.dumps(response).encode())
            else:
                response = {"status": "error", "message": "File not found"}
                conn.sendall(json.dumps(response).encode())
                print(f"[PEER LISTENER] Archivo '{filename}' no encontrado para info.")

        elif command == "REQUEST_CHUNK":
            filename = request["filename"]
            chunk_index = request["chunk_index"]
            
            filepath_shared = os.path.join(SHARED_DIR, filename)
            filepath_received = os.path.join(RECEIVED_DIR, filename)

            file_path = None
            if os.path.exists(filepath_shared):
                file_path = filepath_shared
            elif os.path.exists(filepath_received):
                file_path = filepath_received

            if file_path:
                try:
                    with open(file_path, "rb") as f:
                        f.seek(chunk_index * CHUNK_SIZE)
                        chunk_data = f.read(CHUNK_SIZE)
                        
                        if chunk_data:
                            encoded_chunk = base64.b64encode(chunk_data).decode('ascii') 
                            response = {"status": "success", "chunk": encoded_chunk} 
                            conn.sendall(json.dumps(response).encode())
                        else:
                            print(f"[PEER LISTENER] Chunk {chunk_index} vacío para {filename}. Fuera de rango o archivo más corto.")
                            response = {"status": "error", "message": "Chunk out of range or file too small"}
                            conn.sendall(json.dumps(response).encode())
                except Exception as e:
                    print(f"[PEER LISTENER ERROR] Error al leer/enviar chunk {chunk_index} de {filename}: {e}")
                    response = {"status": "error", "message": f"Error al leer/enviar chunk: {e}"}
                    conn.sendall(json.dumps(response).encode())
            else:
                print(f"[PEER LISTENER] Archivo no encontrado en el directorio compartido o de descarga: {filename}")
                response = {"status": "error", "message": "File not found"}
                conn.sendall(json.dumps(response).encode())
        else:
            print(f"[PEER LISTENER] Comando desconocido: {command}")
            response = {"status": "error", "message": "Unknown command"}
            conn.sendall(json.dumps(response).encode())

    except json.JSONDecodeError:
        print(f"[PEER LISTENER ERROR] Datos JSON inválidos recibidos de {addr}")
        try:
            conn.sendall(json.dumps({"status": "error", "message": "Invalid JSON"}).encode())
        except Exception as e:
            print(f"[PEER LISTENER ERROR] Error al enviar respuesta de error JSON: {e}")
    except ConnectionResetError:
        pass 
    except Exception as e:
        print(f"[PEER LISTENER ERROR] Error general en serve_file_handler con {addr}: {e}")
    finally:
        conn.close() 

def download_chunk_from_peer(peer_ip, peer_port, filename, chunk_index):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(35) 
            s.connect((peer_ip, peer_port))

            request_message = {
                "command": "REQUEST_CHUNK",
                "filename": filename,
                "chunk_index": chunk_index
            }
            s.sendall(json.dumps(request_message).encode())
            
            response_data = b""
            while True:
                chunk_recv = s.recv(4096)
                if not chunk_recv:
                    break
                response_data += chunk_recv
            
            if response_data:
                try:
                    decoded_response = json.loads(response_data.decode())
                    if decoded_response.get("status") == "success" and "chunk" in decoded_response:
                        return base64.b64decode(decoded_response["chunk"]) 
                    else:
                        print(f"[DOWNLOAD] Error en la respuesta del peer {peer_ip}:{peer_port}: {decoded_response.get('message', 'Mensaje de error desconocido')}")
                        return None
                except json.JSONDecodeError as json_e:
                    print(f"[DOWNLOAD] Datos RAW recibidos: {response_data.decode(errors='ignore')}") 
                    return None
            else:
                print(f"[DOWNLOAD] No se recibieron datos de chunk del peer {peer_ip}:{peer_port}.")
                return None

    except socket.timeout:
        print(f"[DOWNLOAD] Timeout al descargar chunk de {peer_ip}:{peer_port}.")
    except ConnectionRefusedError:
        print(f"[DOWNLOAD] Conexion rechazada por {peer_ip}:{peer_port} al descargar chunk.")
    except Exception as e:
        print(f"[DOWNLOAD] Error inesperado al descargar chunk de {peer_ip}:{peer_port}: {e}")
    
    return None

def get_file_info_from_peer(peer_ip, peer_port, filename):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(35) 
            s.connect((peer_ip, peer_port))

            request_message = {
                "command": "GET_FILE_INFO", 
                "filename": filename
            }
            s.sendall(json.dumps(request_message).encode())

            response_data = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response_data += chunk
            
            if response_data:
                try:
                    decoded_response = json.loads(response_data.decode())
                    if decoded_response.get("status") == "success":
                        return decoded_response
                    else:
                        return None
                except json.JSONDecodeError as json_e:
                    print(f"[PEER] Error al decodificar JSON de info del peer {peer_ip}:{peer_port}: {json_e}")
                    return None
            else:
                print(f"[PEER] No se recibieron datos de info del peer {peer_ip}:{peer_port}.")
                return None

    except socket.timeout:
        print(f"[PEER] Timeout al solicitar info del peer {peer_ip}:{peer_port}.")
    except ConnectionRefusedError:
        print(f"[PEER] Conexión rechazada por {peer_ip}:{peer_port} al solicitar info.")
    except Exception as e:
        print(f"[PEER] Error inesperado al solicitar info del peer {peer_ip}:{peer_port}: {e}")
    
    return None

def download_file(filename):
    filepath = os.path.join(RECEIVED_DIR, filename) 
    
    load_progress()
    downloaded_bytes_count = get_progress(filename)
    file_size = None 

    peers_for_info_and_download = get_peers_with_file(TRACKER_IP, TRACKER_PORT, filename)
    if not peers_for_info_and_download:
        print(f"[PEER] Ningún peer tiene el archivo '{filename}'.")
        return
    
    for peer_info in peers_for_info_and_download:
        if peer_info['ip'] == PEER_ADVERTISED_IP and peer_info['port'] == PEER_PORT:
            continue
        
        file_info = get_file_info_from_peer(peer_info['ip'], peer_info['port'], filename)
        if file_info and 'file_size' in file_info:
            file_size = file_info['file_size']
            break
    
    if file_size is None:
        print(f"[PEER] No se pudo obtener el tamaño del archivo '{filename}' de ningún peer disponible.")
        return 

    if os.path.exists(filepath):
        current_local_size = os.path.getsize(filepath)
        
        if current_local_size == file_size:
            print(f"[PEER] El archivo '{filename}' ya está completo. Actualizando tracker y saliendo.")
            remove_progress(filename) 
            register_or_update_peer(TRACKER_IP, TRACKER_PORT, PEER_ID, PEER_ADVERTISED_IP, PEER_PORT, SHARED_DIR, RECEIVED_DIR, initial_registration=False)
            return 
        elif current_local_size < file_size:
            print(f"[PEER] El archivo '{filename}' está incompleto ({current_local_size}/{file_size} bytes). Reanudando descarga.")
            downloaded_bytes_count = current_local_size 
            save_progress(filename, downloaded_bytes_count)
        else: 
            print(f"[PEER] Advertencia: El archivo '{filename}' local es más grande de lo esperado. Reiniciando descarga.")
            os.remove(filepath) 
            remove_progress(filename)
            downloaded_bytes_count = 0 
    else: 
        downloaded_bytes_count = 0 
        remove_progress(filename) 

    os.makedirs(RECEIVED_DIR, exist_ok=True)

    print(f"[PEER] Iniciando descarga de '{filename}' ({file_size} bytes). Progreso actual: {downloaded_bytes_count} bytes.")

    mode = "ab" if downloaded_bytes_count > 0 else "wb" 
    with open(filepath, mode) as f:
        if mode == "ab":
            f.seek(0, os.SEEK_END)

        with tqdm(initial=downloaded_bytes_count, total=file_size, unit="B", unit_scale=True,
                  desc=f"Descargando {filename}", ascii=True) as pbar:
            
            while downloaded_bytes_count < file_size:
                available_peers = get_peers_with_file(TRACKER_IP, TRACKER_PORT, filename)
                available_peers = [p for p in available_peers if not (p['ip'] == PEER_ADVERTISED_IP and p['port'] == PEER_PORT)]

                if not available_peers:
                    print(f"\n[PEER] Todos los peers con '{filename}' se desconectaron o no hay otros peers. Reintentando en 10 segundos...")
                    time.sleep(10)
                    continue
                
                random.shuffle(available_peers)
                chunk_index_for_display = downloaded_bytes_count // CHUNK_SIZE
                
                pbar.set_description(f"Descargando {filename} [Chunk {chunk_index_for_display}]")

                chunk_downloaded_this_iteration = False
                for peer in available_peers:
                    peer_ip, peer_port = peer['ip'], peer['port']
                    
                    chunk_index = downloaded_bytes_count // CHUNK_SIZE
                   # print(f"\n[PEER] Intentando descargar chunk {chunk_index} de '{filename}' desde {peer['peer_id']} ({peer_ip}:{peer_port})...") #descomentar para ver fragmentos 
                    
                    chunk_data = download_chunk_from_peer(peer_ip, peer_port, filename, chunk_index) 
                    
                    if chunk_data is not None and len(chunk_data) > 0:
                        f.write(chunk_data)
                        downloaded_bytes_count += len(chunk_data)
                        pbar.update(len(chunk_data))
                        save_progress(filename, downloaded_bytes_count)
                        time.sleep(1) 
                        chunk_downloaded_this_iteration = True
                        break 
                    else:
                        print(f"\n[PEER] No se pudo descargar el chunk {chunk_index} de {peer['peer_id']}.")
                        pass 
                
                if not chunk_downloaded_this_iteration and downloaded_bytes_count < file_size:
                    print(f"\n[PEER] No se pudo conectar con ningún peer para continuar la descarga de '{filename}'. Reintentando en 5 segundos...")
                    time.sleep(5)
    
    if downloaded_bytes_count >= file_size:
        print(f"\n[PEER] Descarga de '{filename}' completada.")
        remove_progress(filename) 
        register_or_update_peer(TRACKER_IP, TRACKER_PORT, PEER_ID, PEER_ADVERTISED_IP, PEER_PORT, SHARED_DIR, RECEIVED_DIR, initial_registration=False) 
    else:
        print(f"\n[PEER] Descarga de '{filename}' finalizada pero incompleta. Progreso guardado.")

def main_menu():
    while True:
        clear_console() 
        print(f"\n---------------------------------------------------------------------")
        print(f"|                     PEER {PEER_ID}                                     |")
        print(f"| IP Local (Bind): {PEER_BIND_IP}, Puerto: {PEER_PORT}                          |") 
        print(f"| IP Publicada (Tracker): {PEER_ADVERTISED_IP}                             |") 
        print(f"---------------------------------------------------------------------")
        print("1. Mostrar archivos locales")
        print("2. Mostrar archivos disponibles en la red")
        print("3. Descargar archivo")
        print("4. Forzar actualización de archivos compartidos al tracker")
        print("5. Salir")
        choice = input("Seleccione una opción: ")

        if choice == '1':
            print("\n--- Archivos Locales ---")
            local_files = [f for f in os.listdir(SHARED_DIR) if os.path.isfile(os.path.join(SHARED_DIR, f))]
            local_files.extend([f for f in os.listdir(RECEIVED_DIR) if os.path.isfile(os.path.join(RECEIVED_DIR, f))])
            if local_files:
                for f in sorted(list(set(local_files))): 
                    print(f"- {f}")
            else:
                print("No hay archivos locales.")
            input("\nPresione Enter para continuar...") 
        elif choice == '2':
            print("\n--- Archivos Disponibles en la Red (según el tracker) ---")
            network_status = get_network_status(TRACKER_IP, TRACKER_PORT)
            if network_status:
                file_to_peers = {}
                for pid, info in network_status.items():
                    if info.get('status') == 'activo': 
                        for f in info['files']:
                            if f not in file_to_peers:
                                file_to_peers[f] = []
                            file_to_peers[f].append(pid)
                if file_to_peers:
                    for f, peers in sorted(file_to_peers.items()):
                        print(f"- {f} (Disponible en nodos: {', '.join(peers)})")
                else:
                    print("No hay archivos disponibles en la red de peers activos.")
            else:
                print("[PEER] No se pudo obtener el estado de la red del tracker.")
            input("\nPresione Enter para continuar...") 
        elif choice == '3':
            print("\n--- Archivos Disponibles en la Red (según el tracker) ---")
            network_status = get_network_status(TRACKER_IP, TRACKER_PORT)
            if network_status:
                file_to_peers = {}
                for pid, info in network_status.items():
                    if info.get('status') == 'activo':
                        for f in info['files']:
                            if f not in file_to_peers:
                                file_to_peers[f] = []
                            file_to_peers[f].append(pid)
                if file_to_peers:
                    for f, peers in sorted(file_to_peers.items()):
                        print(f"- {f} (Disponible en nodos: {', '.join(peers)})")
                else:
                    print("No hay archivos disponibles en la red de peers activos.")
            else:
                print("[PEER] No se pudo obtener el estado de la red del tracker.")

            filename = input("Ingrese el nombre del archivo a descargar: ")
            threading.Thread(target=download_file, args=(filename,)).start()
            input("\nLa descarga ha comenzado en segundo plano. Presione Enter para continuar...")
        elif choice == '4':
            success = register_or_update_peer(TRACKER_IP, TRACKER_PORT, PEER_ID, PEER_ADVERTISED_IP, PEER_PORT, SHARED_DIR, RECEIVED_DIR, initial_registration=False)
            if success:
                print("\nArchivos locales actualizados en el tracker.")
            else:
                print("\nNo se pudieron actualizar los archivos en el tracker.")
            input("\nPresione Enter para continuar...")
        elif choice == '5':
            print("[PEER] Saliendo...")
            break
        else:
            print("Opción no válida. Intente de nuevo.")
            input("\nPresione Enter para continuar...")

def main():
    print("[PEER] Registrando peer con el tracker...")
    if not register_or_update_peer(TRACKER_IP, TRACKER_PORT, PEER_ID, PEER_ADVERTISED_IP, PEER_PORT, SHARED_DIR, RECEIVED_DIR, initial_registration=True):
        print("[PEER] Falló el registro inicial. Asegúrese de que el tracker esté corriendo.")
        exit() 
    print("[PEER] Registro exitoso. Iniciando servicios...")

    print(f"[PEER] Iniciando servicio de archivos en {PEER_BIND_IP}:{PEER_PORT}") 
    threading.Thread(target=start_listener, args=(PEER_BIND_IP, PEER_PORT, serve_file_handler), daemon=True).start() 

    threading.Thread(target=heartbeat_to_tracker, daemon=True).start()

    main_menu()

if __name__ == "__main__":
    main()