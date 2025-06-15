#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CARRETTO MUSICALE - COMPATIBILE CON SUPERCOLLIDER
Autore: Michele Pietravalle
Data: 2025-06-15 18:49:48
Utente: michelepietravalle
Versione: 9.0

Sistema completo che integra:
- Lettura dei potenziometri dall'Arduino originale con formato binario corretto
- Controllo delle strisce LED WS2812B (512 LED su GPIO 18 e 13) a tempo con la musica
- Generazione musicale controllata dai potenziometri con comunicazione OSC compatibile con SuperCollider
"""

import threading
import time
import os
import sys
import glob
import serial
import random
import math
import json
import signal
from pythonosc import dispatcher, osc_server, udp_client
from rpi_ws281x import *

# Configurazione LED
LED_COUNT = 512
LED_PIN1 = 18
LED_PIN2 = 13
LED_FREQ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 50
LED_INVERT = False
LED_CHANNEL1 = 0
LED_CHANNEL2 = 1

# Configurazione OSC
OSC_IP = "127.0.0.1" 
OSC_PORT = 5005      
OSC_CLIENT_PORT = 57120  # Porta SuperCollider

# Configurazione musicale
DEFAULT_BPM = 120
DEFAULT_VOLUME = 0.8
DEFAULT_GENRE = "dub"  # SuperCollider vuole una stringa
DEFAULT_PATTERN = 0    # SuperCollider vuole un intero

# Generi musicali disponibili (stringhe)
GENRES = ["dub", "techno", "reggae", "house", "drumandbass", "ambient", "trap"]

# Colori per i generi
GENRE_COLORS = {
    "dub": (255, 165, 0),      # Arancione
    "techno": (255, 255, 255),  # Bianco
    "reggae": (255, 255, 0),    # Giallo
    "house": (255, 0, 255),     # Magenta
    "drumandbass": (0, 0, 255), # Blu
    "ambient": (0, 255, 255),   # Ciano
    "trap": (128, 0, 128),      # Viola
    "default": (255, 255, 255)  # Bianco (predefinito)
}

# Modalità di visualizzazione
VIS_MODES = ["pulse", "spectrum", "chase", "flash", "rainbow", "blocks", "wave", "reactive"]

# Patterns musicali
PATTERN_NAMES = ["basic", "complex", "breakbeat", "minimal"]

# Soglie di cambiamento
CHANGE_THRESHOLD = 0.05  # 5% di cambiamento per la maggior parte dei controlli
GENRE_PATTERN_THRESHOLD = 0.015  # 1.5% per controlli più sensibili

# Debug OSC
DEBUG_OSC = True

class Logger:
    def __init__(self, console=True):
        self.console = console
    
    def info(self, message):
        if self.console:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] INFO: {message}")
    
    def error(self, message):
        if self.console:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] ERROR: {message}")
    
    def debug(self, message):
        if self.console:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] DEBUG: {message}")

class ArduinoReader:
    """Classe per leggere i valori dei potenziometri da Arduino in formato binario"""
    
    def __init__(self, port=None, baudrate=9600):
        self.logger = Logger()
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        self.thread = None
        # Solo 4 potenziometri come nell'Arduino originale
        self.values = {"pot1": 0.5, "pot2": 0.5, "pot3": 0.5, "pot4": 0.5}
        
        # Se non è specificata una porta, cerca automaticamente
        if not self.port:
            self.port = self.find_arduino_port()
        
        self.logger.info(f"ArduinoReader inizializzato, porta: {self.port}")
    
    def find_arduino_port(self):
        """Cerca automaticamente la porta seriale Arduino"""
        ports = glob.glob('/dev/tty[A-Za-z]*')
        
        self.logger.info(f"Porte seriali disponibili: {ports}")
        
        # Cerca prima USB0 o ACM0 che sono tipicamente usate da Arduino
        for p in ports:
            if 'USB0' in p or 'ACM0' in p:
                self.logger.info(f"Porta Arduino rilevata: {p}")
                return p
        
        # Fallback a tutte le altre porte
        for p in ports:
            if 'USB' in p or 'ACM' in p:
                self.logger.info(f"Possibile porta Arduino: {p}")
                return p
        
        # Default fallback
        self.logger.error("Nessuna porta Arduino trovata, usando /dev/ttyUSB0")
        return '/dev/ttyUSB0'
    
    def connect(self):
        """Connette all'Arduino"""
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Attendi che la connessione si stabilizzi
            # Svuota il buffer in ingresso
            self.serial.reset_input_buffer()
            self.logger.info(f"Connesso ad Arduino su {self.port}")
            return True
        except Exception as e:
            self.logger.error(f"Errore nella connessione ad Arduino: {e}")
            return False
    
    def read_values(self):
        """Legge i valori dai potenziometri usando il formato binario originale dell'Arduino"""
        if not self.serial:
            return False
        
        try:
            # Assicurati che ci siano abbastanza dati disponibili
            if self.serial.in_waiting >= 5:  # 1 byte di marker + 4 byte di dati
                marker = self.serial.read(1)[0]
                if marker == 0xFF:  # 0xFF è il marker di inizio dati
                    pot_data = self.serial.read(4)  # Leggi 4 byte per i 4 potenziometri
                    
                    # Aggiorna i valori (mappando da 0-255 a 0-1)
                    for i in range(4):
                        pot_name = f"pot{i+1}"
                        self.values[pot_name] = pot_data[i] / 255.0
                    
                    return True
                else:
                    # Se il primo byte non è 0xFF, svuota il buffer
                    self.serial.reset_input_buffer()
            
            return False
        except Exception as e:
            self.logger.error(f"Errore nella lettura dei potenziometri: {e}")
            # In caso di errore, chiudi e riapri la connessione seriale
            self.disconnect()
            return False
    
    def disconnect(self):
        """Disconnette dall'Arduino"""
        if self.serial:
            try:
                self.serial.close()
            except:
                pass
            self.serial = None
    
    def start(self):
        """Avvia il thread di lettura"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run)
            self.thread.daemon = True
            self.thread.start()
            self.logger.info("ArduinoReader avviato")
            return True
        return False
    
    def stop(self):
        """Ferma il thread di lettura"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        self.disconnect()
        self.logger.info("ArduinoReader fermato")
    
    def run(self):
        """Loop principale del thread di lettura"""
        reconnect_attempts = 0
        max_reconnect_attempts = 5
        
        while self.running:
            if not self.serial:
                # Tenta di riconnettersi
                if reconnect_attempts < max_reconnect_attempts:
                    self.logger.info(f"Tentativo di riconnessione ad Arduino ({reconnect_attempts + 1}/{max_reconnect_attempts})...")
                    if self.connect():
                        reconnect_attempts = 0
                    else:
                        reconnect_attempts += 1
                        time.sleep(2)  # Attendi prima di riprovare
                else:
                    self.logger.error(f"Impossibile connettersi ad Arduino dopo {max_reconnect_attempts} tentativi")
                    time.sleep(5)  # Attendere più a lungo prima di riprovare
                    reconnect_attempts = 0
            else:
                # Leggi i valori
                self.read_values()
                time.sleep(0.01)  # Breve pausa tra le letture
    
    def get_values(self):
        """Restituisce i valori dei potenziometri"""
        return self.values.copy()

