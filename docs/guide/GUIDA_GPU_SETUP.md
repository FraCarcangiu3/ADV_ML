# Guida: Configurazione GPU per Training Accelerato

## 🎯 Obiettivo

Configurare PyTorch per usare la GPU (se disponibile sul server) invece della CPU, velocizzando il training di **10-50x**.

---

## 📋 STEP 1: Verifica se il Server ha una GPU

Sul server SSH:

```bash
# 1. Controlla se ci sono GPU NVIDIA
nvidia-smi

# Se vedi output tipo questo, hai una GPU:
# +-----------------------------------------------------------------------------+
# | NVIDIA-SMI 525.60.13    Driver Version: 525.60.13    CUDA Version: 12.0     |
# |-------------------------------+----------------------+----------------------+
# | GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
# |   0  Tesla T4            Off  | 00000000:00:1E.0 Off |                    0 |
# +-------------------------------+----------------------+----------------------+

# 2. Se nvidia-smi non funziona, prova:
lspci | grep -i nvidia

# 3. Oppure controlla in /proc:
ls /proc/driver/nvidia/
```

### Risultati Possibili

| Comando | Output | Significato |
|---------|--------|-------------|
| `nvidia-smi` | Tabella GPU | ✅ **GPU disponibile** |
| `nvidia-smi` | `command not found` | ❌ Nessuna GPU o driver non installati |
| `lspci \| grep nvidia` | Lista dispositivi | GPU presente ma driver mancanti |
| `lspci \| grep nvidia` | Nessun output | ❌ Nessuna GPU fisica |

---

## 🔧 STEP 2: Installa PyTorch con Supporto GPU

### Se hai GPU NVIDIA (caso comune)

```bash
# Attiva ambiente conda
conda activate ac_ml

# RIMUOVI PyTorch CPU (se già installato)
pip uninstall torch torchvision torchaudio -y

# Installa PyTorch con supporto CUDA
# Per CUDA 11.8 (comune):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Per CUDA 12.1 (più recente):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Se non sai quale versione CUDA hai:
nvidia-smi  # Guarda "CUDA Version: X.Y" nell'output
```

### Come scegliere la versione CUDA

| CUDA Version (da `nvidia-smi`) | Comando pip |
|--------------------------------|-------------|
| 11.x (es. 11.7, 11.8) | `--index-url https://download.pytorch.org/whl/cu118` |
| 12.x (es. 12.0, 12.1) | `--index-url https://download.pytorch.org/whl/cu121` |
| 10.x (vecchio) | `--index-url https://download.pytorch.org/whl/cu102` |

**Nota:** PyTorch è compatibile con versioni CUDA leggermente diverse. CUDA 11.8 funziona anche con 11.7-11.9, CUDA 12.1 funziona anche con 12.0-12.3.

---

## ✅ STEP 3: Verifica che PyTorch Veda la GPU

```bash
# Attiva ambiente
conda activate ac_ml

# Test rapido Python
python << 'EOF'
import torch

print("=" * 60)
print("PYTORCH GPU CHECK")
print("=" * 60)

# 1. Versione PyTorch
print(f"PyTorch version: {torch.__version__}")

# 2. CUDA disponibile?
cuda_available = torch.cuda.is_available()
print(f"CUDA available: {cuda_available}")

if cuda_available:
    # 3. Versione CUDA
    print(f"CUDA version: {torch.version.cuda}")
    
    # 4. Numero GPU
    num_gpus = torch.cuda.device_count()
    print(f"Number of GPUs: {num_gpus}")
    
    # 5. Nome GPU
    for i in range(num_gpus):
        print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
    
    # 6. Memoria GPU
    gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"GPU 0 memory: {gpu_mem:.2f} GB")
    
    # 7. Test allocazione
    try:
        x = torch.randn(1000, 1000).cuda()
        print(f"✅ Test allocazione GPU: SUCCESS")
    except Exception as e:
        print(f"❌ Test allocazione GPU: FAILED - {e}")
else:
    print("❌ CUDA non disponibile")
    print("   Possibili cause:")
    print("   - PyTorch installato senza supporto CUDA")
    print("   - Driver NVIDIA non installati")
    print("   - Nessuna GPU fisica presente")

print("=" * 60)
EOF
```

