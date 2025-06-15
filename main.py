#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CARRETTO MUSICALE - MAIN CONTROLLER
Autore: Michele Pietravalle
Data: 2025-06-15
Versione: 2.6

Questo script è ottimizzato per Raspberry Pi 4 e include supporto per GPS e potenziometri reali.
"""

import threading
import time
import os
import sys
import glob
from modules.arduino_reader import ArduinoReader
from modules.gps_reader import GPSReader
from modules.music_engine import MusicEngine
from modules.led_controller import LedController

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
print(f"Current Date and Time (UTC - YYYY-MM-DD HH:MM:SS formatted): {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}")
print(f"Current User's Login: {os.getlogin()}")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")

def main():
    # Rileva automaticamente le porte seriali
    arduino_port, gps_port = find_serial_ports()
    
    # Inizializzazione dei moduli
    # Nota: Arduino Nano usa 9600 baud
    arduino = ArduinoReader(arduino_port, baudrate=9600)
    arduino.start()

    gps = GPSReader(gps_port)
    gps.start()

    # Configurato per utilizzare la porta 57120 (porta confermata)
    music = MusicEngine(port=57120)
    music.start()

    # Puoi anche disabilitare i LED se non necessari sul Raspberry Pi
    try:
        leds = LedController(data_pins=[18, 13], led_count_per_pin=32)
        leds.start()
        led_enabled = True
    except Exception as e:
        print(f"LED controller non inizializzato: {e}")
        print("Il sistema continuerà senza supporto LED")
        led_enabled = False

    print("Carretto musicale avviato. Ctrl+C per uscire.")
    print(f"Data: 2025-06-15, Utente: {os.getlogin()}")
    
    try:
        debug_counter = 0
        while True:
            pots = arduino.get_values()
            gps_data = gps.get_data()
            
            # Aggiorna i moduli con i dati attuali
            music.update(pots, gps_data)
            
            if led_enabled:
                leds.update(pots, gps_data)

            # Debug ogni 1 secondo (~20 cicli da 0.05s)
            debug_counter += 1
            if debug_counter >= 20:
                print(f"[DEBUG] Potenziometri: {pots} | GPS: {gps_data}")
                debug_counter = 0

            time.sleep(0.05)  # 50ms di attesa per non sovraccaricare la CPU
    except KeyboardInterrupt:
        print("Arresto in corso...")
        arduino.stop()
        gps.stop()
        music.stop()
        if led_enabled:
            leds.stop()
        print("Sistema arrestato correttamente.")

if __name__ == "__main__":
    main()
