#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CARRETTO MUSICALE - MUSIC ENGINE
Autore: Michele Pietravalle
Data: 2025-06-15
Versione: 2.6

Questo modulo gestisce la comunicazione con SuperCollider via OSC.
"""

import threading
import time
import subprocess
import os
from pythonosc import udp_client
import socket

class MusicEngine:
    def __init__(self, host="127.0.0.1", port=57120):  # Porta confermata 57120
        """
        Inizializza il motore musicale
        
        Args:
            host: IP del server SuperCollider
            port: Porta OSC di SuperCollider (57120 è la porta confermata)
        """
        self.host = host
        # Forza la porta a 57120 indipendentemente dal parametro passato
        self.port = 57120
            
        # Inizializza il client OSC
        self.client = udp_client.SimpleUDPClient(host, self.port)
        self.running = False
        self.thread = None
        self.current_values = {
            "volume": 0.8,
            "bpm": 120,
            "tune": 0.5,
            "pattern": "dub",
            "patternIdx": 0,
            "speed": 0
        }
        self.prev_values = self.current_values.copy()
        
        # Print di debug per la porta
        print(f"[MUSIC] Inizializzato client OSC su {host}:{self.port}")
        
    def start(self):
        """Avvia il thread di aggiornamento"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._update_thread)
            self.thread.daemon = True
            self.thread.start()
            print("[MUSIC] Thread di aggiornamento avviato.")
            
            # Invia un messaggio di test diretto per verificare la connessione
            try:
                # Test diretto: invia un messaggio che produce un suono
                self.client.send_message("/test", 1.0)
                print("[MUSIC] Test OSC diretto inviato.")
                
                # Test carretto: invia un messaggio tramite il protocollo carretto
                self.client.send_message("/carretto/test", 1.0)
                print("[MUSIC] Test OSC carretto inviato.")
            except Exception as e:
                print(f"[MUSIC] Errore invio test OSC: {e}")
    
    def stop(self):
        """Ferma il thread di aggiornamento"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            print("[MUSIC] Thread di aggiornamento arrestato.")
    
    def update(self, pots, gps):
        """
        Aggiorna i valori correnti in base ai potenziometri e al GPS
        
        Args:
            pots: Dizionario con i valori dei potenziometri
            gps: Dizionario con i dati GPS
        """
        # Aggiorna i valori in base ai potenziometri
        if 'pot1' in pots:
            # Volume (mappato direttamente)
            self.current_values["volume"] = pots['pot1']
            
        if 'pot2' in pots:
            # BPM (mappato da 0-1 a 60-180)
            self.current_values["bpm"] = 60 + (pots['pot2'] * 120)
            
        if 'pot3' in pots:
            # Tune (mappato direttamente)
            self.current_values["tune"] = pots['pot3']
            
            # Usa pot3 anche per selezionare il genere
            # Dividi l'intervallo 0-1 in 7 fasce per i 7 generi
            genre_idx = int(pots['pot3'] * 6.99)
            genres = ["dub", "techno", "reggae", "house", "drumandbass", "ambient", "random"]
            self.current_values["pattern"] = genres[genre_idx]
            
        if 'pot4' in pots:
            # Pattern index (mappato da 0-1 a 0-3)
            pattern_idx = int(pots['pot4'] * 3.99)
            self.current_values["patternIdx"] = pattern_idx
        
        # Aggiorna la velocità in base al GPS se disponibile
        if 'speed' in gps and gps['speed'] is not None:
            self.current_values["speed"] = gps['speed']
    
    def _update_thread(self):
        """Thread che invia messaggi OSC a SuperCollider quando i valori cambiano"""
        last_force_update = time.time()
        
        while self.running:
            force_update = False
            current_time = time.time()
            
            # Forza un aggiornamento completo ogni 2 secondi
            if current_time - last_force_update > 2.0:
                force_update = True
                last_force_update = current_time
                print("[MUSIC] Forza aggiornamento completo OSC...")
            
            # Confronta i valori attuali con quelli precedenti
            for key, value in self.current_values.items():
                if key == "pattern":
                    # Per il pattern (genere), invia come stringa
                    if str(self.prev_values.get(key, "")) != str(value) or force_update:
                        osc_address = f"/carretto/{key}"
                        try:
                            # Invia come stringa
                            self.client.send_message(osc_address, str(value))
                            print(f"[MUSIC] OSC sent: {osc_address} = {value} (string)")
                            self.prev_values[key] = value
                        except Exception as e:
                            print(f"[MUSIC] Errore invio OSC {osc_address}: {e}")
                
                elif key == "patternIdx":
                    # Per l'indice del pattern, invia come intero
                    if int(self.prev_values.get(key, -1)) != int(value) or force_update:
                        osc_address = f"/carretto/{key}"
                        try:
                            # Invia come intero
                            self.client.send_message(osc_address, int(value))
                            print(f"[MUSIC] OSC sent: {osc_address} = {value} (int)")
                            self.prev_values[key] = value
                        except Exception as e:
                            print(f"[MUSIC] Errore invio OSC {osc_address}: {e}")
                
                else:
                    # Per tutti gli altri valori numerici, invia come float
                    try:
                        if force_update or abs(float(self.prev_values.get(key, 0)) - float(value)) > 0.01:
                            osc_address = f"/carretto/{key}"
                            try:
                                # Invia come float
                                self.client.send_message(osc_address, float(value))
                                print(f"[MUSIC] OSC sent: {osc_address} = {value} (float)")
                                self.prev_values[key] = value
                            except Exception as e:
                                print(f"[MUSIC] Errore invio OSC {osc_address}: {e}")
                    except (TypeError, ValueError) as e:
                        print(f"[MUSIC] Errore conversione valore {key}={value}: {e}")
            
            # Invia un ping periodico per mantenere la connessione
            try:
                self.client.send_message("/carretto/ping", float(current_time))
            except Exception as e:
                print(f"[MUSIC] Errore invio ping: {e}")
            
            # Invia un test diretto periodico
            if force_update:
                try:
                    self.client.send_message("/test", 1.0)
                except Exception as e:
                    print(f"[MUSIC] Errore invio test diretto: {e}")
            
            # Pausa per non sovraccaricare la CPU
            time.sleep(0.1)

# Per test standalone
if __name__ == "__main__":
    music = MusicEngine()
    music.start()
    try:
        # Test con valori simulati
        for i in range(5):
            # Simula potenziometri
            pots = {
                'pot1': 0.8,         # Volume
                'pot2': 0.5,         # BPM
                'pot3': i / 4.0,     # Tune/Genre
                'pot4': i % 4 / 3.0  # Pattern
            }
            
            # Simula GPS
            gps = {'speed': i * 0.5}
            
            # Aggiorna i valori
            music.update(pots, gps)
            print(f"Test {i+1}: Valori aggiornati")
            
            # Attendi per vedere gli effetti
            time.sleep(2)
    except KeyboardInterrupt:
        music.stop()
