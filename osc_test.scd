/*
* TEST OSC SUPERCOLLIDER - VERSIONE CORRETTA
* Questo file è progettato per testare solo la ricezione OSC
*/

(
// ===== CONFIGURAZIONE AUDIO ESPLICITA =====
s = Server.default;
s.options.numOutputBusChannels = 2;
s.options.numInputBusChannels = 0;
s.options.sampleRate = 48000;  // Adattato alla tua configurazione
s.options.memSize = 8192;

// ===== PORTA OSC ESPLICITA =====
// Imposta l'indirizzo di binding per ascoltare su tutti gli indirizzi
s.options.bindAddress = "0.0.0.0";
s.options.maxLogins = 8;

// ===== DEBUG DETTAGLIATO =====
// Funzione per stampare messaggi di debug
~debug = { |msg|
    (">> " ++ msg).postln;
};

// Stampa informazioni sulle porte
~debug.value("Avvio SuperCollider - configurazione porte...");
~debug.value("Porta linguaggio attuale: " ++ NetAddr.langPort);

// Avvia il server
~debug.value("Avvio del server audio...");

s.waitForBoot({
    ~debug.value("Server audio avviato e pronto!");
    
    // Imposta il volume master al massimo
    s.volume = 1.0;

    // ===== DEFINIZIONE SYNTH SEMPLICI =====
    // Synth di test - un semplice beep
    SynthDef(\testBeep, {|freq=440, amp=0.5, dur=0.5|
        var env = EnvGen.ar(Env.perc(0.01, dur), doneAction: 2);
        var snd = SinOsc.ar(freq) * env * amp;
        Out.ar(0, snd!2);
    }).add;
    
    // Kick semplice
    SynthDef(\kick, {|amp=0.8, freq=60, dur=0.6|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = SinOsc.ar(freq) * env * amp;
        Out.ar(0, snd!2);
    }).add;
    
    // Snare semplice
    SynthDef(\snare, {|amp=0.8, freq=120, dur=0.3|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = (SinOsc.ar(freq) * 0.3 + WhiteNoise.ar() * 0.7) * env * amp;
        Out.ar(0, snd!2);
    }).add;

    // Attendi che i synth siano definiti
    s.sync;
    
    ~debug.value("Synths definiti e pronti!");

    // ===== RICEZIONE OSC SEMPLIFICATA =====
    
    // Ricevi qualsiasi messaggio OSC e stampa info
    OSCdef(\allMessages, {|msg, time, addr, recvPort|
        ~debug.value("OSC ricevuto: " ++ msg);
        
        // Esegui un beep per confermare la ricezione
        Synth(\testBeep, [\freq, 660, \amp, 0.3]);
    }, nil, nil, nil).permanent_(true);
    
    // Definizione specifica per ogni comando
    OSCdef(\testCmd, {|msg, time, addr, recvPort|
        ~debug.value("Test comando OSC ricevuto!");
        Synth(\kick, [\amp, 1.0]);
    }, '/test', nil, nil).permanent_(true);
    
    OSCdef(\volumeCmd, {|msg, time, addr, recvPort|
        var vol = msg[1].asFloat;
        ~debug.value("Volume comando ricevuto: " ++ vol);
        s.volume = vol * 2 - 1; // -1 a +1 dB
        Synth(\testBeep, [\freq, 440 + (vol * 440), \amp, 0.5]);
    }, '/carretto/volume', nil, nil).permanent_(true);
    
    OSCdef(\patternCmd, {|msg, time, addr, recvPort|
        var pat = msg[1].asString;
        ~debug.value("Pattern comando ricevuto: " ++ pat);
        
        if(pat == "dub") {
            Synth(\kick, [\amp, 1.0, \freq, 60]);
        } {
            Synth(\snare, [\amp, 1.0, \freq, 120]);
        };
    }, '/carretto/pattern', nil, nil).permanent_(true);
    
    OSCdef(\patternIdxCmd, {|msg, time, addr, recvPort|
        var idx = msg[1].asInteger;
        ~debug.value("PatternIdx comando ricevuto: " ++ idx);
        
        Synth(\testBeep, [\freq, 440 + (idx * 100), \amp, 0.5]);
    }, '/carretto/patternIdx', nil, nil).permanent_(true);
    
    OSCdef(\bpmCmd, {|msg, time, addr, recvPort|
        var bpm = msg[1].asFloat;
        ~debug.value("BPM comando ricevuto: " ++ bpm);
        
        Synth(\testBeep, [\freq, 300 + (bpm/2), \amp, 0.5]);
    }, '/carretto/bpm', nil, nil).permanent_(true);

    // ===== TEST INIZIALE =====
    // Suoni di test all'avvio
    fork {
        ~debug.value("Riproduzione suoni di test...");
        Synth(\testBeep, [\freq, 440, \amp, 0.5]); 0.5.wait;
        Synth(\kick, [\amp, 0.8]); 0.5.wait;
        Synth(\snare, [\amp, 0.8]); 0.5.wait;
        ~debug.value("Test audio completato!");
    };

    ~debug.value("TEST OSC READY!");
    ~debug.value("Invia messaggi a /test o /carretto/* sulla porta: " ++ NetAddr.langPort);
    
    // Print system status
    ~debug.value("INFORMAZIONI DI SISTEMA:");
    ~debug.value("Language Port: " ++ NetAddr.langPort);
    ~debug.value("Server Port: " ++ s.addr.port);
    ~debug.value("Local Address: " ++ NetAddr.localAddr);
    
    // Riproduci un suono ogni 10 secondi
    fork {
        ~debug.value("Avvio suoni di test periodici");
        loop {
            Synth(\testBeep, [\freq, 880, \amp, 0.3]);
            10.wait;
        }
    };
});
)