### Output Atteso (se GPU disponibile)

```
============================================================
PYTORCH GPU CHECK
============================================================
PyTorch version: 2.1.0+cu118
CUDA available: True
CUDA version: 11.8
Number of GPUs: 1
GPU 0: Tesla T4
GPU 0 memory: 15.89 GB
✅ Test allocazione GPU: SUCCESS
============================================================
```

### Output se GPU NON disponibile

```
============================================================
PYTORCH GPU CHECK
============================================================
PyTorch version: 2.1.0+cpu
CUDA available: False
❌ CUDA non disponibile
   Possibili cause:
   - PyTorch installato senza supporto CUDA
   - Driver NVIDIA non installati
   - Nessuna GPU fisica presente
============================================================
```

---

## 🚀 STEP 4: Rilancia Training con GPU

Una volta configurato, il codice del collega usa **automaticamente** la GPU!

```bash
cd COLLEAGUE_BSc_Thesis

# Il codice rileva automaticamente la GPU
# Nessun parametro extra necessario!
python -m model_classifier.deep_cv

# Oppure in background:
nohup python -m model_classifier.deep_cv > logs_deep_cv_gpu.txt 2>&1 &
```

**Cosa cambia:**
- ✅ Nessun warning `pin_memory`
- ✅ Training **10-50x più veloce**
- ✅ Nei log vedrai: `device=cuda:0` invece di `device=cpu`

### Monitora Uso GPU durante Training

In un altro terminale:

```bash
# Monitora GPU ogni 2 secondi
watch -n 2 nvidia-smi

# Oppure in loop manuale
while true; do clear; nvidia-smi; sleep 2; done
```

**Output atteso durante training:**

```
+-----------------------------------------------------------------------------+
| Processes:                                                                  |
|  GPU   GI   CI        PID   Type   Process name                  GPU Memory |
|  0     N/A  N/A    123456      C   python                          8234MiB |
+-----------------------------------------------------------------------------+
```

---

## 🔍 Troubleshooting

### Problema 1: `nvidia-smi: command not found`

**Causa:** Driver NVIDIA non installati o GPU non disponibile.

**Soluzione:**

```bash
# Verifica se hai GPU fisica
lspci | grep -i nvidia

# Se vedi GPU ma nvidia-smi manca, installa driver:
# (richiede permessi sudo - contatta admin del server)
sudo apt update
sudo apt install nvidia-driver-525  # o versione più recente
sudo reboot

# Dopo reboot:
nvidia-smi
```

### Problema 2: `CUDA available: False` anche dopo install

**Causa:** PyTorch installato senza CUDA o versione CUDA incompatibile.

**Soluzione:**

```bash
conda activate ac_ml

# 1. Verifica versione PyTorch
pip show torch | grep Version

# Se vedi "cpu" nel nome (es. 2.1.0+cpu):
pip uninstall torch torchvision torchaudio -y
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 2. Re-verifica
python -c "import torch; print(torch.cuda.is_available())"
```

### Problema 3: `RuntimeError: CUDA out of memory`

**Causa:** GPU ha poca memoria per il batch size corrente.

**Soluzione 1 - Riduci batch size:**

```bash
# Modifica temporanea nel codice deep_cv.py
# Cerca: batch_size=16  (o altro valore)
# Cambia in: batch_size=8  (o 4 se serve)
```

**Soluzione 2 - Usa gradient accumulation:**

```bash
# Aggiungi variabile ambiente
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512 python -m model_classifier.deep_cv
```

### Problema 4: Server ha GPU ma è già occupata da altri

