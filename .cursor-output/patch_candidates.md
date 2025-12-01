# Pitch Shift PoC – Candidate Hook Points

1) AC/source/src/openal.cpp : lines ~280–305 (before alBufferData for OGG decode)
Motivazione: punto immediatamente prima del caricamento nel buffer OpenAL. Qui i campioni PCM (buf.getbuf(), buf.length(), info->rate) sono disponibili; inserire una trasformazione (pitch shift) è naturale e a basso impatto, prima che i dati vengano copiati in OpenAL.

2) AC/source/src/openal.cpp : lines ~320–338 (before alBufferData for WAV load)
Motivazione: percorso alternativo per file WAV via SDL_LoadWAV; anche qui i dati PCM (wavbuf, wavlen, wavspec.freq) sono pronti. Un hook qui copre asset non-OGG.

3) AC/source/src/soundlocation.cpp : location::play/updatepos (range ~180–210)
Motivazione: livello alto di gestione sorgenti; possibile applicare offset/pitch a runtime, ma meno ideale per un POC PCM→transform perché qui il pitch è un parametro OpenAL (src->pitch) e non una trasformazione dei campioni. Preferibile solo se si vuole un pitch ‘globale’ senza modificare PCM.
