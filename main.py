#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CARRETTO MUSICALE - CONTROLLER PRINCIPALE
Autore: Michele Pietravalle
Data: 2025-06-15
Versione: 3.1

Sistema completo di controllo per il carretto musicale.
Ottimizzato per inviare comandi solo quando i valori cambiano significativamente.
"""

import threading
import time
import os
import sys
import glob
from modules.arduino_reader import ArduinoReader
from modules.gps_reader import GPSReader
from modules.music_engine import MusicEngine

# Cerca automaticamente le porte seriali disponibili
def find_serial_ports():
    # Trova tutte le porte seriali disponibili
    ports = glob.glob('/dev/tty[A-Za-z]*')
    
    arduino_port = None
    gps_port = None
    
    print(f"Porte seriali disponibili: {ports}")
    
    # Cerca porta Arduino (Nano) che tipicamente usa 9600 baud
    for p in ports:
        if 'ACM' in p or 'USB0' in p:
            arduino_port = p
            print(f"Porta Arduino rilevata: {arduino_port}")
            break
    
    # Cerca porta GPS (tipicamente la seconda USB a 9600 baud)
    for p in ports:
        if p != arduino_port and ('USB' in p or 'ACM' in p):
            gps_port = p
            print(f"Porta GPS rilevata: {gps_port}")
            break
    
    # Fallback a valori di default
    if not arduino_port:
        arduino_port = '/dev/ttyUSB0'
        print(f"Nessuna porta Arduino rilevata, usando default: {arduino_port}")
    
    if not gps_port:
        gps_port = '/dev/ttyUSB1'
        print(f"Nessuna porta GPS rilevata, usando default: {gps_port}")
    
    return arduino_port, gps_port

# Rendi disponibili tutte le informazioni nel log
print(f"Current Date and Time (UTC): {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}")
print(f"Current User's Login: {os.getlogin()}")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")

def main():
    print("\n===== CARRETTO MUSICALE v3.1 =====")
    print("Autore: Michele Pietravalle")
    print(f"Data: 2025-06-15, Utente: {os.getlogin()}")
    
    # Rileva automaticamente le porte seriali
    arduino_port, gps_port = find_serial_ports()
    
    # Inizializzazione dei moduli
    print("\nInizializzazione moduli...")
    
    arduino = ArduinoReader(arduino_port, baudrate=9600)
    arduino.start()
    print("✓ Arduino Reader avviato")

    gps = GPSReader(gps_port)
    gps.start()
    print("✓ GPS Reader avviato")

    # Usa direttamente la porta 57120 per SuperCollider
    music = MusicEngine(host="127.0.0.1", port=57120)
    music.start()
    print("✓ Music Engine avviato")

    print("\nCarretto musicale avviato e pronto!")
    print("Utilizzare i potenziometri per controllare la musica:")
    print("- POT1: Volume (0-1)")
    print("- POT2: BPM (60-180)")
    print("- POT3: Genere musicale")
    print("- POT4: Pattern (0-3)")
    print("\nCtrl+C per uscire.")
    
    # Valori precedenti per confronto
    prev_pots = {}
    prev_gps = {}
    
    # Contatore per aggiornamenti forzati periodici
    force_update_counter = 0
    
    # Soglia di cambiamento significativo
    change_threshold = 0.05  # 5% di cambiamento
    
    # Soglia di cambiamento minimo per il genere e il pattern
    # (questi richiedono una precisione maggiore)
    genre_pattern_threshold = 0.015  # 1.5% di cambiamento
    
    try:
        debug_counter = 0
        while True:
            # Leggi i valori attuali
            pots = arduino.get_values()
            gps_data = gps.get_data()
            
            # Verifica se i valori sono cambiati significativamente
            values_changed = False
            
            # Controlla i potenziometri
            if pots:
                for key, value in pots.items():
                    # Usa una soglia più bassa per pot3 (genere) e pot4 (pattern)
                    threshold = genre_pattern_threshold if key in ('pot3', 'pot4') else change_threshold
                    
                    if (key not in prev_pots or 
                        abs(value - prev_pots.get(key, 0)) > threshold):
                        values_changed = True
                        break
            
            # Controlla il GPS
            if gps_data and 'speed' in gps_data and gps_data['speed'] is not None:
                if ('speed' not in prev_gps or 
                    abs(gps_data['speed'] - prev_gps.get('speed', 0)) > 0.5):  # 0.5 km/h di differenza
                    values_changed = True
            
            # Forza un aggiornamento ogni ~10 secondi anche se i valori non cambiano
            force_update_counter += 1
            if force_update_counter >= 200:  # 200 * 0.05s = 10s
                values_changed = True
                force_update_counter = 0
                print("[INFO] Aggiornamento forzato periodico")
            
            # Aggiorna i moduli solo se i valori sono cambiati
            if values_changed:
                music.update(pots, gps_data)
                
                # Aggiorna i valori precedenti
                if pots:
                    prev_pots = pots.copy()
                if gps_data:
                    prev_gps = gps_data.copy()
                
                # Debug quando i valori cambiano
                print(f"[AGGIORNAMENTO] Potenziometri: {pots} | GPS: {gps_data}")
            
            # Debug ogni ~30 secondi indipendentemente dai cambiamenti
            debug_counter += 1
            if debug_counter >= 600:  # 600 * 0.05s = 30s
                print(f"[DEBUG] Potenziometri: {pots} | GPS: {gps_data}")
                debug_counter = 0

            time.sleep(0.05)  # 50ms di attesa
    except KeyboardInterrupt:
        print("\nArresto in corso...")
        arduino.stop()
        gps.stop()
        music.stop()
        print("Sistema arrestato correttamente.")

if __name__ == "__main__":
    main()
