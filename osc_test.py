#!/usr/bin/env python3
"""
Test OSC con formattazione corretta
"""

import socket
import struct
import time
from pythonosc import udp_client
from pythonosc import osc_message_builder
from pythonosc import osc_bundle_builder

def main():
    host = "127.0.0.1"
    port = 57120  # La porta SuperCollider
    
    print("=== TEST OSC CORRETTO ===")
    print(f"Invio di messaggi OSC a {host}:{port}")
    
    # Crea il client OSC utilizzando pythonosc
    client = udp_client.SimpleUDPClient(host, port)
    
    # Test 1: Comando semplice
    print("\n=== TEST 1: COMANDO SEMPLICE ===")
    client.send_message("/test", 1)
    print("Inviato: /test 1")
    time.sleep(1)
    
    # Test 2: Volume
    print("\n=== TEST 2: VOLUME ===")
    client.send_message("/carretto/volume", 0.8)
    print("Inviato: /carretto/volume 0.8")
    time.sleep(2)
    
    # Test 3: Pattern
    print("\n=== TEST 3: PATTERN ===")
    client.send_message("/carretto/pattern", "dub")
    print("Inviato: /carretto/pattern \"dub\"")
    time.sleep(2)
    
    client.send_message("/carretto/pattern", "techno")
    print("Inviato: /carretto/pattern \"techno\"")
    time.sleep(2)
    
    # Test 4: Pattern Index
    print("\n=== TEST 4: PATTERN INDEX ===")
    client.send_message("/carretto/patternIdx", 2)
    print("Inviato: /carretto/patternIdx 2")
    time.sleep(2)
    
    # Test 5: BPM
    print("\n=== TEST 5: BPM ===")
    client.send_message("/carretto/bpm", 140.0)
    print("Inviato: /carretto/bpm 140.0")
    time.sleep(2)
    
    print("\nTest completato!")

if __name__ == "__main__":
    main()
