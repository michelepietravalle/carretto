#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CARRETTO MUSICALE - MUSIC ENGINE (VERSIONE CORRETTA)
Autore: Michele Pietravalle
Data: 2025-06-15
Versione: 2.9

Questo modulo gestisce la comunicazione con SuperCollider via OSC.
Versione corretta per gestire i messaggi OSC appropriatamente.
"""

import threading
import time
from pythonosc import udp_client
import socket

class MusicEngine:
    def __init__(self, host="127.0.0.1", port=57120):
        """Inizializza il motore musicale"""
        self.host = host
        self.port = 57120  # Forza la porta a 57120
        
        print(f"[MUSIC] Inizializzando client OSC su {host}:{self.port}")
        self.client = udp_client.SimpleUDPClient(host, self.port)
        
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
        
        # Valori precedenti per il confronto
        self.prev_values = {}
        
        # Valori precedenti dei potenziometri
        self.prev_pots = {}
    
    def start(self):
        """Avvia il thread di aggiornamento"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._update_thread)
            self.thread.daemon = True
            self.thread.start()
            
            print("[MUSIC] Thread di aggiornamento avviato")
            
            # Test di connessione iniziale
            try:
                # Invia un intero come richiesto dal protocollo OSC
                self.client.send_message("/test", 1)
                print("[MUSIC] Test di connessione inviato")
            except Exception as e:
                print(f"[MUSIC] Errore test connessione: {e}")
    
    def stop(self):
        """Ferma il thread di aggiornamento"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        print("[MUSIC] Thread di aggiornamento arrestato")
    
    def update(self, pots, gps):
        """
        Aggiorna i valori correnti in base ai potenziometri e al GPS
        Versione corretta con i tipi appropriati
        """
        # Rileva se qualche potenziometro è cambiato
        pots_changed = False
        for key, value in pots.items():
            if key not in self.prev_pots or abs(value - self.prev_pots[key]) > 0.02:
                pots_changed = True
                print(f"[MUSIC] Potenziometro {key} cambiato: {value:.2f} (era: {self.prev_pots.get(key, 0):.2f})")
        
        # Se nessun potenziometro è cambiato, non fare nulla
        if not pots_changed:
            return
        
        # Aggiorna i valori precedenti dei potenziometri
        self.prev_pots = pots.copy()
        
        # VOLUME (pot1)
        if 'pot1' in pots:
            volume = pots['pot1']
            self.current_values["volume"] = volume
            print(f"[MUSIC] Volume aggiornato a {volume:.2f}")
            
            # Invia immediatamente il comando volume come float
            try:
                self.client.send_message("/carretto/volume", float(volume))
                print(f"[MUSIC] Comando volume inviato: {volume:.2f}")
            except Exception as e:
                print(f"[MUSIC] Errore invio volume: {e}")
        
        # BPM (pot2)
        if 'pot2' in pots:
            # Mappa 0-1 a 60-180 BPM
            bpm = 60 + (pots['pot2'] * 120)
            self.current_values["bpm"] = bpm
            print(f"[MUSIC] BPM aggiornato a {bpm:.1f}")
            
            # Invia immediatamente il comando BPM come float
            try:
                self.client.send_message("/carretto/bpm", float(bpm))
                print(f"[MUSIC] Comando BPM inviato: {bpm:.1f}")
            except Exception as e:
                print(f"[MUSIC] Errore invio BPM: {e}")
        
        # GENRE (pot3)
        if 'pot3' in pots:
            # Mappa 0-1 a 7 generi
            genre_idx = int(pots['pot3'] * 6.99)
            genres = ["dub", "techno", "reggae", "house", "drumandbass", "ambient", "random"]
            new_pattern = genres[genre_idx]
            
            # Se il genere è cambiato, aggiorna
            if new_pattern != self.current_values["pattern"]:
                self.current_values["pattern"] = new_pattern
                print(f"[MUSIC] Genere aggiornato a {new_pattern}")
                
                # Invia immediatamente il comando genere come stringa
                try:
                    self.client.send_message("/carretto/pattern", new_pattern)
                    print(f"[MUSIC] Comando pattern inviato: {new_pattern}")
                except Exception as e:
                    print(f"[MUSIC] Errore invio pattern: {e}")
        
        # PATTERN INDEX (pot4)
        if 'pot4' in pots:
            # Mappa 0-1 a 0-3 pattern index
            pattern_idx = int(pots['pot4'] * 3.99)
            
            # Se il pattern index è cambiato, aggiorna
            if pattern_idx != self.current_values["patternIdx"]:
                self.current_values["patternIdx"] = pattern_idx
                print(f"[MUSIC] Pattern index aggiornato a {pattern_idx}")
                
                # Invia immediatamente il comando pattern index come intero
                try:
                    self.client.send_message("/carretto/patternIdx", int(pattern_idx))
                    print(f"[MUSIC] Comando patternIdx inviato: {pattern_idx}")
                except Exception as e:
                    print(f"[MUSIC] Errore invio patternIdx: {e}")
        
        # GPS
        if 'speed' in gps and gps['speed'] is not None:
            self.current_values["speed"] = gps['speed']
    
    def _update_thread(self):
        """Thread che invia ping periodici e test"""
        last_test_time = time.time()
        
        while self.running:
            current_time = time.time()
            
            # Invia un ping ogni 5 secondi
            if current_time - last_test_time > 5.0:
                try:
                    # Invia un intero come richiesto dal protocollo OSC
                    self.client.send_message("/test", 1)
                    print("[MUSIC] Test periodico inviato")
                    last_test_time = current_time
                except Exception as e:
                    print(f"[MUSIC] Errore invio test: {e}")
            
            # Pausa breve
            time.sleep(0.1)

# Test diretto
if __name__ == "__main__":
    music = MusicEngine()
    music.start()
    
    try:
        # Simulazione cambio potenziometri
        print("\nSimulazione cambio potenziometri:")
        
        # Volume (pot1)
        pots = {'pot1': 0.3, 'pot2': 0.5, 'pot3': 0.0, 'pot4': 0.0}
        music.update(pots, {})
        print("Volume impostato a 0.3")
        time.sleep(2)
        
        # Volume alto
        pots = {'pot1': 1.0, 'pot2': 0.5, 'pot3': 0.0, 'pot4': 0.0}
        music.update(pots, {})
        print("Volume impostato a 1.0")
        time.sleep(2)
        
        # BPM lento
        pots = {'pot1': 1.0, 'pot2': 0.0, 'pot3': 0.0, 'pot4': 0.0}
        music.update(pots, {})
        print("BPM impostato a 60")
        time.sleep(3)
        
        # BPM veloce
        pots = {'pot1': 1.0, 'pot2': 1.0, 'pot3': 0.0, 'pot4': 0.0}
        music.update(pots, {})
        print("BPM impostato a 180")
        time.sleep(3)
        
        # Genere techno
        pots = {'pot1': 1.0, 'pot2': 0.5, 'pot3': 0.2, 'pot4': 0.0}
        music.update(pots, {})
        print("Genere impostato a techno")
        time.sleep(3)
        
        # Pattern index 2
        pots = {'pot1': 1.0, 'pot2': 0.5, 'pot3': 0.2, 'pot4': 0.5}
        music.update(pots, {})
        print("Pattern index impostato a 2")
        time.sleep(3)
        
        print("Test completato")
    except KeyboardInterrupt:
        print("Test interrotto")
    finally:
        music.stop()