class MusicEngine:
    """Engine per generare e controllare la musica"""
    
    def __init__(self, host=OSC_IP, port=OSC_CLIENT_PORT):
        self.logger = Logger()
        self.host = host
        self.port = port
        self.client = None
        
        # Parametri musicali
        self.volume = DEFAULT_VOLUME
        self.bpm = DEFAULT_BPM
        self.genre = DEFAULT_GENRE  # STRINGA per SuperCollider!
        self.pattern = DEFAULT_PATTERN
        
        # Effetti musicali
        self.fx1 = 0.5
        self.fx2 = 0.5
        self.fx3 = 0.5
        self.fx4 = 0.5
        
        # Flag per beat
        self.last_beat_time = 0
        self.beat_active = False
        
        # Valori precedenti per rilevare cambiamenti
        self.prev_values = {}
        
        # Inizializza il client OSC
        self.create_client()
        
        # Thread per beat e spettro
        self.running = False
        self.thread = None
        
        # Callback per il beat (usato per sincronizzare i LED)
        self.beat_callback = None
    
    def set_beat_callback(self, callback):
        """Imposta una callback da chiamare quando c'è un beat"""
        self.beat_callback = callback
    
    def create_client(self):
        """Crea un client OSC"""
        try:
            self.client = udp_client.SimpleUDPClient(self.host, self.port)
            self.logger.info(f"Client OSC creato per {self.host}:{self.port}")
            
            # Invia un ping di test per verificare la connessione
            self.client.send_message("/carretto/ping", 1)
            self.logger.info("Messaggio di ping OSC inviato")
            
            return True
        except Exception as e:
            self.logger.error(f"Errore nella creazione del client OSC: {e}")
            return False
    
    def update(self, pot_values, gps_data=None):
        """Aggiorna i parametri musicali dai valori dei potenziometri"""
        if not pot_values:
            return False
            
        # Debug per vedere i valori reali che arrivano
        if DEBUG_OSC:
            print(f"[UPDATE] Potenziometri: {pot_values}")
        
        try:
            # Volume (pot1)
            if "pot1" in pot_values:
                volume = pot_values["pot1"]
                self.set_volume(volume)
            
            # BPM (pot2)
            if "pot2" in pot_values:
                # Scala il pot2 da 0-1 a 60-180 BPM
                bpm = int(60 + pot_values["pot2"] * 120)
                self.set_bpm(bpm)
            
            # Genere (pot3)
            if "pot3" in pot_values:
                # Scala il pot3 da 0-1 a indice del genere (0-6)
                genre_index = int(pot_values["pot3"] * len(GENRES))
                genre_index = min(genre_index, len(GENRES) - 1)
                genre = GENRES[genre_index]
                self.set_genre(genre)  # SuperCollider vuole il nome del genere come stringa!
            
            # Pattern (pot4)
            if "pot4" in pot_values:
                # Scala il pot4 da 0-1 a 0-3 (4 pattern)
                pattern = int(pot_values["pot4"] * 4)
                pattern = min(pattern, 3)
                self.set_pattern(pattern)  # SuperCollider vuole un intero per il pattern!
            
            # Usa dati GPS se disponibili (opzionale)
            if gps_data and 'speed' in gps_data and gps_data['speed'] is not None:
                speed = gps_data['speed']
                self.send_message("/carretto/speed", speed)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Errore nell'aggiornamento dei parametri musicali: {e}")
            return False
    
    def set_volume(self, volume):
        """Imposta il volume e invia al server OSC"""
        volume = max(0.0, min(1.0, float(volume)))
        if volume != self.volume:
            self.volume = volume
            self.send_message("/carretto/volume", self.volume)
    
    def set_bpm(self, bpm):
        """Imposta il BPM e invia al server OSC"""
        bpm = max(60, min(180, int(bpm)))
        if bpm != self.bpm:
            self.bpm = bpm
            self.send_message("/carretto/bpm", self.bpm)
    
    def set_genre(self, genre):
        """Imposta il genere e invia al server OSC"""
        if genre in GENRES and genre != self.genre:
            self.genre = genre
            # SuperCollider si aspetta /carretto/pattern e una STRINGA per il genere
            self.send_message("/carretto/pattern", self.genre)
            self.logger.info(f"Genere impostato a {self.genre}")
    
    def set_pattern(self, pattern):
        """Imposta il pattern e invia al server OSC"""
        pattern = max(0, min(3, int(pattern)))
        if pattern != self.pattern:
            self.pattern = pattern
            # SuperCollider si aspetta /carretto/patternIdx e un INTERO per il pattern
            self.send_message("/carretto/patternIdx", self.pattern)
            
            pattern_name = PATTERN_NAMES[pattern] if pattern < len(PATTERN_NAMES) else "unknown"
            self.logger.info(f"Pattern impostato a {self.pattern} ({pattern_name})")
    
    def send_message(self, address, value):
        """Invia un messaggio OSC con log dettagliato"""
        if self.client:
            try:
                self.client.send_message(address, value)
                if DEBUG_OSC:
                    print(f"[OSC] Inviato: {address} = {value}")
                return True
            except Exception as e:
                self.logger.error(f"Errore nell'invio OSC a {address}: {e}")
        return False
    
    def send_beat(self):
        """Invia un beat e attiva il flag di beat"""
        self.send_message("/carretto/beat", 1)
        
        # Aggiorna lo stato del beat
        self.last_beat_time = time.time()
        self.beat_active = True
        
        # Chiamiamo la callback per il beat se è impostata
        if self.beat_callback:
            self.beat_callback(True)
    
    def send_spectrum(self):
        """Invia dati spettro simulati"""
        if not self.client:
            return
        
        bands = 16
        spectrum = []
        
        # Simula diverse forme di spettro in base al genere
        if self.genre == "techno":
            # Picchi alle basse e alte frequenze
            for i in range(bands):
                if i < 3 or i > bands - 3:
                    value = random.uniform(0.7, 1.0)
                else:
                    value = random.uniform(0.3, 0.6)
                spectrum.append(value)
        elif self.genre == "drumandbass":
            # Picchi bassi forti e alti intermittenti
            for i in range(bands):
                if i < 4:
                    value = random.uniform(0.8, 1.0)
                elif i > bands - 4 and random.random() > 0.5:
                    value = random.uniform(0.7, 0.9)
                else:
                    value = random.uniform(0.2, 0.5)
                spectrum.append(value)
        elif self.genre == "ambient":
            # Distribuzione più uniforme, meno picchi
            for i in range(bands):
                value = random.uniform(0.3, 0.7)
                spectrum.append(value)
        else:
            # Generico
            for i in range(bands):
                # Più movimento nelle frequenze basse
                if i < bands / 3:
                    value = random.uniform(0.5, 1.0)
                # Frequenze medie
                elif i < bands * 2 / 3:
                    value = random.uniform(0.3, 0.8)
                # Frequenze alte
                else:
                    value = random.uniform(0.1, 0.5)
                spectrum.append(value)
        
        # Moltiplica per il volume
        spectrum = [x * self.volume for x in spectrum]
        
        # Invia lo spettro
        self.client.send_message("/carretto/spectrum", spectrum)
    
    def start(self):
        """Avvia l'engine musicale"""
        if not self.running:
            if not self.client:
                self.create_client()
            
            # Invia i valori iniziali
            self.set_volume(self.volume)
            self.set_bpm(self.bpm)
            self.set_genre(self.genre)
            self.set_pattern(self.pattern)
            
            self.running = True
            self.thread = threading.Thread(target=self.run)
            self.thread.daemon = True
            self.thread.start()
            self.logger.info("MusicEngine avviato")
            return True
        return False
    
    def stop(self):
        """Ferma l'engine musicale"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        self.logger.info("MusicEngine fermato")
    
    def run(self):
        """Loop principale per inviare beat e spettro"""
        last_spectrum_time = 0
        last_beat_time = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Calcola il tempo tra i beat
                beat_interval = 60.0 / max(1, self.bpm)
                
                # Invia beat al momento giusto
                if current_time - last_beat_time >= beat_interval:
                    self.send_beat()
                    last_beat_time = current_time
                
                # Invia dati spettro più frequentemente (10 volte al secondo)
                if current_time - last_spectrum_time >= 0.1:
                    self.send_spectrum()
                    last_spectrum_time = current_time
                
                # Controlla se il beat è ancora attivo (durata 100ms)
                if self.beat_active and current_time - self.last_beat_time > 0.1:
                    self.beat_active = False
                    # Inviamo il segnale di fine beat
                    if self.beat_callback:
                        self.beat_callback(False)
                
                # Breve pausa
                time.sleep(0.01)
            except Exception as e:
                self.logger.error(f"Errore nel loop dell'engine musicale: {e}")
                time.sleep(0.1)  # Pausa più lunga in caso di errore

class LedController:
    """Controller per le strisce LED"""
    
    def __init__(self):
        self.logger = Logger()
        
        # Inizializza strisce
        self.strip1 = None
        self.strip2 = None
        
        # Stato attuale
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        
        # Stato della musica
        self.current_genre = DEFAULT_GENRE  # Nome del genere
        self.current_bpm = DEFAULT_BPM
        self.current_volume = DEFAULT_VOLUME
        self.beat_counter = 0
        self.last_beat_time = 0
        self.visualization_mode = "pulse"
        self.next_beat_time = 0
        self.spectrum_data = [0.0] * 16  # Dati spettro audio (16 bande)
        
        # Effetti extra
        self.fx1_value = 0.5  # Valore effetto 1 (generico)
        self.fx2_value = 0.5  # Valore effetto 2 (generico)
        self.fx3_value = 0.5  # Valore effetto 3 (generico)
        
        # Flag per il beat in corso
        self.beat_active = False
        
        # Inizializza le strisce
        self.initialize_strips()
    
    def initialize_strips(self):
        """Inizializza entrambe le strisce LED"""
        try:
            # Inizializza striscia 1
            self.strip1 = Adafruit_NeoPixel(
                LED_COUNT,
                LED_PIN1,
                LED_FREQ,
                LED_DMA,
                LED_INVERT,
                LED_BRIGHTNESS,
                LED_CHANNEL1
            )
            self.strip1.begin()
            
            # Inizializza striscia 2
            self.strip2 = Adafruit_NeoPixel(
                LED_COUNT,
                LED_PIN2,
                LED_FREQ,
                LED_DMA,
                LED_INVERT,
                LED_BRIGHTNESS,
                LED_CHANNEL2
            )
            self.strip2.begin()
            
            self.logger.info(f"Strisce LED inizializzate: {LED_COUNT} LED su GPIO {LED_PIN1} e {LED_PIN2}")
            return True
        except Exception as e:
            self.logger.error(f"Errore nell'inizializzazione delle strisce LED: {e}")
            return False
    
    def clear_all(self):
        """Spegne tutti i LED su entrambe le strisce"""
        with self.lock:
            if self.strip1:
                for i in range(self.strip1.numPixels()):
                    self.strip1.setPixelColor(i, Color(0, 0, 0))
                self.strip1.show()
            
            if self.strip2:
                for i in range(self.strip2.numPixels()):
                    self.strip2.setPixelColor(i, Color(0, 0, 0))
                self.strip2.show()
    
    def set_brightness(self, brightness):
        """Imposta la luminosità di entrambe le strisce"""
        brightness = max(0, min(255, int(brightness)))
        
        with self.lock:
            if self.strip1:
                self.strip1.setBrightness(brightness)
                self.strip1.show()
            if self.strip2:
                self.strip2.setBrightness(brightness)
                self.strip2.show()
        
        self.logger.info(f"Luminosità impostata a {brightness}")
    
    def wheel(self, pos):
        """Genera un colore dal ciclo RGB"""
        pos = int(pos % 256)
        if pos < 85:
            return Color(pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return Color(255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return Color(0, pos * 3, 255 - pos * 3)
    
    def get_genre_color(self, genre=None, intensity=1.0):
        """Ottiene il colore associato a un genere musicale con intensità variabile"""
        if not genre:
            genre = self.current_genre
        
        # Assicurati che l'intensità sia un float reale
        intensity = float(intensity)
        
        if genre in GENRE_COLORS:
            r, g, b = GENRE_COLORS[genre]
        else:
            r, g, b = GENRE_COLORS["default"]
        
        # Assicurati che r, g, b siano interi positivi
        r = max(0, int(float(r) * intensity))
        g = max(0, int(float(g) * intensity))
        b = max(0, int(float(b) * intensity))
        
        return Color(r, g, b)
    
    def start(self):
        """Avvia il controller LED"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run)
            self.thread.daemon = True
            self.thread.start()
            self.logger.info("Controller LED avviato")
    
    def stop(self):
        """Ferma il controller LED"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        self.clear_all()
        self.logger.info("Controller LED fermato")
    
    def update_genre(self, genre):
        """Aggiorna il genere musicale corrente"""
        if genre in GENRES:
            self.logger.info(f"Genere musicale cambiato: {genre}")
            self.current_genre = genre
            
            # Adatta la modalità di visualizzazione in base al genere
            if genre == "ambient":
                self.visualization_mode = "pulse"
            elif genre == "techno":
                self.visualization_mode = "flash"
            elif genre == "dub":
                self.visualization_mode = "blocks"
            elif genre == "reggae":
                self.visualization_mode = "rainbow"
            elif genre == "house":
                self.visualization_mode = "chase"
            elif genre == "drumandbass":
                self.visualization_mode = "spectrum"
            elif genre == "trap":
                self.visualization_mode = "wave"
            else:
                self.visualization_mode = "pulse"
    
    def update_bpm(self, bpm):
        """Aggiorna il BPM corrente"""
        try:
            self.current_bpm = float(bpm)
        except (ValueError, TypeError):
            self.logger.error(f"BPM non valido: {bpm}")
            self.current_bpm = DEFAULT_BPM
    
    def update_volume(self, volume):
        """Aggiorna il volume corrente"""
        try:
            self.current_volume = float(volume)
        except (ValueError, TypeError):
            self.logger.error(f"Volume non valido: {volume}")
            self.current_volume = DEFAULT_VOLUME
    
    def on_beat(self, active):
        """Callback per i beat - sincronizza con l'engine musicale"""
        if active:
            self.beat_counter += 1
            self.last_beat_time = time.time()
            self.beat_active = True
        else:
            self.beat_active = False
    
    def update_spectrum(self, spectrum_values):
        """Aggiorna i dati dello spettro audio"""
        self.spectrum_data = spectrum_values
    
    def set_visualization_mode(self, mode):
        """Imposta la modalità di visualizzazione"""
        if mode in VIS_MODES:
            self.visualization_mode = mode
            self.logger.info(f"Modalità di visualizzazione impostata a {mode}")
    
    def run(self):
        """Loop principale del controller LED"""
        while self.running:
            try:
                # Aggiorna l'effetto visivo in base alla modalità corrente
                if self.visualization_mode == "pulse":
                    self.effect_pulse()
                elif self.visualization_mode == "spectrum":
                    self.effect_spectrum()
                elif self.visualization_mode == "chase":
                    self.effect_chase()
                elif self.visualization_mode == "flash":
                    self.effect_flash()
                elif self.visualization_mode == "rainbow":
                    self.effect_rainbow()
                elif self.visualization_mode == "blocks":
                    self.effect_blocks()
                elif self.visualization_mode == "wave":
                    self.effect_wave()
                elif self.visualization_mode == "reactive":
                    self.effect_reactive()
            except Exception as e:
                self.logger.error(f"Errore nell'effetto {self.visualization_mode}: {e}")
            
            # Breve pausa per evitare di sovraccaricare la CPU
            time.sleep(0.01)
    
    def effect_pulse(self):
        """Effetto pulsazione sul beat"""
        # Calcola l'intensità della pulsazione
        time_since_beat = time.time() - self.last_beat_time
        beat_interval = 60.0 / self.current_bpm
        phase = min(1.0, time_since_beat / beat_interval)
        
        # Intensità basata sulla fase del beat
        intensity = 0.5 + 0.5 * math.cos(phase * 2 * math.pi)
        
        # Ottieni il colore con l'intensità appropriata
        color = self.get_genre_color(intensity=intensity)
        
        with self.lock:
            # Applica a striscia 1
            for i in range(self.strip1.numPixels()):
                self.strip1.setPixelColor(i, color)
            self.strip1.show()
            
            # Applica a striscia 2
            for i in range(self.strip2.numPixels()):
                self.strip2.setPixelColor(i, color)
            self.strip2.show()
    
    def effect_spectrum(self):
        """Effetto simulazione spettro audio"""
        # Se non abbiamo dati spettro, usiamo una simulazione
        if all(x == 0 for x in self.spectrum_data):
            # Simula 16 bande di frequenza
            bands = 16
            simulated_spectrum = []
            for i in range(bands):
                # Più movimento nelle frequenze basse
                if i < bands / 3:
                    value = random.uniform(0.5, 1.0)
                # Frequenze medie
                elif i < bands * 2 / 3:
                    value = random.uniform(0.3, 0.8)
                # Frequenze alte
                else:
                    value = random.uniform(0.1, 0.5)
                simulated_spectrum.append(value)
            
            # Applica un po' di smoothing temporale
            if not hasattr(self, 'last_spectrum'):
                self.last_spectrum = simulated_spectrum
            else:
                # Mix tra il vecchio spettro e quello nuovo
                alpha = 0.7  # Peso del nuovo spettro
                for i in range(bands):
                    self.last_spectrum[i] = alpha * simulated_spectrum[i] + (1-alpha) * self.last_spectrum[i]
                simulated_spectrum = self.last_spectrum
            
            self.spectrum_data = simulated_spectrum
        
        # Numero di LED per banda
        leds_per_band_1 = max(1, self.strip1.numPixels() // len(self.spectrum_data))
        leds_per_band_2 = max(1, self.strip2.numPixels() // len(self.spectrum_data))
        
        # Colore base del genere
        r, g, b = GENRE_COLORS.get(self.current_genre, GENRE_COLORS["default"])
        
        with self.lock:
            # Striscia 1
            for band, value in enumerate(self.spectrum_data):
                # Calcola quanti LED accendere per questa banda
                num_leds = int(leds_per_band_1 * value)
                start_led = band * leds_per_band_1
                
                # Accendi i LED proporzionalmente al valore della banda
                for i in range(start_led, start_led + leds_per_band_1):
                    if i < self.strip1.numPixels():
                        if i < start_led + num_leds:
                            # Varia l'intensità in base alla posizione
                            intensity = (i - start_led) / max(1, num_leds)
                            color = Color(
                                int(r * value * (1.0 - intensity * 0.5)),
                                int(g * value * (1.0 - intensity * 0.5)),
                                int(b * value * (1.0 - intensity * 0.5))
                            )
                            self.strip1.setPixelColor(i, color)
                        else:
                            self.strip1.setPixelColor(i, Color(0, 0, 0))
            self.strip1.show()
            
            # Striscia 2 - versione speculare
            for band, value in enumerate(self.spectrum_data):
                # Calcola quanti LED accendere per questa banda
                num_leds = int(leds_per_band_2 * value)
                start_led = (len(self.spectrum_data) - band - 1) * leds_per_band_2
                
                # Accendi i LED proporzionalmente al valore della banda
                for i in range(start_led, start_led + leds_per_band_2):
                    if i < self.strip2.numPixels():
                        if i < start_led + num_leds:
                            # Varia l'intensità in base alla posizione
                            intensity = (i - start_led) / max(1, num_leds)
                            color = Color(
                                int(r * value * (1.0 - intensity * 0.5)),
                                int(g * value * (1.0 - intensity * 0.5)),
                                int(b * value * (1.0 - intensity * 0.5))
                            )
                            self.strip2.setPixelColor(i, color)
                        else:
                            self.strip2.setPixelColor(i, Color(0, 0, 0))
            self.strip2.show()
    
    def effect_chase(self):
        """Effetto inseguimento"""
        # Determina la velocità dell'inseguimento in base al BPM
        speed_factor = self.current_bpm / 120.0
        
        # Calcola la posizione in base al tempo
        position = int((time.time() * speed_factor * 50) % self.strip1.numPixels())
        
        # Lunghezza del segmento illuminato
        segment_length = max(1, int(self.strip1.numPixels() / 10))
        
        # Colore del genere corrente
        color = self.get_genre_color()
        
        with self.lock:
            # Striscia 1
            for i in range(self.strip1.numPixels()):
                # Distanza dal punto di inseguimento
                distance = (i - position) % self.strip1.numPixels()
                if distance < segment_length:
                    # Fade all'interno del segmento
                    intensity = 1.0 - (distance / segment_length)
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                    adjusted_color = Color(
                        int(r * intensity),
                        int(g * intensity),
                        int(b * intensity)
                    )
                    self.strip1.setPixelColor(i, adjusted_color)
                else:
                    self.strip1.setPixelColor(i, Color(0, 0, 0))
            self.strip1.show()
            
            # Striscia 2 - movimento opposto
            reversed_position = self.strip2.numPixels() - position - 1
            for i in range(self.strip2.numPixels()):
                # Distanza dal punto di inseguimento
                distance = (i - reversed_position) % self.strip2.numPixels()
                if distance < segment_length:
                    # Fade all'interno del segmento
                    intensity = 1.0 - (distance / segment_length)
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                    adjusted_color = Color(
                        int(r * intensity),
                        int(g * intensity),
                        int(b * intensity)
                    )
                    self.strip2.setPixelColor(i, adjusted_color)
                else:
                    self.strip2.setPixelColor(i, Color(0, 0, 0))
            self.strip2.show()
    
    def effect_flash(self):
        """Effetto flash sul beat"""
        # Se siamo su un beat attivo, accendi tutto
        if self.beat_active:
            color = self.get_genre_color()
            
            with self.lock:
                # Striscia 1
                for i in range(self.strip1.numPixels()):
                    self.strip1.setPixelColor(i, color)
                self.strip1.show()
                
                # Striscia 2
                for i in range(self.strip2.numPixels()):
                    self.strip2.setPixelColor(i, color)
                self.strip2.show()
        else:
            # Tra i beat, intensità proporzionale alla distanza dal prossimo beat
            time_since_beat = time.time() - self.last_beat_time
            beat_interval = 60.0 / self.current_bpm
            remaining = 1.0 - min(1.0, time_since_beat / beat_interval)
            
            # Estingui rapidamente
            intensity = remaining * remaining  # Decadimento quadratico
            
            if intensity < 0.05:
                # Se l'intensità è troppo bassa, spegni tutto
                with self.lock:
                    # Striscia 1
                    for i in range(self.strip1.numPixels()):
                        self.strip1.setPixelColor(i, Color(0, 0, 0))
                    self.strip1.show()
                    
                    # Striscia 2
                    for i in range(self.strip2.numPixels()):
                        self.strip2.setPixelColor(i, Color(0, 0, 0))
                    self.strip2.show()
    
    def effect_rainbow(self):
        """Effetto arcobaleno"""
        # Velocità dell'arcobaleno proporzionale al BPM
        speed_factor = self.current_bpm / 120.0
        
        offset = int(time.time() * speed_factor * 30) % 256
        
        with self.lock:
            # Striscia 1
            for i in range(self.strip1.numPixels()):
                position = int((i * 1.0 + offset) % 256)
                self.strip1.setPixelColor(i, self.wheel(position))
            self.strip1.show()
            
            # Striscia 2 - direzione opposta
            for i in range(self.strip2.numPixels()):
                position = int((self.strip2.numPixels() - i) * 1.0 + offset) % 256
                self.strip2.setPixelColor(i, self.wheel(position))
            self.strip2.show()
    
    def effect_blocks(self):
        """Effetto blocchi alternati"""
        # Numero di blocchi proporzionale al BPM
        num_blocks = max(2, int(self.current_bpm / 30))
        block_size_1 = max(1, self.strip1.numPixels() // num_blocks)
        block_size_2 = max(1, self.strip2.numPixels() // num_blocks)
        
        # Pattern di blocchi che si alterna sul beat
        pattern = (self.beat_counter % 2) == 0
        
        # Colore del genere corrente
        color = self.get_genre_color()
        
        with self.lock:
            # Striscia 1
            for block in range(num_blocks):
                block_color = color if (block % 2) == pattern else Color(0, 0, 0)
                start = block * block_size_1
                end = start + block_size_1
                
                for i in range(start, min(end, self.strip1.numPixels())):
                    self.strip1.setPixelColor(i, block_color)
            self.strip1.show()
            
            # Striscia 2 - pattern inverso
            for block in range(num_blocks):
                block_color = color if (block % 2) != pattern else Color(0, 0, 0)
                start = block * block_size_2
                end = start + block_size_2
                
                for i in range(start, min(end, self.strip2.numPixels())):
                    self.strip2.setPixelColor(i, block_color)
            self.strip2.show()
    
    def effect_wave(self):
        """Effetto onda musicale"""
        # Parametri dell'onda
        time_val = time.time()
        speed = self.current_bpm / 60.0  # Velocità proporzionale al BPM
        
        # Ottieni il colore base
        base_color = self.get_genre_color()
        r_base = (base_color >> 16) & 0xFF
        g_base = (base_color >> 8) & 0xFF
        b_base = base_color & 0xFF
        
        with self.lock:
            # Striscia 1 - onda sinusoidale
            for i in range(self.strip1.numPixels()):
                # Posizione normalizzata
                pos = i / max(1, self.strip1.numPixels())
                
                # Valore dell'onda
                wave_val = 0.5 + 0.5 * math.sin(speed * time_val * 2 * math.pi + pos * 4 * math.pi)
                
                # Calcola il colore in base al valore dell'onda
                r = int(r_base * wave_val)
                g = int(g_base * wave_val)
                b = int(b_base * wave_val)
                
                self.strip1.setPixelColor(i, Color(r, g, b))
            self.strip1.show()
            
            # Striscia 2 - onda cosinusoidale (sfasata)
            for i in range(self.strip2.numPixels()):
                # Posizione normalizzata
                pos = i / max(1, self.strip2.numPixels())
                
                # Valore dell'onda (sfasata)
                wave_val = 0.5 + 0.5 * math.cos(speed * time_val * 2 * math.pi + pos * 4 * math.pi)
                
                # Calcola il colore in base al valore dell'onda
                r = int(r_base * wave_val)
                g = int(g_base * wave_val)
                b = int(b_base * wave_val)
                
                self.strip2.setPixelColor(i, Color(r, g, b))
            self.strip2.show()
    
    def effect_reactive(self):
        """Effetto reattivo al volume"""
        # Applica il volume
        react_val = self.current_volume
        
        # Colore base del genere
        color = self.get_genre_color()
        
        with self.lock:
            # Striscia 1 - dal centro verso l'esterno
            mid_point = self.strip1.numPixels() // 2
            for i in range(self.strip1.numPixels()):
                # Distanza dal centro
                distance = abs(i - mid_point)
                max_distance = max(1, self.strip1.numPixels() // 2)
                
                # Normalizza la distanza
                norm_distance = distance / max_distance
                
                if norm_distance <= react_val:
                    # Intensità basata sulla distanza dal centro
                    intensity = 1.0 - norm_distance
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                    
                    self.strip1.setPixelColor(i, Color(
                        int(r * intensity),
                        int(g * intensity),
                        int(b * intensity)
                    ))
                else:
                    self.strip1.setPixelColor(i, Color(0, 0, 0))
            self.strip1.show()
            
            # Striscia 2 - dall'esterno verso il centro
            mid_point = self.strip2.numPixels() // 2
            for i in range(self.strip2.numPixels()):
                # Distanza dal centro
                distance = abs(i - mid_point)
                max_distance = max(1, self.strip2.numPixels() // 2)
                
                # Normalizza la distanza invertita
                norm_distance = 1.0 - (distance / max_distance)
                
                if norm_distance <= react_val:
                    # Intensità basata sulla distanza dal centro
                    intensity = norm_distance
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                    
                    self.strip2.setPixelColor(i, Color(
                        int(r * intensity),
                        int(g * intensity),
                        int(b * intensity)
                    ))
                else:
                    self.strip2.setPixelColor(i, Color(0, 0, 0))
            self.strip2.show()

class OscInterface:
    """Interfaccia OSC per comunicare con altri sistemi"""
    
    def __init__(self, led_controller=None, music_engine=None):
        self.logger = Logger()
        self.led_controller = led_controller
        self.music_engine = music_engine
        
        # Inizializza server e client
        self.dispatcher = dispatcher.Dispatcher()
        self.server = None
        self.client = None
        
        # Configura i gestori di messaggi
        self.setup_handlers()
    
    def setup_handlers(self):
        """Configura i gestori di messaggi OSC"""
        # Handler per i beat
        self.dispatcher.map("/carretto/beat", self.on_beat)
        
        # Handler per il BPM
        self.dispatcher.map("/carretto/bpm", self.on_bpm)
        
        # Handler per il genere musicale
        self.dispatcher.map("/carretto/pattern", self.on_genre)
        
        # Handler per il volume
        self.dispatcher.map("/carretto/volume", self.on_volume)
        
        # Handler per lo spettro audio
        self.dispatcher.map("/carretto/spectrum", self.on_spectrum)
        
        # Handler per la modalità di visualizzazione
        self.dispatcher.map("/carretto/mode", self.on_mode)
        
        # Handler per comandi generici
        self.dispatcher.map("/carretto/command", self.on_command)
    
    def on_beat(self, address, *args):
        """Handler per i beat musicali"""
        if self.led_controller:
            self.led_controller.on_beat(True)  # Passa il beat direttamente
    
    def on_bpm(self, address, bpm):
        """Handler per il BPM"""
        if self.led_controller:
            self.led_controller.update_bpm(bpm)
    
    def on_genre(self, address, genre):
        """Handler per il genere musicale - SuperCollider invia una stringa"""
        if self.led_controller:
            self.led_controller.update_genre(genre)
    
    def on_volume(self, address, volume):
        """Handler per il volume"""
        if self.led_controller:
            self.led_controller.update_volume(volume)
    
    def on_spectrum(self, address, *args):
        """Handler per lo spettro audio"""
        if self.led_controller:
            # Converti gli argomenti in una lista di valori float
            spectrum_data = [float(x) for x in args]
            self.led_controller.update_spectrum(spectrum_data)
    
    def on_mode(self, address, mode):
        """Handler per la modalità di visualizzazione"""
        if self.led_controller and mode in VIS_MODES:
            self.led_controller.set_visualization_mode(mode)
    
    def on_command(self, address, cmd, *args):
        """Handler per comandi generici"""
        self.logger.info(f"Comando ricevuto: {cmd}, args: {args}")
        
        if cmd == "start":
            if self.led_controller:
                self.led_controller.start()
        
        elif cmd == "stop":
            if self.led_controller:
                self.led_controller.stop()
    
    def start_server(self):
        """Avvia il server OSC"""
        try:
            self.server = osc_server.ThreadingOSCUDPServer(
                (OSC_IP, OSC_PORT), self.dispatcher)
            server_thread = threading.Thread(target=self.server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            self.logger.info(f"Server OSC avviato su {OSC_IP}:{OSC_PORT}")
            return True
        except Exception as e:
            self.logger.error(f"Errore nell'avvio del server OSC: {e}")
            return False
    
    def start(self):
        """Avvia l'interfaccia OSC"""
        success = self.start_server()
        return success
    
    def stop(self):
        """Ferma l'interfaccia OSC"""
        if self.server:
            self.server.shutdown()
            self.logger.info("Server OSC fermato")

class CarrettoSystem:
    """Sistema completo che integra tutti i componenti"""
    
    def __init__(self):
        self.logger = Logger()
        
        # Componenti del sistema
        self.arduino_reader = None
        self.music_engine = None
        self.led_controller = None
        self.osc_interface = None
        
        # Stato del sistema
        self.running = False
        
        # Inizializza gestori di segnali
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Gestisce segnali di interruzione"""
        self.logger.info(f"Segnale ricevuto: {sig}")
        self.stop()
    
    def initialize(self):
        """Inizializza tutti i componenti del sistema"""
        self.logger.info("Inizializzazione del sistema Carretto Musicale...")
        
        # Inizializza il controller LED
        self.led_controller = LedController()
        
        # Inizializza l'engine musicale
        self.music_engine = MusicEngine()
        
        # Registra la callback per il beat
        self.music_engine.set_beat_callback(self.led_controller.on_beat)
        
        # Inizializza prima Arduino per la lettura dei potenziometri
        self.arduino_reader = ArduinoReader()
        
        # Inizializza l'interfaccia OSC
        self.osc_interface = OscInterface(
            self.led_controller,
            self.music_engine
        )
        
        self.logger.info("Inizializzazione completata")
        return True
    
    def start(self):
        """Avvia il sistema"""
        if self.running:
            self.logger.warning("Il sistema è già in esecuzione")
            return False
        
        self.logger.info("Avvio del sistema Carretto Musicale...")
        
        # Assicurati che i componenti siano inizializzati
        if not self.arduino_reader or not self.music_engine or not self.led_controller or not self.osc_interface:
            if not self.initialize():
                self.logger.error("Errore nell'inizializzazione del sistema")
                return False
        
        # Avvia l'Arduino reader
        self.arduino_reader.start()
        
        # Avvia l'interfaccia OSC
        self.osc_interface.start()
        
        # Avvia l'engine musicale
        self.music_engine.start()
        
        # Avvia il controller LED
        self.led_controller.start()
        
        self.running = True
        self.logger.info("Sistema Carretto Musicale avviato")
        return True
    
    def stop(self):
        """Ferma il sistema"""
        if not self.running:
            return
        
        self.logger.info("Arresto del sistema Carretto Musicale...")
        
        # Ferma i componenti
        if self.arduino_reader:
            self.arduino_reader.stop()
        
        if self.music_engine:
            self.music_engine.stop()
        
        if self.led_controller:
            self.led_controller.stop()
        
        if self.osc_interface:
            self.osc_interface.stop()
        
        self.running = False
        self.logger.info("Sistema Carretto Musicale arrestato")
    
    def run(self):
        """Esegue il sistema in modalità interattiva"""
        if not self.running:
            self.start()
        
        self.logger.info("Sistema in esecuzione. Premi Ctrl+C per terminare.")
        
        # Valori precedenti per confronto
        prev_pots = {}
        
        # Contatore per aggiornamenti forzati periodici
        force_update_counter = 0
        
        try:
            debug_counter = 0
            while self.running:
                # Leggi i valori attuali
                pots = self.arduino_reader.get_values()
                
                # Verifica se i valori sono cambiati significativamente
                values_changed = False
                
                # Controlla i potenziometri
                if pots:
                    for key, value in pots.items():
                        # Usa una soglia più bassa per pot3 (genere) e pot4 (pattern)
                        threshold = GENRE_PATTERN_THRESHOLD if key in ('pot3', 'pot4') else CHANGE_THRESHOLD
                        
                        if (key not in prev_pots or 
                            abs(value - prev_pots.get(key, 0)) > threshold):
                            values_changed = True
                            break
                
                # Forza un aggiornamento ogni ~10 secondi anche se i valori non cambiano
                force_update_counter += 1
                if force_update_counter >= 200:  # 200 * 0.05s = 10s
                    values_changed = True
                    force_update_counter = 0
                    print("[INFO] Aggiornamento forzato periodico")
                
                # Aggiorna i moduli solo se i valori sono cambiati
                if values_changed:
                    self.music_engine.update(pots)
                    
                    # Aggiorna i valori precedenti
                    if pots:
                        prev_pots = pots.copy()
                    
                    # Debug quando i valori cambiano
                    print(f"[AGGIORNAMENTO] Potenziometri: {pots}")
                
                # Debug ogni ~30 secondi indipendentemente dai cambiamenti
                debug_counter += 1
                if debug_counter >= 600:  # 600 * 0.05s = 30s
                    print(f"[DEBUG] Potenziometri: {pots}")
                    debug_counter = 0
                
                time.sleep(0.05)  # 50ms di attesa
                
        except KeyboardInterrupt:
            self.logger.info("Interruzione richiesta dall'utente")
        finally:
            self.stop()

def main():
    """Funzione principale"""
    # Verifica se lo script è eseguito con privilegi root
    if os.geteuid() != 0:
        print("ERRORE: Questo script deve essere eseguito con privilegi root (sudo)")
        print("Uso: sudo python3 carretto_supercollider.py")
        sys.exit(1)
    
    # Stampa intestazione
    print("\n===== CARRETTO MUSICALE - COMPATIBILE CON SUPERCOLLIDER =====")
    print(f"Data: 2025-06-15 18:49:48, Utente: {os.getlogin()}")
    print("===========================================================\n")
    
    # Mostra informazioni di sistema
    print(f"Current Date and Time (UTC): {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    
    carretto = CarrettoSystem()
    
    try:
        # Inizializza e avvia il sistema
        carretto.initialize()
        carretto.run()
    
    except Exception as e:
        print(f"Errore critico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Assicurati di eseguire la pulizia
        if carretto:
            carretto.stop()

if __name__ == "__main__":
    main()
