#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CARRETTO MUSICALE - ARDUINO READER
Autore: Michele Pietravalle
Data: 2025-06-15
Versione: 2.7

Questo modulo gestisce la comunicazione con Arduino Nano per leggere i potenziometri.
Adattato per il formato binario specifico: [0xFF, val1, val2, val3, val4]
"""

import threading
import time
import serial
import glob
import os

class ArduinoReader:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600):  # Nota: baudrate 9600
        """
        Inizializza il lettore Arduino
        
        Args:
            port: Porta seriale Arduino
            baudrate: Velocità di comunicazione (9600 per l'Arduino Nano)
        """
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        self.thread = None
        self.values = {
            'pot1': 0.5,  # Volume
            'pot2': 0.5,  # BPM
            'pot3': 0.5,  # Tune/Genre
            'pot4': 0.5   # Pattern
        }
        self.raw_values = {
            'pot1': 128,  # Volume (0-255)
            'pot2': 128,  # BPM (0-255)
            'pot3': 128,  # Tune/Genre (0-255)
            'pot4': 128   # Pattern (0-255)
        }
        self.last_values = self.values.copy()
        self.lock = threading.Lock()
        self.debug_counter = 0
        
        # Cerca tutte le porte seriali disponibili
        available_ports = self._find_available_ports()
        print(f"[ARDUINO] Porte seriali disponibili: {available_ports}")
        
        # Rileva automaticamente la porta Arduino
        self.port = self._auto_detect_port(available_ports)
        print(f"[ARDUINO] Usando porta: {self.port}")
        
    def _find_available_ports(self):
        """Trova tutte le porte seriali disponibili"""
        if os.name == 'nt':  # Windows
            return ['COM%s' % (i + 1) for i in range(256)]
        else:  # Linux/Mac
            ports = glob.glob('/dev/tty[A-Za-z]*')
            return ports
            
    def _auto_detect_port(self, available_ports):
        """Rileva automaticamente la porta Arduino"""
        # Prova la porta specificata
        if self.port in available_ports:
            return self.port
            
        # Altrimenti cerca porte Arduino comuni
        for port in available_ports:
            if 'ACM' in port or 'USB' in port:
                print(f"[ARDUINO] Rilevata porta Arduino: {port}")
                return port
                
        # Se non viene trovata, mantieni quella specificata
        print(f"[ARDUINO] Nessuna porta Arduino rilevata, usando: {self.port}")
        return self.port
        
    def start(self):
        """Avvia il thread di lettura"""
        if not self.running:
            self.running = True
            self.simulation_mode = False
            
            # Prova ad aprire la porta seriale
            try:
                print(f"[ARDUINO] Tentativo di apertura porta {self.port} a {self.baudrate} baud...")
                self.serial = serial.Serial(self.port, self.baudrate, timeout=1.0)
                time.sleep(2)  # Attesa per Arduino reset
                print(f"[ARDUINO] Porta {self.port} aperta con successo")
                
                # Leggi eventuali dati iniziali
                if self.serial.in_waiting > 0:
                    initial_data = self.serial.read(self.serial.in_waiting)
                    print(f"[ARDUINO] Dati iniziali: {initial_data.hex()}")
                
                self.thread = threading.Thread(target=self._read_thread)
                self.thread.daemon = True
                self.thread.start()
                print(f"[ARDUINO] Thread di lettura avviato")
            except Exception as e:
                print(f"[ARDUINO] Errore apertura porta {self.port}: {e}")
                print("[ARDUINO] Passaggio alla modalità simulazione")
                self.simulation_mode = True
                self.serial = None
                self.thread = threading.Thread(target=self._simulate_thread)
                self.thread.daemon = True
                self.thread.start()
        
    def stop(self):
        """Ferma il thread di lettura"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.serial:
            self.serial.close()
            self.serial = None
        print("[ARDUINO] Arrestato")
    
    def get_values(self):
        """Restituisce i valori correnti dei potenziometri"""
        with self.lock:
            # Adatta i potenziometri disponibili - il tuo Arduino ha 4 pot
            # ma potrebbero essere necessari 5 valori per il sistema
            values = self.values.copy()
            
            # Se non abbiamo pot5 nel tuo hardware, usa pot4 anche per pattern
            if 'pot5' not in values:
                values['pot5'] = values['pot4']
                
            return values
    
    def _read_thread(self):
        """Thread che legge i dati da Arduino in formato binario [0xFF, val1, val2, val3, val4]"""
        buffer = bytearray()
        marker = 0xFF  # Marker di inizio pacchetto
        packet_size = 5  # 1 byte marker + 4 bytes dati
        last_data_time = time.time()
        last_debug_time = time.time()
        data_received = False
        
        while self.running:
            try:
                if self.serial and self.serial.in_waiting > 0:
                    # Leggi un byte alla volta
                    byte = self.serial.read(1)[0]
                    
                    # Se è un marker di inizio, resetta il buffer
                    if byte == marker:
                        buffer = bytearray([byte])
                    # Altrimenti, aggiungi al buffer se non vuoto
                    elif buffer:
                        buffer.append(byte)
                    
                    # Se abbiamo un pacchetto completo
                    if len(buffer) == packet_size and buffer[0] == marker:
                        last_data_time = time.time()
                        data_received = True
                        
                        # Estrai i 4 valori dei potenziometri (bytes 1-4)
                        pot_values = [buffer[i] for i in range(1, 5)]
                        
                        # Debug periodico del pacchetto ricevuto
                        current_time = time.time()
                        if current_time - last_debug_time > 1.0:  # Debug ogni secondo
                            print(f"[ARDUINO] Pacchetto: {buffer.hex()} => Valori: {pot_values}")
                            last_debug_time = current_time
                        
                        # Normalizza i valori da 0-255 a 0.0-1.0
                        with self.lock:
                            # Salva i valori raw
                            self.raw_values['pot1'] = pot_values[0]
                            self.raw_values['pot2'] = pot_values[1]
                            self.raw_values['pot3'] = pot_values[2]
                            self.raw_values['pot4'] = pot_values[3]
                            
                            # Normalizza e salva i valori
                            self.values['pot1'] = pot_values[0] / 255.0
                            self.values['pot2'] = pot_values[1] / 255.0
                            self.values['pot3'] = pot_values[2] / 255.0
                            self.values['pot4'] = pot_values[3] / 255.0
                            
                            # Debug dei cambiamenti significativi
                            changed = False
                            for key in self.values.keys():
                                if abs(self.values[key] - self.last_values.get(key, 0)) > 0.02:
                                    changed = True
                            
                            if changed:
                                print(f"[ARDUINO] Valori raw: {self.raw_values}")
                                print(f"[ARDUINO] Valori normalizzati: {self.values}")
                                self.last_values = self.values.copy()
                        
                        # Resetta il buffer per il prossimo pacchetto
                        buffer = bytearray()
                
                # Verifica timeout - se non riceviamo dati per 10 secondi, avvisa
                if data_received and time.time() - last_data_time > 10:
                    print("[ARDUINO] ATTENZIONE: Nessun dato ricevuto da Arduino per 10 secondi!")
                    data_received = False
            except Exception as e:
                print(f"[ARDUINO] Errore lettura seriale: {e}")
                # Riconnessione in caso di errore
                if self.serial:
                    self.serial.close()
                try:
                    self.serial = serial.Serial(self.port, self.baudrate, timeout=1.0)
                    print(f"[ARDUINO] Riconnessione alla porta {self.port}")
                except Exception as reconnect_error:
                    print(f"[ARDUINO] Riconnessione fallita: {reconnect_error}")
                    time.sleep(5)  # Attesa prima di riprovare
            
            time.sleep(0.01)  # 10ms per non sovraccaricare la CPU
    
    def _simulate_thread(self):
        """Thread che simula i valori in caso di errore hardware"""
        print("[ARDUINO] Modalità simulazione attiva")
        step = 0
        
        while self.running:
            # Simula valori che cambiano
            step += 1
            with self.lock:
                # Volume oscilla lentamente
                self.values['pot1'] = 0.7 + 0.3 * ((step % 20) / 20.0)
                
                # BPM aumenta e diminuisce
                self.values['pot2'] = 0.3 + 0.4 * ((step % 30) / 30.0)
                
                # Tune rimane costante
                self.values['pot3'] = 0.5
                
                # Pattern/Genre cambia ogni 40 cicli
                if step % 40 == 0:
                    self.values['pot4'] = (int(self.values['pot4'] * 6 + 1) % 7) / 6.0
                    
                # Salva anche i valori raw simulati (0-255)
                self.raw_values['pot1'] = int(self.values['pot1'] * 255)
                self.raw_values['pot2'] = int(self.values['pot2'] * 255)
                self.raw_values['pot3'] = int(self.values['pot3'] * 255)
                self.raw_values['pot4'] = int(self.values['pot4'] * 255)
                    
            if step % 10 == 0:  # Ogni 10 step (circa 1 secondo) stampa i valori simulati
                print(f"[ARDUINO] Simulazione - valori: {self.values}")
                
            time.sleep(0.1)  # Aggiorna ogni 100ms

# Per test standalone
if __name__ == "__main__":
    reader = ArduinoReader()
    reader.start()
    try:
        while True:
            values = reader.get_values()
            print(f"Valori potenziometri: {values}")
            time.sleep(1)
    except KeyboardInterrupt:
        reader.stop()
