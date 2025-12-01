# Discorso per il Professore Relatore

Ho portato a termine l'implementazione tecnica del sistema di obfuscation audio per AssaultCube. Il framework C++ risulta completo e funzionante, con tutte le trasformazioni DSP implementate (pitch shift, noise injection, EQ tilt, filtri HP/LP) e integrate nell'architettura OpenAL mediante hook che ho cercato di rendere minimamente invasivo.
Successivamente ho mi sono concentrato sulla calibrazione, soggettiva e fatta in maniera abbastanza grossolana giusto per test, dei parametri per `weapon/usp` mediante tanti test in-game. 
Mi sono segnato i range trovati in questo caso per la pistola e ho preparato delle guide per trovare i valori di range per altri suoni in maniera molto facile. Tutti i valori sono contenuti in un file .csv che lo script utilizza per determinare il valore di ruore da aggiungere.
Successivamente ho implementato la randomizzazione uniforme dei parametri con seed basato su timestamp per garantire non-reproducibilità. Il sistema randomizza inoltre il tipo di noise (white/pink) e il segno dell'EQ (boost/cut) andando così a massimizzare l'entropia a 7.5 bit rispetto ai 5.5 bit della randomizzazione base (con tipologia di noise e EQ fissa). 
Ora sto documentando tutto e mi ci vorrà diverso tempo  perchè sono arrivato attualmente ad un totale di circa 2200 righe di codice che coprono l'implementazione, gli algoritmi DSP, la calibrazione e la metodologia.

Ho anche completato il sistema Python per test offline: ho creato script che replicano esattamente gli effetti del client C++ e li applicano ai dataset del collega. Ho corretto un problema importante: il rumore viene ora applicato solo durante lo sparo (non sul silenzio), come suggerito dal professore, per simulare meglio il comportamento reale del gioco.

Penso quindi di essere arrivato alla parte finale del mio lavoro che sembra funzionare (dal punto di vista tecnico) adesso penso che dovrei solamente dimostrare l'efficacia contro algoritmi di riconoscimento automatico tramite ML.


# Speech for my Supervisor

I finished the technical implementation of an audio obfuscation system for AssaultCube.
The C++ framework is complete and works. unlike last week where I was only working with pitch shift as Professor Regano suggested I implemented all the DSP transformations: pitch shift, noise injection, EQ tilt, and high-pass / low-pass filters. I integrated these into the OpenAL architecture using hooks and I tried to make the hooks minimally invasive.

Then I focused on calibration. The calibration was subjective and quite rough(ROUF), done only for testing. I tested many times in-game to find good parameter ranges for weapon/usp. I wrote down the ranges I found for the pistol and made simple guides to find ranges for other sounds. All values are stored in a .csv file that the script uses to decide the amount of noise to add.

After that I implemented and finish this last night the uniform randomization of parameters. The seed is based on the timestamp to avoid reproducibility and the ranges I used are wide so they allow for many possible combinations. The system also randomizes the noise type (white or pink) and the EQ sign (boost or cut). This increases entropy to 7.5 bits, compared to 5.5 bits when noise type and EQ sign are fixed.

Now I am documenting everything. This will take some time because the codebase is about 2,200 lines. I should do a refactor of the code. These lines cover the implementation, DSP algorithms, calibration, and the methodology.

I also completed the Python system: I created scripts that exactly replicate the C++ client effects and apply them to my colleague's datasets. I fixed an important issue: noise is now applied only during the gunshot (not on silence), as suggested by the professor, to better simulate the real game behavior.

I think I am now at the final part of my work. The system seems to work technically. The next step is to test how well it defends against automatic recognition algorithms using machine learning.