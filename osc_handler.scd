/*
* HANDLER OSC DIRETTO PER CARRETTO MUSICALE
* Questo file crea un gestore OSC indipendente che riproduce pattern musicali
* Eseguire come file stand-alone
*/

(
// ===== CONFIGURAZIONE AUDIO =====
s = Server.default;
s.options.numOutputBusChannels = 2;
s.options.numInputBusChannels = 0;
s.options.sampleRate = 48000;
s.options.memSize = 8192;

// ===== CONFIGURAZIONE OSC =====
// Ascolta su tutti gli indirizzi
s.options.bindAddress = "0.0.0.0";
s.options.maxLogins = 8;

// ===== DEBUG =====
~debug = { |msg|
    (">> " ++ msg).postln;
};

~debug.value("CARRETTO DIRECT HANDLER");
~debug.value("Porta linguaggio: " ++ NetAddr.langPort);
~debug.value("Avvio del server audio...");

s.waitForBoot({
    ~debug.value("Server audio avviato e pronto!");
    
    // Volume master al massimo
    s.volume = 1.0;

    // ===== VARIABILI GLOBALI =====
    ~currentGenre = \dub;
    ~currentPattern = 0;
    ~currentBPM = 120;
    ~currentVolume = 0.8;
    ~activePlayers = ();

    // ===== DEFINIZIONE SYNTH SEMPLICI =====
    // Kick
    SynthDef(\kick, {|amp=0.8, freq=60, dur=0.3|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = SinOsc.ar(freq * EnvGen.ar(Env([3, 1], [0.03])));
        snd = snd * env * amp;
        Out.ar(0, snd!2);
    }).add;
    
    // Snare
    SynthDef(\snare, {|amp=0.8, freq=120, dur=0.2|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = (SinOsc.ar(freq) * 0.3 + WhiteNoise.ar() * 0.7) * env * amp;
        Out.ar(0, snd!2);
    }).add;
    
    // Hi-hat
    SynthDef(\hat, {|amp=0.6, freq=8000, dur=0.1|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = HPF.ar(WhiteNoise.ar(), freq);
        snd = snd * env * amp;
        Out.ar(0, snd!2);
    }).add;
    
    // Bass
    SynthDef(\bass, {|amp=0.8, freq=60, dur=0.4|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = SinOsc.ar(freq);
        snd = LPF.ar(snd, 800);
        snd = snd * env * amp;
        Out.ar(0, snd!2);
    }).add;
    
    s.sync;  // Attendi che tutti i synth siano definiti
    ~debug.value("Synth definiti e pronti!");
    
    // ===== PATTERN SEMPLICI PER OGNI GENERE =====
    ~patternFunctions = ();
    
    // DUB
    ~patternFunctions.put(\dub, { |patIdx=0, bpm=120, volume=0.8|
        var clock = TempoClock.new(bpm/60);
        var pattern;
        
        switch(patIdx,
            0, { // Pattern base
                pattern = Pbind(
                    \instrument, \kick,
                    \dur, Pseq([1, 1, 1, 1], inf),
                    \amp, volume * 0.9,
                    \freq, 60
                );
            },
            1, { // Kick + snare
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([1, 1, 1, 1], inf),
                        \amp, volume * 0.9,
                        \freq, 60
                    ),
                    Pbind(
                        \instrument, \snare,
                        \dur, Pseq([2, 2], inf),
                        \amp, volume * 0.8,
                        \freq, 120
                    )
                ]);
            },
            2, { // Kick + snare + hat
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([1, 1, 1, 1], inf),
                        \amp, volume * 0.9,
                        \freq, 60
                    ),
                    Pbind(
                        \instrument, \snare,
                        \dur, Pseq([2, 2], inf),
                        \amp, volume * 0.8,
                        \freq, 120
                    ),
                    Pbind(
                        \instrument, \hat,
                        \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                        \amp, volume * 0.6,
                        \freq, 8000
                    )
                ]);
            },
            { // Pattern completo (default per 3 o altri valori)
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([1, 1, 1, 1], inf),
                        \amp, volume * 0.9,
                        \freq, 60
                    ),
                    Pbind(
                        \instrument, \snare,
                        \dur, Pseq([2, 2], inf),
                        \amp, volume * 0.8,
                        \freq, 120
                    ),
                    Pbind(
                        \instrument, \hat,
                        \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                        \amp, volume * 0.6,
                        \freq, 8000
                    ),
                    Pbind(
                        \instrument, \bass,
                        \dur, Pseq([0.5, 0.25, 0.25, 0.5, 0.5], inf),
                        \amp, volume * 0.8,
                        \freq, Pseq([60, 80, 60, 40, 60], inf)
                    )
                ]);
            }
        );
        
        ~debug.value("DUB pattern " ++ patIdx ++ " creato con BPM " ++ bpm ++ " e volume " ++ volume);
        
        // Restituisci il pattern con il clock
        pattern.play(clock);
    });
    
    // TECHNO
    ~patternFunctions.put(\techno, { |patIdx=0, bpm=128, volume=0.8|
        var clock = TempoClock.new(bpm/60);
        var pattern;
        
        switch(patIdx,
            0, { // Pattern base
                pattern = Pbind(
                    \instrument, \kick,
                    \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                    \amp, volume * 0.9,
                    \freq, 60
                );
            },
            1, { // Kick + hat
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                        \amp, volume * 0.9,
                        \freq, 60
                    ),
                    Pbind(
                        \instrument, \hat,
                        \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf),
                        \amp, volume * 0.7,
                        \freq, 9000
                    )
                ]);
            },
            2, { // Kick + hat + snare
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                        \amp, volume * 0.9,
                        \freq, 60
                    ),
                    Pbind(
                        \instrument, \hat,
                        \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf),
                        \amp, volume * 0.7,
                        \freq, 9000
                    ),
                    Pbind(
                        \instrument, \snare,
                        \dur, Pseq([1, 1], inf),
                        \amp, volume * 0.8,
                        \freq, 180
                    )
                ]);
            },
            { // Pattern completo (default per 3 o altri valori)
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                        \amp, volume * 0.9,
                        \freq, 60
                    ),
                    Pbind(
                        \instrument, \hat,
                        \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf),
                        \amp, volume * 0.7,
                        \freq, 9000
                    ),
                    Pbind(
                        \instrument, \snare,
                        \dur, Pseq([1, 1], inf),
                        \amp, volume * 0.8,
                        \freq, 180
                    ),
                    Pbind(
                        \instrument, \bass,
                        \dur, Pseq([0.25, 0.25, 0.25, 0.25, 0.5, 0.5], inf),
                        \amp, volume * 0.8,
                        \freq, Pseq([60, 80, 100, 80, 60, 40], inf)
                    )
                ]);
            }
        );
        
        ~debug.value("TECHNO pattern " ++ patIdx ++ " creato con BPM " ++ bpm ++ " e volume " ++ volume);
        
        // Restituisci il pattern con il clock
        pattern.play(clock);
    });
    
    // REGGAE
    ~patternFunctions.put(\reggae, { |patIdx=0, bpm=80, volume=0.8|
        var clock = TempoClock.new(bpm/60);
        var pattern;
        
        switch(patIdx,
            0, { // Pattern base
                pattern = Pbind(
                    \instrument, \kick,
                    \dur, Pseq([1, 1, 1, 1], inf),
                    \amp, volume * 0.9,
                    \freq, 60
                );
            },
            1, { // Kick + bass
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([1, 1, 1, 1], inf),
                        \amp, volume * 0.9,
                        \freq, 60
                    ),
                    Pbind(
                        \instrument, \bass,
                        \dur, Pseq([0.5, 0.5, 1, 1, 1], inf),
                        \amp, volume * 0.7,
                        \freq, Pseq([60, 50, 45, 50, 60], inf)
                    )
                ]);
            },
            2, { // Kick + bass + hat
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([1, 1, 1, 1], inf),
                        \amp, volume * 0.9,
                        \freq, 60
                    ),
                    Pbind(
                        \instrument, \bass,
                        \dur, Pseq([0.5, 0.5, 1, 1, 1], inf),
                        \amp, volume * 0.7,
                        \freq, Pseq([60, 50, 45, 50, 60], inf)
                    ),
                    Pbind(
                        \instrument, \hat,
                        \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                        \amp, volume * 0.5,
                        \freq, 8000
                    )
                ]);
            },
            { // Pattern completo (default per 3 o altri valori)
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([1, 1, 1, 1], inf),
                        \amp, volume * 0.9,
                        \freq, 60
                    ),
                    Pbind(
                        \instrument, \bass,
                        \dur, Pseq([0.5, 0.5, 1, 1, 1], inf),
                        \amp, volume * 0.7,
                        \freq, Pseq([60, 50, 45, 50, 60], inf)
                    ),
                    Pbind(
                        \instrument, \hat,
                        \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                        \amp, volume * 0.5,
                        \freq, 8000
                    ),
                    Pbind(
                        \instrument, \snare,
                        \dur, Pseq([2, 2], inf),
                        \amp, Pseq([0, volume * 0.8], inf),
                        \freq, 120
                    )
                ]);
            }
        );
        
        ~debug.value("REGGAE pattern " ++ patIdx ++ " creato con BPM " ++ bpm ++ " e volume " ++ volume);
        
        // Restituisci il pattern con il clock
        pattern.play(clock);
    });
    
    // HOUSE
    ~patternFunctions.put(\house, { |patIdx=0, bpm=124, volume=0.8|
        var clock = TempoClock.new(bpm/60);
        var pattern;
        
        switch(patIdx,
            0, { // Pattern base
                pattern = Pbind(
                    \instrument, \kick,
                    \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                    \amp, volume * 0.9,
                    \freq, 60
                );
            },
            1, { // Kick + hat
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                        \amp, volume * 0.9,
                        \freq, 60
                    ),
                    Pbind(
                        \instrument, \hat,
                        \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf),
                        \amp, volume * 0.7,
                        \freq, 10000
                    )
                ]);
            },
            2, { // Kick + hat + snare
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                        \amp, volume * 0.9,
                        \freq, 60
                    ),
                    Pbind(
                        \instrument, \hat,
                        \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf),
                        \amp, volume * 0.7,
                        \freq, 10000
                    ),
                    Pbind(
                        \instrument, \snare,
                        \dur, Pseq([1, 1], inf),
                        \amp, volume * 0.8,
                        \freq, 150
                    )
                ]);
            },
            { // Pattern completo (default per 3 o altri valori)
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                        \amp, volume * 0.9,
                        \freq, 60
                    ),
                    Pbind(
                        \instrument, \hat,
                        \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf),
                        \amp, volume * 0.7,
                        \freq, 10000
                    ),
                    Pbind(
                        \instrument, \snare,
                        \dur, Pseq([1, 1], inf),
                        \amp, volume * 0.8,
                        \freq, 150
                    ),
                    Pbind(
                        \instrument, \bass,
                        \dur, Pseq([0.25, 0.25, 0.5, 0.5, 0.5], inf),
                        \amp, volume * 0.8,
                        \freq, Pseq([60, 80, 100, 80, 60], inf)
                    )
                ]);
            }
        );
        
        ~debug.value("HOUSE pattern " ++ patIdx ++ " creato con BPM " ++ bpm ++ " e volume " ++ volume);
        
        // Restituisci il pattern con il clock
        pattern.play(clock);
    });
    
    // DRUMANDBASS
    ~patternFunctions.put(\drumandbass, { |patIdx=0, bpm=172, volume=0.8|
        var clock = TempoClock.new(bpm/60);
        var pattern;
        
        switch(patIdx,
            0, { // Pattern base
                pattern = Pbind(
                    \instrument, \kick,
                    \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                    \amp, volume * 0.9,
                    \freq, 60
                );
            },
            1, { // Kick + hat
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                        \amp, volume * 0.9,
                        \freq, 60
                    ),
                    Pbind(
                        \instrument, \hat,
                        \dur, Pseq([0.125, 0.125, 0.125, 0.125], inf),
                        \amp, volume * 0.7,
                        \freq, 12000
                    )
                ]);
            },
            2, { // Kick + hat + snare
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                        \amp, volume * 0.9,
                        \freq, 60
                    ),
                    Pbind(
                        \instrument, \hat,
                        \dur, Pseq([0.125, 0.125, 0.125, 0.125], inf),
                        \amp, volume * 0.7,
                        \freq, 12000
                    ),
                    Pbind(
                        \instrument, \snare,
                        \dur, Pseq([1, 1], inf),
                        \amp, volume * 0.8,
                        \freq, 200
                    )
                ]);
            },
            { // Pattern completo (default per 3 o altri valori)
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf),
                        \amp, volume * 0.9,
                        \freq, 60
                    ),
                    Pbind(
                        \instrument, \hat,
                        \dur, Pseq([0.125, 0.125, 0.125, 0.125], inf),
                        \amp, volume * 0.7,
                        \freq, 12000
                    ),
                    Pbind(
                        \instrument, \snare,
                        \dur, Pseq([1, 1], inf),
                        \amp, volume * 0.8,
                        \freq, 200
                    ),
                    Pbind(
                        \instrument, \bass,
                        \dur, Pseq([0.25, 0.25, 0.125, 0.125, 0.25], inf),
                        \amp, volume * 0.8,
                        \freq, Pseq([60, 80, 100, 80, 60], inf)
                    )
                ]);
            }
        );
        
        ~debug.value("DRUMANDBASS pattern " ++ patIdx ++ " creato con BPM " ++ bpm ++ " e volume " ++ volume);
        
        // Restituisci il pattern con il clock
        pattern.play(clock);
    });
    
    // AMBIENT
    ~patternFunctions.put(\ambient, { |patIdx=0, bpm=60, volume=0.8|
        var clock = TempoClock.new(bpm/60);
        var pattern;
        
        switch(patIdx,
            0, { // Pattern base
                pattern = Pbind(
                    \instrument, \kick,
                    \dur, Pseq([4], inf),
                    \amp, volume * 0.5,
                    \freq, 40
                );
            },
            1, { // Pattern con bass
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([4], inf),
                        \amp, volume * 0.5,
                        \freq, 40
                    ),
                    Pbind(
                        \instrument, \bass,
                        \dur, Pseq([2, 2], inf),
                        \amp, volume * 0.6,
                        \freq, Pseq([40, 60, 50, 40], inf)
                    )
                ]);
            },
            2, { // Kick + bass + hat
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([4], inf),
                        \amp, volume * 0.5,
                        \freq, 40
                    ),
                    Pbind(
                        \instrument, \bass,
                        \dur, Pseq([2, 2], inf),
                        \amp, volume * 0.6,
                        \freq, Pseq([40, 60, 50, 40], inf)
                    ),
                    Pbind(
                        \instrument, \hat,
                        \dur, Pseq([1, 1, 1, 1], inf),
                        \amp, volume * 0.4,
                        \freq, 6000
                    )
                ]);
            },
            { // Pattern completo (default per 3 o altri valori)
                pattern = Ppar([
                    Pbind(
                        \instrument, \kick,
                        \dur, Pseq([4], inf),
                        \amp, volume * 0.5,
                        \freq, 40
                    ),
                    Pbind(
                        \instrument, \bass,
                        \dur, Pseq([2, 2], inf),
                        \amp, volume * 0.6,
                        \freq, Pseq([40, 60, 50, 40], inf)
                    ),
                    Pbind(
                        \instrument, \hat,
                        \dur, Pseq([1, 1, 1, 1], inf),
                        \amp, volume * 0.4,
                        \freq, 6000
                    ),
                    Pbind(
                        \instrument, \snare,
                        \dur, Pseq([2, 6], inf),
                        \amp, volume * 0.3,
                        \freq, 100
                    )
                ]);
            }
        );
        
        ~debug.value("AMBIENT pattern " ++ patIdx ++ " creato con BPM " ++ bpm ++ " e volume " ++ volume);
        
        // Restituisci il pattern con il clock
        pattern.play(clock);
    });
    
    // ===== FUNZIONE PER AVVIARE UN PATTERN =====
    ~playPattern = { |genre, patIdx, bpm, volume|
        // Debug
        ~debug.value("Avvio pattern: " ++ genre ++ ", idx: " ++ patIdx ++ ", BPM: " ++ bpm ++ ", volume: " ++ volume);
        
        // Arresta eventuali pattern attivi
        ~activePlayers.do { |player| 
            if(player.notNil, { 
                player.stop; 
                ~debug.value("Player arrestato"); 
            }); 
        };
        ~activePlayers = ();
        
        // Crea suono di conferma
        Synth(\kick, [\amp, 1.0]);
        
        // Avvia il nuovo pattern
        ~activePlayers[genre] = ~patternFunctions[genre].value(patIdx, bpm, volume);
        
        // Aggiorna variabili di stato
        ~currentGenre = genre;
        ~currentPattern = patIdx;
        ~currentBPM = bpm;
        ~currentVolume = volume;
        
        // Imposta volume master
        s.volume = volume * 2 - 1; // -1 a +1 dB
    };
    
    // ===== RICEZIONE OSC =====
    // Test comando
    OSCdef(\testCmd, { |msg, time, addr, recvPort|
        ~debug.value("[OSC] Test comando ricevuto!");
        Synth(\kick, [\amp, 1.0]);
    }, '/test', nil, nil).permanent_(true);
    
    // Volume
    OSCdef(\volumeCmd, { |msg, time, addr, recvPort|
        var vol = msg[1].asFloat;
        ~debug.value("[OSC] Volume ricevuto: " ++ vol);
        
        // Limita il volume all'intervallo [0, 1]
        vol = vol.clip(0, 1);
        
        // Aggiorna volume
        ~currentVolume = vol;
        
        // Aggiorna volume master
        s.volume = vol * 2 - 1; // -1 a +1 dB
        
        // Riavvia il pattern corrente
        ~playPattern.(~currentGenre, ~currentPattern, ~currentBPM, ~currentVolume);
    }, '/carretto/volume', nil, nil).permanent_(true);
    
    // BPM
    OSCdef(\bpmCmd, { |msg, time, addr, recvPort|
        var bpm = msg[1].asFloat;
        ~debug.value("[OSC] BPM ricevuto: " ++ bpm);
        
        // Limita il BPM a un intervallo ragionevole
        bpm = bpm.clip(60, 180);
        
        // Aggiorna BPM
        ~currentBPM = bpm;
        
        // Riavvia il pattern corrente
        ~playPattern.(~currentGenre, ~currentPattern, ~currentBPM, ~currentVolume);
    }, '/carretto/bpm', nil, nil).permanent_(true);
    
    // Pattern (Genere)
    OSCdef(\patternCmd, { |msg, time, addr, recvPort|
        var pattern_str = msg[1].asString;
        var genre;
        
        ~debug.value("[OSC] Pattern ricevuto: " ++ pattern_str);
        
        // Mappa il nome del genere al simbolo
        switch(pattern_str,
            "dub", { genre = \dub; },
            "techno", { genre = \techno; },
            "reggae", { genre = \reggae; },
            "house", { genre = \house; },
            "drumandbass", { genre = \drumandbass; },
            "ambient", { genre = \ambient; },
            "random", { 
                // Per random, seleziona un genere casuale
                var genreKeys = ~patternFunctions.keys.asArray;
                genre = genreKeys.choose;
                ~debug.value("[OSC] Random ha scelto: " ++ genre);
            },
            { 
                // Default a dub
                genre = \dub;
                ~debug.value("[OSC] Genere non riconosciuto, usando dub");
            }
        );
        
        // Avvia il pattern con il nuovo genere
        ~playPattern.(genre, 0, ~currentBPM, ~currentVolume);
    }, '/carretto/pattern', nil, nil).permanent_(true);
    
    // Pattern Index
    OSCdef(\patternIdxCmd, { |msg, time, addr, recvPort|
        var idx = msg[1].asInteger;
        ~debug.value("[OSC] Pattern Index ricevuto: " ++ idx);
        
        // Limita l'indice a 0-3
        idx = idx.clip(0, 3);
        
        // Avvia il pattern con il nuovo indice
        ~playPattern.(~currentGenre, idx, ~currentBPM, ~currentVolume);
    }, '/carretto/patternIdx', nil, nil).permanent_(true);
    
    // Tune (ignorato in questa implementazione semplificata)
    OSCdef(\tuneCmd, { |msg, time, addr, recvPort|
        var tune = msg[1].asFloat;
        ~debug.value("[OSC] Tune ricevuto: " ++ tune);
        
        // Per semplicità, non facciamo nulla con tune
        // Ma produciamo un suono di conferma
        Synth(\hat, [\amp, 0.8]);
    }, '/carretto/tune', nil, nil).permanent_(true);
    
    // ===== AVVIO INIZIALE =====
    ~debug.value("Avvio pattern iniziale...");
    ~playPattern.(\dub, 0, 120, 0.8);
    
    ~debug.value("[CARRETTO] Sistema pronto!");
    ~debug.value("Invia comandi OSC alla porta: " ++ NetAddr.langPort);
});
)