```bash
# Controlla chi sta usando la GPU
nvidia-smi

# Se vedi altri processi, puoi:
# 1. Aspettare che finiscano
# 2. Chiedere all'admin di riservare GPU
# 3. Usare GPU specifica (se multi-GPU):
CUDA_VISIBLE_DEVICES=1 python -m model_classifier.deep_cv  # Usa GPU 1
```

### Problema 5: Warning "GPU 0 has a cuda capability..."

```bash
# Warning tipo:
# UserWarning: GPU 0 has a cuda capability of 3.5, which is less than 3.7

# Causa: GPU molto vecchia (es. Kepler)
# Il training funziona comunque, ma sarà più lento
# Soluzione: Nessuna azione necessaria (o usa CPU se GPU è troppo vecchia)
```

---

## 📊 Confronto Performance: CPU vs GPU

### Dataset Esempio: 1000 campioni, 9-fold CV

| Hardware | Tempo per Fold | Tempo Totale (9 fold) | Speedup |
|----------|----------------|----------------------|---------|
| CPU (16 core Intel Xeon) | ~40 min | **~6 ore** | 1x |
| GPU (NVIDIA T4) | ~2 min | **~18 min** | **20x** |
| GPU (NVIDIA V100) | ~1 min | **~9 min** | **40x** |
| GPU (NVIDIA A100) | ~30 sec | **~5 min** | **72x** |

**Conclusione:** Se il server ha GPU, **usala assolutamente**! 🚀

---

## 🎯 Verifica Finale Prima del Training

Checklist completa:

```bash
# 1. GPU disponibile
nvidia-smi  # ✅ Vedi tabella GPU

# 2. PyTorch vede GPU
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"  # ✅ True

# 3. Test allocazione
python -c "import torch; x = torch.randn(100,100).cuda(); print('✅ GPU OK')"

# 4. Checkpoint puliti (se riparti da zero)
rm -rf COLLEAGUE_BSc_Thesis/model_classifier/checkpoints/*.pth

# 5. Lancia training
cd COLLEAGUE_BSc_Thesis
nohup python -m model_classifier.deep_cv > logs_gpu.txt 2>&1 &

# 6. Verifica che usi GPU (nei primi 30 sec)
sleep 30 && tail -30 logs_gpu.txt | grep -i "device"
# Output atteso: "device=cuda:0" o "device=cuda"

# 7. Monitora GPU
watch -n 2 nvidia-smi
```

---

## 📋 Comandi Rapidi per Server SSH

### Setup Iniziale (una volta)

```bash
# Test GPU
nvidia-smi

# Se GPU presente, installa PyTorch con CUDA
conda activate ac_ml
pip uninstall torch torchvision torchaudio -y
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verifica
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

### Training con GPU

```bash
cd COLLEAGUE_BSc_Thesis

# Launch training (usa GPU automaticamente se disponibile)
nohup python -m model_classifier.deep_cv > logs_gpu.txt 2>&1 &

# Monitor
tail -f logs_gpu.txt         # Log training
watch -n 2 nvidia-smi        # Uso GPU (altro terminale)
```

---

## 🔗 Riferimenti Utili

- **PyTorch - Get Started:** https://pytorch.org/get-started/locally/
- **CUDA Compatibility:** https://docs.nvidia.com/deploy/cuda-compatibility/
- **nvidia-smi Guide:** https://developer.nvidia.com/nvidia-system-management-interface

---

## 💡 Riepilogo

| Situazione | Azione |
|------------|--------|
| ✅ Server ha GPU | Installa PyTorch con CUDA → Training 20-40x più veloce |
| ❌ Server senza GPU | Usa PyTorch CPU → Training funziona ma più lento |
| ⚠️ GPU occupata | Aspetta o usa `CUDA_VISIBLE_DEVICES` per altra GPU |
| 🐛 CUDA OOM | Riduci batch size o usa CPU |

**Fine Guida** 🎮

**Autore:** Francesco Carcangiu  
**Ultimo aggiornamento:** 2025-12-02

#test 
