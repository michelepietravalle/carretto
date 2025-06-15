/*
* CARRETTO MUSICALE - SISTEMA COMPLETO (PORTA 57120)
* Autore: Michele Pietravalle
* Data: 2025-06-15
* Versione: 2.6
*
* Ottimizzato per Raspberry Pi 4
*/

(
// ===== CONFIGURAZIONE AUDIO ESPLICITA =====
s = Server.default;
s.options.numOutputBusChannels = 2;
s.options.numInputBusChannels = 0;
s.options.sampleRate = 44100;
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
~debug.value("I comandi '/carretto/*' devono essere inviati alla porta: " ++ NetAddr.langPort);

// Avvia il server
~debug.value("Avvio del server audio...");

s.waitForBoot({
    ~debug.value("Server audio avviato e pronto!");
    
    // Imposta il volume master al massimo
    s.volume = 1.0;

    // ===== PARAMETRI INIZIALI =====
    ~genres = ["dub", "techno", "reggae", "house", "drumandbass", "ambient", "random"];
    ~params = (
        dub: (volume: 0.8, bpm: 120, tone: 0),
        techno: (volume: 0.8, bpm: 128, tone: 0),
        reggae: (volume: 0.8, bpm: 80, tone: 0),
        house: (volume: 0.8, bpm: 124, tone: 0),
        drumandbass: (volume: 0.8, bpm: 172, tone: 0),
        ambient: (volume: 0.8, bpm: 60, tone: 0),
        random: (volume: 0.8, bpm: 110, tone: 0)
    );

    ~currentPattern = "dub";
    ~currentPatternIdx = 0;
    ~activePlayers = (); // Tiene traccia dei player attivi

    // ===== DEFINIZIONE SYNTH =====
    // Kick - aumentato volume
    SynthDef(\dubKick, {|out=0, amp=0.8, freq=60, dur=0.6|
        var env, snd;
        env = EnvGen.ar(Env.perc(0.001, dur, 1, -8), doneAction: 2);
        snd = SinOsc.ar(freq * EnvGen.ar(Env([3, 1], [0.03])));
        snd = snd * env * amp;
        Out.ar(out, snd!2);
    }).add;

    // Snare - esplicitamente con volume alto
    SynthDef(\dubSnare, {|out=0, amp=0.9, freq=120, dur=0.3|
        var env, snd, noise;
        env = EnvGen.ar(Env.perc(0.001, dur, 1, -8), doneAction: 2);
        snd = SinOsc.ar(freq);
        noise = WhiteNoise.ar();
        snd = (snd * 0.3 + noise * 0.7) * env * amp;
        Out.ar(out, snd!2);
    }).add;

    // Hi-hat - aumentato volume
    SynthDef(\dubHat, {|out=0, amp=0.7, freq=8000, dur=0.1|
        var env, snd;
        env = EnvGen.ar(Env.perc(0.001, dur, 1, -8), doneAction: 2);
        snd = HPF.ar(WhiteNoise.ar(), freq);
        snd = snd * env * amp;
        Out.ar(out, snd!2);
    }).add;

    // Bass - aumentato volume
    SynthDef(\dubBass, {|out=0, amp=0.9, freq=60, dur=0.5|
        var env, snd;
        env = EnvGen.ar(Env.perc(0.001, dur, 1, -4), doneAction: 2);
        snd = SinOsc.ar(freq);
        snd = LPF.ar(snd, 800);
        snd = snd * env * amp;
        Out.ar(out, snd!2);
    }).add;

    // Percussioni - aumentato volume
    SynthDef(\dubPerc, {|out=0, amp=0.8, freq=300, dur=0.2|
        var env, snd;
        env = EnvGen.ar(Env.perc(0.001, dur, 1, -8), doneAction: 2);
        snd = SinOsc.ar(freq);
        snd = snd * env * amp;
        Out.ar(out, snd!2);
    }).add;

    // Synth per Techno
    SynthDef(\techKick, {|out=0, amp=0.9, freq=60, dur=0.5|
        var env, snd;
        env = EnvGen.ar(Env.perc(0.001, dur, 1, -8), doneAction: 2);
        snd = SinOsc.ar(freq * EnvGen.ar(Env([5, 1], [0.02])));
        snd = snd * env * amp;
        Out.ar(out, snd!2);
    }).add;

    SynthDef(\techHat, {|out=0, amp=0.7, freq=9000, dur=0.05|
        var env, snd;
        env = EnvGen.ar(Env.perc(0.001, dur, 1, -8), doneAction: 2);
        snd = HPF.ar(WhiteNoise.ar(), freq);
        snd = snd * env * amp;
        Out.ar(out, snd!2);
    }).add;

    SynthDef(\techSnare, {|out=0, amp=0.9, freq=180, dur=0.2|
        var env, snd, noise;
        env = EnvGen.ar(Env.perc(0.001, dur, 1, -4), doneAction: 2);
        snd = SinOsc.ar(freq);
        noise = WhiteNoise.ar();
        snd = (snd * 0.2 + noise * 0.8) * env * amp;
        Out.ar(out, snd!2);
    }).add;

    SynthDef(\techBass, {|out=0, amp=0.9, freq=60, dur=0.3, cutoff=1200|
        var env, snd;
        env = EnvGen.ar(Env.perc(0.001, dur, 1, -4), doneAction: 2);
        snd = Saw.ar(freq);
        snd = LPF.ar(snd, cutoff);
        snd = snd * env * amp;
        Out.ar(out, snd!2);
    }).add;

    // TEST ESPLICITO - Riproduci ogni suono all'avvio
    fork {
        ~debug.value("TEST AUDIO INIZIALE - riproducendo campioni...");
        Synth(\dubKick, [\amp, 1.0]); 0.5.wait;
        Synth(\dubSnare, [\amp, 1.0]); 0.5.wait;
        Synth(\dubHat, [\amp, 1.0]); 0.5.wait;
        Synth(\dubBass, [\freq, 60, \amp, 1.0]); 0.5.wait;
        Synth(\dubPerc, [\amp, 1.0]); 0.5.wait;
        ~debug.value("TEST AUDIO COMPLETATO!");
    };

    // ===== DEFINIZIONE DEI PATTERN DIRETTAMENTE =====
    
    // --- PATTERN DUB ---
    ~dub_patterns = Array.new;

    // Pattern 0 - Kick semplice
    ~dub_patterns = ~dub_patterns.add(
        Pbind(
            \instrument, \dubKick,
            \dur, Pseq([1, 1, 1, 1], inf),
            \amp, 0.9,
            \freq, 60
        )
    );

    // Pattern 1 - Kick + snare
    ~dub_patterns = ~dub_patterns.add(
        Ppar([
            Pbind(
                \instrument, \dubKick,
                \dur, Pseq([1, 1, 1, 1], inf),
                \amp, 0.9,
                \freq, 60
            ),
            Pbind(
                \instrument, \dubSnare,
                \dur, Pseq([2, 2], inf),
                \amp, 0.8,
                \freq, 120
            )
        ])
    );

    // Pattern 2 - Kick + snare + hat
    ~dub_patterns = ~dub_patterns.add(
        Ppar([
            Pbind(
                \instrument, \dubKick,
                \dur, Pseq([1, 1, 1, 1], inf),
                \amp, 0.9,
                \freq, 60
            ),
            Pbind(
                \instrument, \dubSnare,
                \dur, Pseq([2, 2], inf),
                \amp, 0.8,
                \freq, 120
            ),
            Pbind(
                \instrument, \dubHat,
                \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                \amp, 0.6,
                \freq, 8000
            )
        ])
    );

    // Pattern 3 - Dub completo
    ~dub_patterns = ~dub_patterns.add(
        Ppar([
            Pbind(
                \instrument, \dubKick,
                \dur, Pseq([1, 1, 1, 1], inf),
                \amp, 0.9,
                \freq, 60
            ),
            Pbind(
                \instrument, \dubSnare,
                \dur, Pseq([2, 2], inf),
                \amp, 0.8,
                \freq, 120
            ),
            Pbind(
                \instrument, \dubHat,
                \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                \amp, 0.6,
                \freq, 8000
            ),
            Pbind(
                \instrument, \dubBass,
                \dur, Pseq([0.5, 0.25, 0.25, 0.5, 0.5], inf),
                \amp, 0.8,
                \freq, Pseq([60, 80, 60, 40, 60], inf)
            )
        ])
    );

    ~debug.value("DUB patterns definiti: %".format(~dub_patterns.size));

    // --- PATTERN TECHNO ---
    ~techno_patterns = Array.new;

    // Pattern 0 - Kick semplice
    ~techno_patterns = ~techno_patterns.add(
        Pbind(
            \instrument, \techKick,
            \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
            \amp, 0.9,
            \freq, 60
        )
    );

    // Pattern 1 - Kick + hat
    ~techno_patterns = ~techno_patterns.add(
        Ppar([
            Pbind(
                \instrument, \techKick,
                \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                \amp, 0.9,
                \freq, 60
            ),
            Pbind(
                \instrument, \techHat,
                \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf),
                \amp, 0.7,
                \freq, 9000
            )
        ])
    );

    // Pattern 2 - Kick + hat + snare
    ~techno_patterns = ~techno_patterns.add(
        Ppar([
            Pbind(
                \instrument, \techKick,
                \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                \amp, 0.9,
                \freq, 60
            ),
            Pbind(
                \instrument, \techHat,
                \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf),
                \amp, 0.7,
                \freq, 9000
            ),
            Pbind(
                \instrument, \techSnare,
                \dur, Pseq([1, 1], inf),
                \amp, 0.8,
                \freq, 180
            )
        ])
    );

    // Pattern 3 - Techno completo
    ~techno_patterns = ~techno_patterns.add(
        Ppar([
            Pbind(
                \instrument, \techKick,
                \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                \amp, 0.9,
                \freq, 60
            ),
            Pbind(
                \instrument, \techHat,
                \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf),
                \amp, 0.7,
                \freq, 9000
            ),
            Pbind(
                \instrument, \techSnare,
                \dur, Pseq([1, 1], inf),
                \amp, 0.8,
                \freq, 180
            ),
            Pbind(
                \instrument, \techBass,
                \dur, Pseq([0.25, 0.25, 0.25, 0.25, 0.5, 0.5], inf),
                \amp, 0.8,
                \freq, Pseq([60, 80, 100, 80, 60, 40], inf),
                \cutoff, 1800
            )
        ])
    );

    ~debug.value("TECHNO patterns definiti: %".format(~techno_patterns.size));
    
    // ===== PLAYER PER OGNI GENERE =====
    ~players = ();
    
    // Definisci i player per ogni genere disponibile
    ~players.put(\dub, { |pat=0|
        // Stoppa eventuali altri player attivi
        ~activePlayers.do { |player| if(player.notNil, { player.stop; }); };
        ~activePlayers = ();
        
        // Crea e avvia il nuovo player
        ~activePlayers[\dub] = ~dub_patterns[pat].play(
            TempoClock.new((~params[\dub][\bpm] ?? 120)/60)
        );
        ~debug.value("[CARRETTO] DUB pattern % avviato!".format(pat));
    });
    
    ~players.put(\techno, { |pat=0|
        // Stoppa eventuali altri player attivi
        ~activePlayers.do { |player| if(player.notNil, { player.stop; }); };
        ~activePlayers = ();
        
        // Crea e avvia il nuovo player
        ~activePlayers[\techno] = ~techno_patterns[pat].play(
            TempoClock.new((~params[\techno][\bpm] ?? 128)/60)
        );
        ~debug.value("[CARRETTO] TECHNO pattern % avviato!".format(pat));
    });
    
    // Debug dei pattern caricati
    ~debug.value("Player disponibili: %".format(~players.keys));
    
    // ===== FUNZIONI DI UTILITÀ =====
    ~setPattern = { |genre, idx=0|
        if(~players[genre].notNil, {
            ~players[genre].value(idx);
            ~currentPattern = genre.asString;
            ~currentPatternIdx = idx;
            ~debug.value("[CARRETTO] Switch to % (pattern %)".format(genre, idx));
        }, {
            ~debug.value("[CARRETTO] Genere % non definito.".format(genre));
        });
    };

    ~setParam = { |genre, key, value|
        if(~params[genre].notNil, {
            ~params[genre][key] = value;
            ~debug.value("[CARRETTO] Set %/% = %".format(genre, key, value));
        });
    };

    // ===== TEST COMANDI OSC DIRETTI =====
    // Comando di test
    OSCdef(\testCmd, { |msg, time, addr, recvPort|
        ~debug.value("Test comando OSC ricevuto!");
        Synth(\dubKick, [\amp, 1.0]);
    }, '/test', nil, nil).permanent_(true);
    
    // ===== RICEZIONE OSC =====
    OSCdef(\carrettoOSC, { |msg, time, addr, port|
        var path = msg[0];
        var value = msg[1];
        
        // DEBUG DETTAGLIATO
        ~debug.value("[OSC] Ricevuto: % : % (tipo: %)".format(path, value, value.class));
        
        switch(path,
            '/carretto/volume', { 
                // Accetta numeri 0-1 o 0-255 e li normalizza
                var vol = value.asFloat;
                if(vol > 1.0, { vol = vol / 255.0 });
                ~setParam.(~currentPattern.asSymbol, \volume, vol);
                ~debug.value("[CARRETTO] Volume impostato a %".format(vol));
            },
            '/carretto/bpm', { 
                var bpm = value.asFloat;
                ~setParam.(~currentPattern.asSymbol, \bpm, bpm);
                // Restart pattern with new bpm
                ~setPattern.(~currentPattern.asSymbol, ~currentPatternIdx);
                ~debug.value("[CARRETTO] BPM impostato a %".format(bpm));
            },
            '/carretto/tune', { 
                var tone = value.asFloat;
                if(tone > 1.0, { tone = tone / 255.0 });
                ~setParam.(~currentPattern.asSymbol, \tone, tone);
                ~debug.value("[CARRETTO] Tune impostato a %".format(tone));
            },
            '/carretto/pattern', {
                var pattern_str = value.asString;
                var genres = ~genres;
                var idx = genres.indexOfEqual(pattern_str);
                if(idx.notNil, {
                    ~setPattern.(genres[idx].asSymbol, 0);
                    ~debug.value("[CARRETTO] Pattern cambiato a %".format(pattern_str));
                }, {
                    ~debug.value("[CARRETTO] Pattern non riconosciuto: %".format(pattern_str));
                });
            },
            '/carretto/patternIdx', {
                var idx = value.asInteger;
                var patternArray;
                
                // Determina quanti pattern ha il genere corrente
                switch(~currentPattern.asSymbol,
                    \dub, { patternArray = ~dub_patterns; },
                    \techno, { patternArray = ~techno_patterns; }
                    // Aggiungi altri generi quando saranno implementati
                );
                
                if(patternArray.notNil, {
                    idx = idx.clip(0, (patternArray.size - 1));
                    ~setPattern.(~currentPattern.asSymbol, idx);
                    ~debug.value("[CARRETTO] Pattern Index cambiato a %".format(idx));
                });
            },
            '/carretto/speed', { 
                ~debug.value("[CARRETTO] Speed: %".format(value));
            },
            '/carretto/ping', {
                // Ping di conferma connessione - risponde con pong
                addr.sendMsg('/carretto/pong', value);
                ~debug.value("[CARRETTO] Ping ricevuto");
            },
            '/carretto/test', {
                // Test message
                ~debug.value("[CARRETTO] Test message received: %".format(value));
                // Riproduci un suono di test
                Synth(\dubKick, [\amp, 1.0]);
            }
        );
    }, '/carretto', nil, nil).permanent_(true);

    ~debug.value("[CARRETTO] Sistema pronto! Invia comandi OSC alla porta: %".format(NetAddr.langPort));
    
    // Print system status
    ~debug.value("INFORMAZIONI DI SISTEMA:");
    ~debug.value("Language Port (per comandi OSC): %".format(NetAddr.langPort));
    ~debug.value("Local Address: %".format(NetAddr.localAddr));
    
    // Avvia il primo pattern
    fork {
        1.wait;
        ~debug.value("Avvio pattern dub...");
        ~setPattern.(\dub, 0);
    };
    
    // Riproduci un suono di test ogni 5 secondi
    fork {
        ~debug.value("Avvio suoni di test periodici");
        loop {
            Synth(\dubKick, [\amp, 0.7, \freq, 40]);
            5.wait;
        }
    };
});
)
