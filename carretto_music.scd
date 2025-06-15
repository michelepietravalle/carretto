/*
* CARRETTO MUSICALE - SISTEMA OSC COMPLETO
* Autore: Michele Pietravalle
* Data: 2025-06-15
* Versione: 3.2
*
* Sistema completo ottimizzato per Raspberry Pi 4
*/

(
// ===== CONFIGURAZIONE AUDIO =====
s = Server.default;
s.options.numOutputBusChannels = 2;
s.options.numInputBusChannels = 0;
s.options.sampleRate = 48000;
s.options.memSize = 8192;
s.options.bindAddress = "0.0.0.0";  // Ascolta su tutti gli indirizzi
s.options.maxLogins = 8;

// ===== DEBUG =====
~debug = { |msg| (">> " ++ msg).postln; };
~debug.value("CARRETTO MUSIC ENGINE");
~debug.value("Porta OSC: " ++ NetAddr.langPort);
~debug.value("Avvio del server audio...");

s.waitForBoot({
    ~debug.value("Server audio avviato!");
    
    // Variabili globali
    ~currentGenre = \dub;
    ~currentPattern = 0;
    ~currentBPM = 120;
    ~currentVolume = 0.8;
    ~activePlayers = ();
    ~genres = ["dub", "techno", "reggae", "house", "drumandbass", "ambient", "trap"];

    // ===== SYNTH DEFINITIONS =====
    // DUB
    SynthDef(\dubKick, {|amp=0.8, freq=60, dur=0.3|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = SinOsc.ar(freq * EnvGen.ar(Env([4, 1], [0.05])));
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    SynthDef(\dubSnare, {|amp=0.8, freq=100, dur=0.2|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = SinOsc.ar(freq) * 0.3 + WhiteNoise.ar() * 0.7;
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    SynthDef(\dubHat, {|amp=0.5, freq=8000, dur=0.1|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = BPF.ar(WhiteNoise.ar(), freq, 0.2);
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    SynthDef(\dubBass, {|amp=0.9, freq=60, dur=0.5|
        var env = EnvGen.ar(Env.perc(0.01, dur), doneAction: 2);
        var snd = SinOsc.ar([freq, freq*1.01]);
        snd = LPF.ar(snd, freq*3);
        Out.ar(0, (snd * env * amp));
    }).add;

    // TECHNO
    SynthDef(\techKick, {|amp=0.9, freq=60, dur=0.3|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = SinOsc.ar(freq * EnvGen.ar(Env([6, 1], [0.03])));
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    SynthDef(\techHat, {|amp=0.7, freq=9000, dur=0.05|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = BPF.ar(WhiteNoise.ar(), freq, 0.1);
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    SynthDef(\techBass, {|amp=0.9, freq=60, dur=0.2, cutoff=1800|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = Saw.ar(freq);
        snd = LPF.ar(snd, cutoff * EnvGen.ar(Env([1.5, 1], [0.1])));
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    // REGGAE
    SynthDef(\reggaeKick, {|amp=0.8, freq=60, dur=0.4|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = SinOsc.ar(freq * EnvGen.ar(Env([3, 1], [0.07])));
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    SynthDef(\reggaeSkank, {|amp=0.6, freq=440, dur=0.1|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = Pulse.ar(freq, 0.3) * 0.7 + SinOsc.ar(freq*2) * 0.3;
        snd = HPF.ar(snd, 400);
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    SynthDef(\reggaeBass, {|amp=0.9, freq=60, dur=0.5|
        var env = EnvGen.ar(Env.perc(0.01, dur), doneAction: 2);
        var snd = SinOsc.ar(freq) * 0.7 + (SinOsc.ar(freq*2) * 0.3);
        snd = LPF.ar(snd, 800);
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    // HOUSE
    SynthDef(\houseKick, {|amp=0.9, freq=60, dur=0.3|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = SinOsc.ar(freq * EnvGen.ar(Env([5, 1], [0.05])));
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    SynthDef(\houseClap, {|amp=0.8, freq=800, dur=0.2|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = BPF.ar(WhiteNoise.ar(), freq, 0.3);
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    SynthDef(\houseHat, {|amp=0.7, freq=10000, dur=0.1|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = HPF.ar(WhiteNoise.ar(), freq);
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    // AMBIENT
    SynthDef(\ambientPad, {|amp=0.6, freq=220, dur=2.0, attack=0.3|
        var env = EnvGen.ar(Env.perc(attack, dur), doneAction: 2);
        var snd = SinOsc.ar(freq) * 0.4 + SinOsc.ar(freq*1.01) * 0.3 + SinOsc.ar(freq*0.99) * 0.3;
        snd = LPF.ar(snd, 1200);
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    SynthDef(\ambientBell, {|amp=0.7, freq=440, dur=1.5|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = SinOsc.ar(freq) * SinOsc.ar(freq * 1.5);
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    // DRUM & BASS
    SynthDef(\dnbKick, {|amp=0.9, freq=60, dur=0.2|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = SinOsc.ar(freq * EnvGen.ar(Env([7, 1], [0.02])));
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    SynthDef(\dnbHat, {|amp=0.7, freq=12000, dur=0.05|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = HPF.ar(WhiteNoise.ar(), freq);
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    SynthDef(\dnbBass, {|amp=0.9, freq=60, dur=0.2, cutoff=2000|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = Saw.ar(freq) * 0.5 + (SinOsc.ar(freq/2) * 0.5);
        snd = LPF.ar(snd, cutoff);
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    // TRAP
    SynthDef(\trapKick, {|amp=0.9, freq=60, dur=0.6|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = SinOsc.ar(freq * EnvGen.ar(Env([4, 1], [0.04])));
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    SynthDef(\trapHat, {|amp=0.7, freq=12000, dur=0.05|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = HPF.ar(WhiteNoise.ar(), freq);
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    SynthDef(\trapBass, {|amp=0.9, freq=40, dur=0.3|
        var env = EnvGen.ar(Env.perc(0.001, dur), doneAction: 2);
        var snd = SinOsc.ar(freq);
        snd = LPF.ar(snd, 1000);
        Out.ar(0, (snd * env * amp)!2);
    }).add;

    // Attendi che tutti i synth siano definiti
    s.sync;
    ~debug.value("Synth definiti!");
    
    // ===== PATTERN FUNCTIONS =====
    ~patternFunctions = ();
    
    // DUB
    ~patternFunctions.put(\dub, { |patIdx=0, bpm=120, volume=0.8|
        var clock = TempoClock.new(bpm/60);
        var pattern;
        
        switch(patIdx,
            0, { // Pattern base
                pattern = Ppar([
                    Pbind(\instrument, \dubKick, \dur, Pseq([1, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \dubHat, \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.6 }, \freq, 8000)
                ]);
            },
            1, { // Pattern con basso
                pattern = Ppar([
                    Pbind(\instrument, \dubKick, \dur, Pseq([1, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \dubSnare, \dur, Pseq([2, 2], inf), 
                          \amp, Pfunc { ~currentVolume * 0.8 }, \freq, 100),
                    Pbind(\instrument, \dubHat, \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.6 }, \freq, 8000),
                    Pbind(\instrument, \dubBass, \dur, Pseq([0.5, 0.5, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, 
                          \freq, Pseq([60, 60, 40, 50, 60], inf))
                ]);
            },
            2, { // Pattern complesso
                pattern = Ppar([
                    Pbind(\instrument, \dubKick, \dur, Pseq([1, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \dubSnare, \dur, Pseq([2, 2], inf), 
                          \amp, Pfunc { ~currentVolume * 0.8 }, \freq, 100),
                    Pbind(\instrument, \dubHat, \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.6 }, \freq, 8000),
                    Pbind(\instrument, \dubBass, \dur, Pseq([0.5, 0.5, 1, 1, 0.5, 0.5, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, 
                          \freq, Pseq([60, 60, 40, 50, 60, 60, 45, 55], inf))
                ]);
            },
            { // Pattern default
                pattern = Ppar([
                    Pbind(\instrument, \dubKick, \dur, Pseq([1, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \dubHat, \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.6 }, \freq, 8000),
                    Pbind(\instrument, \dubBass, \dur, Pseq([0.5, 0.5, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, 
                          \freq, Pseq([60, 60, 40, 50, 60], inf))
                ]);
            }
        );
        
        ~debug.value("DUB pattern " ++ patIdx ++ " creato con BPM " ++ bpm);
        
        // Avvia il pattern con il clock
        pattern.play(clock);
    });
    
    // TECHNO
    ~patternFunctions.put(\techno, { |patIdx=0, bpm=128, volume=0.8|
        var clock = TempoClock.new(bpm/60);
        var pattern;
        
        switch(patIdx,
            0, { // Pattern base
                pattern = Ppar([
                    Pbind(\instrument, \techKick, \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \techHat, \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 9000)
                ]);
            },
            1, { // Pattern con basso
                pattern = Ppar([
                    Pbind(\instrument, \techKick, \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \techHat, \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 9000),
                    Pbind(\instrument, \techBass, \dur, Pseq([0.25, 0.25, 0.25, 0.25, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.8 }, 
                          \freq, Pseq([60, 60, 60, 60, 80, 40], inf))
                ]);
            },
            2, { // Pattern complesso
                pattern = Ppar([
                    Pbind(\instrument, \techKick, \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \techHat, \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 9000),
                    Pbind(\instrument, \techBass, \dur, Pseq([0.25, 0.25, 0.25, 0.25, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.8 }, 
                          \freq, Pseq([60, 60, 60, 60, 80, 40], inf))
                ]);
            },
            { // Pattern default
                pattern = Ppar([
                    Pbind(\instrument, \techKick, \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \techHat, \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 9000)
                ]);
            }
        );
        
        ~debug.value("TECHNO pattern " ++ patIdx ++ " creato con BPM " ++ bpm);
        
        // Avvia il pattern con il clock
        pattern.play(clock);
    });
    
    // REGGAE
    ~patternFunctions.put(\reggae, { |patIdx=0, bpm=80, volume=0.8|
        var clock = TempoClock.new(bpm/60);
        var pattern;
        
        switch(patIdx,
            0, { // Pattern base
                pattern = Ppar([
                    Pbind(\instrument, \reggaeKick, \dur, Pseq([1, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.8 }, \freq, 60),
                    Pbind(\instrument, \reggaeSkank, \dur, Pseq([1, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.6 }, 
                          \freq, Pseq([440, 550, 440, 550], inf))
                ]);
            },
            1, { // Pattern con basso
                pattern = Ppar([
                    Pbind(\instrument, \reggaeKick, \dur, Pseq([1, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.8 }, \freq, 60),
                    Pbind(\instrument, \reggaeSkank, \dur, Pseq([1, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.6 }, 
                          \freq, Pseq([440, 550, 440, 550], inf)),
                    Pbind(\instrument, \reggaeBass, \dur, Pseq([0.5, 0.5, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, 
                          \freq, Pseq([60, 60, 45, 50, 60], inf))
                ]);
            },
            2, { // Pattern complesso
                pattern = Ppar([
                    Pbind(\instrument, \reggaeKick, \dur, Pseq([1, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.8 }, \freq, 60),
                    Pbind(\instrument, \reggaeSkank, \dur, Pseq([1, 1, 1, 1, 0.5, 0.5, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.6 }, 
                          \freq, Pseq([440, 550, 440, 550, 660, 550, 440, 330], inf)),
                    Pbind(\instrument, \reggaeBass, \dur, Pseq([0.5, 0.5, 1, 1, 1, 0.5, 0.5, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, 
                          \freq, Pseq([60, 60, 45, 50, 60, 60, 60, 40, 45, 60], inf))
                ]);
            },
            { // Pattern default
                pattern = Ppar([
                    Pbind(\instrument, \reggaeKick, \dur, Pseq([1, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.8 }, \freq, 60),
                    Pbind(\instrument, \reggaeSkank, \dur, Pseq([1, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.6 }, 
                          \freq, Pseq([440, 550, 440, 550], inf))
                ]);
            }
        );
        
        ~debug.value("REGGAE pattern " ++ patIdx ++ " creato con BPM " ++ bpm);
        
        // Avvia il pattern con il clock
        pattern.play(clock);
    });
    
    // HOUSE
    ~patternFunctions.put(\house, { |patIdx=0, bpm=124, volume=0.8|
        var clock = TempoClock.new(bpm/60);
        var pattern;
        
        switch(patIdx,
            0, { // Pattern base
                pattern = Ppar([
                    Pbind(\instrument, \houseKick, \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \houseHat, \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 10000)
                ]);
            },
            1, { // Pattern con clap
                pattern = Ppar([
                    Pbind(\instrument, \houseKick, \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \houseHat, \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 10000),
                    Pbind(\instrument, \houseClap, \dur, Pseq([1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.8 }, \freq, 800)
                ]);
            },
            2, { // Pattern complesso
                pattern = Ppar([
                    Pbind(\instrument, \houseKick, \dur, Pseq([0.5, 0.5, 0.5, 0.5, 0.25, 0.25, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \houseHat, \dur, Pseq([0.25, 0.25, 0.25, 0.25, 0.125, 0.125, 0.25, 0.25], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 10000),
                    Pbind(\instrument, \houseClap, \dur, Pseq([1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.8 }, \freq, 800)
                ]);
            },
            { // Pattern default
                pattern = Ppar([
                    Pbind(\instrument, \houseKick, \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \houseHat, \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 10000)
                ]);
            }
        );
        
        ~debug.value("HOUSE pattern " ++ patIdx ++ " creato con BPM " ++ bpm);
        
        // Avvia il pattern con il clock
        pattern.play(clock);
    });
    
    // AMBIENT
    ~patternFunctions.put(\ambient, { |patIdx=0, bpm=60, volume=0.8|
        var clock = TempoClock.new(bpm/60);
        var pattern;
        
        switch(patIdx,
            0, { // Pattern base
                pattern = Pbind(\instrument, \ambientPad, \dur, Pseq([4], inf), 
                               \amp, Pfunc { ~currentVolume * 0.6 }, 
                               \freq, Pseq([220, 330, 440, 275], inf), \attack, 0.3);
            },
            1, { // Pattern con bells
                pattern = Ppar([
                    Pbind(\instrument, \ambientPad, \dur, Pseq([4], inf), 
                          \amp, Pfunc { ~currentVolume * 0.6 }, 
                          \freq, Pseq([220, 330, 440, 275], inf), \attack, 0.3),
                    Pbind(\instrument, \ambientBell, \dur, Pseq([2, 4, 2], inf), 
                          \amp, Pfunc { ~currentVolume * 0.5 }, 
                          \freq, Pseq([440, 550, 660], inf))
                ]);
            },
            2, { // Pattern complesso
                pattern = Ppar([
                    Pbind(\instrument, \ambientPad, \dur, Pseq([4, 4, 4, 4], inf), 
                          \amp, Pfunc { ~currentVolume * 0.6 }, 
                          \freq, Pseq([220, 330, 440, 275, 165, 220], inf), 
                          \attack, Pseq([0.3, 0.5, 0.3, 0.4], inf)),
                    Pbind(\instrument, \ambientBell, \dur, Pseq([2, 4, 2, 3, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.5 }, 
                          \freq, Pseq([440, 550, 660, 770, 880, 990], inf))
                ]);
            },
            { // Pattern default
                pattern = Pbind(\instrument, \ambientPad, \dur, Pseq([4], inf), 
                               \amp, Pfunc { ~currentVolume * 0.6 }, 
                               \freq, Pseq([220, 330, 440, 275], inf), \attack, 0.3);
            }
        );
        
        ~debug.value("AMBIENT pattern " ++ patIdx ++ " creato con BPM " ++ bpm);
        
        // Avvia il pattern con il clock
        pattern.play(clock);
    });
    
    // DRUMANDBASS
    ~patternFunctions.put(\drumandbass, { |patIdx=0, bpm=172, volume=0.8|
        var clock = TempoClock.new(bpm/60);
        var pattern;
        
        switch(patIdx,
            0, { // Pattern base
                pattern = Ppar([
                    Pbind(\instrument, \dnbKick, \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \dnbHat, \dur, Pseq([0.125, 0.125, 0.125, 0.125], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 12000)
                ]);
            },
            1, { // Pattern con basso
                pattern = Ppar([
                    Pbind(\instrument, \dnbKick, \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \dnbHat, \dur, Pseq([0.125, 0.125, 0.125, 0.125], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 12000),
                    Pbind(\instrument, \dnbBass, \dur, Pseq([0.25, 0.25, 0.125, 0.125, 0.25], inf), 
                          \amp, Pfunc { ~currentVolume * 0.8 }, 
                          \freq, Pseq([60, 80, 100, 80, 60], inf))
                ]);
            },
            2, { // Pattern complesso
                pattern = Ppar([
                    Pbind(\instrument, \dnbKick, \dur, Pseq([0.5, 0.5, 0.5, 0.5, 0.25, 0.25, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \dnbHat, \dur, Pseq([0.125, 0.125, 0.125, 0.125, 0.0625, 0.0625, 0.125, 0.125], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 12000),
                    Pbind(\instrument, \dnbBass, \dur, Pseq([0.25, 0.25, 0.125, 0.125, 0.25, 0.125, 0.125, 0.25], inf), 
                          \amp, Pfunc { ~currentVolume * 0.8 }, 
                          \freq, Pseq([60, 80, 100, 80, 60, 100, 80, 60], inf))
                ]);
            },
            { // Pattern default
                pattern = Ppar([
                    Pbind(\instrument, \dnbKick, \dur, Pseq([0.5, 0.5, 0.5, 0.5], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \dnbHat, \dur, Pseq([0.125, 0.125, 0.125, 0.125], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 12000)
                ]);
            }
        );
        
        ~debug.value("DRUM & BASS pattern " ++ patIdx ++ " creato con BPM " ++ bpm);
        
        // Avvia il pattern con il clock
        pattern.play(clock);
    });
    
    // TRAP
    ~patternFunctions.put(\trap, { |patIdx=0, bpm=70, volume=0.8|
        var clock = TempoClock.new(bpm/60);
        var pattern;
        
        switch(patIdx,
            0, { // Pattern base
                pattern = Ppar([
                    Pbind(\instrument, \trapKick, \dur, Pseq([1, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \trapHat, \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 12000)
                ]);
            },
            1, { // Pattern con basso
                pattern = Ppar([
                    Pbind(\instrument, \trapKick, \dur, Pseq([1, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \trapHat, \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 12000),
                    Pbind(\instrument, \trapBass, \dur, Pseq([0.5, 0.5, 0.5, 0.5, 2], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, 
                          \freq, Pseq([40, 40, 40, 40, 30], inf))
                ]);
            },
            2, { // Pattern complesso
                pattern = Ppar([
                    Pbind(\instrument, \trapKick, \dur, Pseq([1, 1, 1, 1, 0.5, 0.5, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \trapHat, \dur, Pseq([0.25, 0.25, 0.25, 0.25, 0.125, 0.125, 0.125, 0.125], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 12000),
                    Pbind(\instrument, \trapBass, \dur, Pseq([0.5, 0.5, 0.5, 0.5, 2, 0.5, 0.5, 0.5, 0.5, 2], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, 
                          \freq, Pseq([40, 40, 40, 40, 30, 40, 40, 40, 40, 35], inf))
                ]);
            },
            { // Pattern default
                pattern = Ppar([
                    Pbind(\instrument, \trapKick, \dur, Pseq([1, 1, 1, 1], inf), 
                          \amp, Pfunc { ~currentVolume * 0.9 }, \freq, 60),
                    Pbind(\instrument, \trapHat, \dur, Pseq([0.25, 0.25, 0.25, 0.25], inf), 
                          \amp, Pfunc { ~currentVolume * 0.7 }, \freq, 12000)
                ]);
            }
        );
        
        ~debug.value("TRAP pattern " ++ patIdx ++ " creato con BPM " ++ bpm);
        
        // Avvia il pattern con il clock
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
        Synth(\techKick, [\amp, 1.0]);
        
        // Avvia il nuovo pattern
        ~activePlayers[genre] = ~patternFunctions[genre].value(patIdx, bpm, volume);
        
        // Aggiorna variabili di stato
        ~currentGenre = genre;
        ~currentPattern = patIdx;
        ~currentBPM = bpm;
        ~currentVolume = volume;
        
        // Imposta volume master
        s.volume = volume * 2 - 0.5; // -0.5 a +1.5 dB
    };
    
    // ===== RICEZIONE OSC =====
    // Test comando
    OSCdef(\testCmd, { |msg, time, addr, recvPort|
        ~debug.value("[OSC] Test comando ricevuto!");
        Synth(\techKick, [\amp, 1.0]);
    }, '/test', nil, nil).permanent_(true);
    
    // Volume
    OSCdef(\volumeCmd, { |msg, time, addr, recvPort|
        var vol = msg[1].asFloat;
        ~debug.value("[OSC] Volume ricevuto: " ++ vol);
        
        // Limita il volume all'intervallo [0, 1]
        vol = vol.clip(0, 1);
        
        // Aggiorna volume
        ~currentVolume = vol;
        
        // Aggiorna volume master (potenziato per essere più evidente)
        s.volume = vol * 2 - 0.5; // -0.5 a +1.5 dB
        
        // Crea feedback audio
        Synth(\techHat, [\amp, vol]);
        
        ~debug.value("[OSC] Volume impostato a " ++ vol);
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
            "trap", { genre = \trap; },
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
        Synth(\techHat, [\amp, 0.8]);
    }, '/carretto/tune', nil, nil).permanent_(true);
    
    // ===== AVVIO INIZIALE =====
    ~debug.value("Avvio pattern iniziale...");
    ~playPattern.(\dub, 0, 120, 0.8);
    
    ~debug.value("[CARRETTO] Sistema pronto!");
    ~debug.value("Invia comandi OSC alla porta: " ++ NetAddr.langPort);
});
)
