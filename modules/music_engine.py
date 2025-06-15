#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CARRETTO MUSICALE - MUSIC ENGINE (VERSIONE FIXED)
Autore: Michele Pietravalle
Data: 2025-06-15
Versione: 3.1

Modulo per il controllo di SuperCollider via OSC.
Questa versione include fix specifici per assicurare la corretta trasmissione dei comandi.
"""

import threading
import time
from pythonosc import udp_client
import socket

class MusicEngine:
    def __init__(self, host="127.0.0.1", port=57120):
        """Inizializza il motore musicale"""
        self.host = host
        self.port = port
        
        print(f"[MUSIC] Inizializzazione client OSC su {host}:{port}")
        self.client = udp_client.SimpleUDPClient(host, port)
        
        self.running = False
        self.thread = None
        
        # Valori correnti
        self.current_values = {
            "volume": 0.8,
            "bpm": 120,
            "tune": 0.5,
            "pattern": "dub",
            "patternIdx": 0,
            "speed": 0
        }
        
        # Valori precedenti per confronto
        self.prev_values = {}
        self.prev_pots = {}
        
        # Debug flag per verificare la comunicazione
        self.debug_mode = True
        
        # Test iniziale esplicito
        try:
            print("[MUSIC] Invio test iniziale esplicito...")
            self.client.send_message("/test", 1)
        except Exception as e:
            print(f"[MUSIC] Errore test iniziale: {e}")
    
    def start(self):
        """Avvia il thread di aggiornamento"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._update_thread)
            self.thread.daemon = True
            self.thread.start()
            
            print("[MUSIC] Thread di aggiornamento avviato")
            
            # Invia comandi iniziali espliciti
            try:
                # Sequenza iniziale per assicurarsi che tutto funzioni
                print("[MUSIC] Invio sequenza iniziale...")
                time.sleep(0.1)
                self.client.send_message("/test", 1)
                time.sleep(0.1)
                self.client.send_message("/carretto/volume", 0.8)
                time.sleep(0.1)
                self.client.send_message("/carretto/pattern", "dub")
                time.sleep(0.1)
                self.client.send_message("/carretto/patternIdx", 0)
                print("[MUSIC] Sequenza iniziale completata")
            except Exception as e:
                print(f"[MUSIC] Errore sequenza iniziale: {e}")
    
    def stop(self):
        """Ferma il thread di aggiornamento"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        print("[MUSIC] Thread di aggiornamento arrestato")
    
    def _send_osc_message(self, address, value):
        """Funzione helper per inviare messaggi OSC con gestione degli errori"""
        try:
            self.client.send_message(address, value)
            if self.debug_mode:
                print(f"[MUSIC] Inviato: {address} = {value}")
            return True
        except Exception as e:
            print(f"[MUSIC] Errore invio {address}: {e}")
            return False
    
    def update(self, pots, gps):
        """
        Aggiorna i valori correnti in base ai potenziometri e al GPS
        
        Args:
            pots: Dizionario con i valori dei potenziometri
            gps: Dizionario con i dati GPS
        """
        # IMPORTANTE: Invia sempre un comando di test per mantenere attiva la connessione
        self._send_osc_message("/test", 1)
        
        # Elabora tutti i potenziometri, anche se non sono cambiati significativamente
        # Questo assicura che i comandi vengano inviati anche se i potenziometri
        # non cambiano molto ma vengono comunque spostati
        
        # VOLUME (pot1)
        if 'pot1' in pots:
            volume = float(pots['pot1'])
            
            # Manda esplicitamente come float
            self._send_osc_message("/carretto/volume", volume)
            self.current_values["volume"] = volume
            
            # Forza un refresh del volume master
            self._send_osc_message("/carretto/volume", volume)
        
        # BPM (pot2)
        if 'pot2' in pots:
            # Mappa 0-1 a 60-180 BPM
            bpm = 60.0 + (float(pots['pot2']) * 120.0)
            
            # Manda esplicitamente come float
            self._send_osc_message("/carretto/bpm", bpm)
            self.current_values["bpm"] = bpm
        
        # GENRE (pot3)
        if 'pot3' in pots:
            pot3_value = float(pots['pot3'])
            
            # Mappa 0-1 a 7 generi, usando floor per evitare out of range
            genre_idx = min(int(pot3_value * 6.99), 6)
            genres = ["dub", "techno", "reggae", "house", "drumandbass", "ambient", "random"]
            new_pattern = genres[genre_idx]
            
            # Invia sempre il pattern, anche se non è cambiato
            self._send_osc_message("/carretto/pattern", new_pattern)
            self.current_values["pattern"] = new_pattern
            
            # Invia sempre tune
            self._send_osc_message("/carretto/tune", pot3_value)
            self.current_values["tune"] = pot3_value
        
        # PATTERN INDEX (pot4)
        if 'pot4' in pots:
            pot4_value = float(pots['pot4'])
            
            # Mappa 0-1 a 0-3 pattern index
            pattern_idx = min(int(pot4_value * 3.99), 3)
            
            # Invia sempre il pattern index, anche se non è cambiato
            self._send_osc_message("/carretto/patternIdx", pattern_idx)
            self.current_values["patternIdx"] = pattern_idx
        
        # Aggiorna i valori precedenti dei potenziometri
        self.prev_pots = pots.copy()
        
        # GPS - opzionale
        if 'speed' in gps and gps['speed'] is not None:
            speed = float(gps['speed'])
            self.current_values["speed"] = speed
            
            # Invia solo se è cambiata significativamente
            if abs(speed - self.prev_values.get("speed", 0)) > 0.5:
                self._send_osc_message("/carretto/speed", speed)
                self.prev_values["speed"] = speed
    
    def _update_thread(self):
        """Thread che invia ping periodici e test"""
        last_ping_time = time.time()
        last_test_time = time.time()
        
        while self.running:
            current_time = time.time()
            
            # Invia ping ogni 3 secondi
            if current_time - last_ping_time > 3.0:
                self._send_osc_message("/carretto/ping", int(current_time))
                last_ping_time = current_time
            
            # Invia test ogni 1 secondo per mantenere attiva la connessione
            if current_time - last_test_time > 1.0:
                self._send_osc_message("/test", 1)
                last_test_time = current_time
            
            # Pausa breve
            time.sleep(0.1)

# Per test standalone
if __name__ == "__main__":
    music = MusicEngine()
    music.start()
    
    try:
        print("\nTest dei controlli musicali:")
        
        # Test volume
        print("\nTest volume (0.3 -> 1.0)...")
        music.client.send_message("/carretto/volume", 0.3)
        time.sleep(2)
        music.client.send_message("/carretto/volume", 1.0)
        time.sleep(2)
        
        # Test generi
        for genre in ["dub", "techno", "reggae", "house", "drumandbass", "ambient"]:
            print(f"\nTest genere {genre}...")
            music.client.send_message("/carretto/pattern", genre)
            time.sleep(3)
            
            # Test pattern per ogni genere
            for idx in range(4):
                print(f"  Pattern {idx}...")
                music.client.send_message("/carretto/patternIdx", idx)
                time.sleep(2)
        
        print("\nTest completato!")
    except KeyboardInterrupt:
        print("\nTest interrotto")
    finally:
        music.stop()
