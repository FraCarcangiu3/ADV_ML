#!/bin/bash
# Test mitragliatrice con valori progressivi

cd "/Users/francesco03/Documents/GitHub/AssaultCube Server/AC"

echo "🔫 TEST MITRAGLIATRICE - Progressione Pitch"
echo "=========================================="
echo ""
echo "⚠️  Per ogni test:"
echo "   1. Avvia il client"
echo "   2. Inizia una partita (Singleplayer > Team Deathmatch)"
echo "   3. Raccogli la mitragliatrice (Assault Rifle)"
echo "   4. SPARA diverse raffiche"
echo "   5. Ascolta attentamente"
echo "   6. Premi Ctrl+C per chiudere e passare al prossimo test"
echo ""
read -p "Premi INVIO per iniziare..."

# Test 1: Baseline (0 cents)
echo ""
echo "═══════════════════════════════════════"
echo "TEST 1: BASELINE (0 cents - originale)"
echo "═══════════════════════════════════════"
echo "Ascolta BENE questo audio originale!"
read -p "Premi INVIO per avviare..."
./source/src/ac_client
echo ""
echo "✅ Test 1 completato"
sleep 2

# Test 2: +200 cents
echo ""
echo "═══════════════════════════════════════"
echo "TEST 2: +200 cents (2 semitoni)"
echo "═══════════════════════════════════════"
echo "Confronta con l'originale - dovrebbe essere più acuto"
read -p "Premi INVIO per avviare..."
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=200 ./source/src/ac_client
echo ""
echo "❓ Hai sentito differenza?"
read -p "Nota qui: " nota2
sleep 2

# Test 3: +300 cents
echo ""
echo "═══════════════════════════════════════"
echo "TEST 3: +300 cents (3 semitoni)"
echo "═══════════════════════════════════════"
echo "Dovrebbe essere MOLTO più acuto"
read -p "Premi INVIO per avviare..."
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=300 ./source/src/ac_client
echo ""
echo "❓ Hai sentito differenza?"
read -p "Nota qui: " nota3
sleep 2

# Test 4: +400 cents
echo ""
echo "═══════════════════════════════════════"
echo "TEST 4: +400 cents (4 semitoni)"
echo "═══════════════════════════════════════"
echo "Dovrebbe essere ESTREMAMENTE acuto"
read -p "Premi INVIO per avviare..."
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=400 ./source/src/ac_client
echo ""
echo "❓ Hai sentito differenza?"
read -p "Nota qui: " nota4
sleep 2

# Test 5: +500 cents
echo ""
echo "═══════════════════════════════════════"
echo "TEST 5: +500 cents (5 semitoni) MASSIMO"
echo "═══════════════════════════════════════"
echo "Dovrebbe essere COMPLETAMENTE diverso!"
read -p "Premi INVIO per avviare..."
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=500 ./source/src/ac_client
echo ""
echo "❓ Hai sentito differenza?"
read -p "Nota qui: " nota5
sleep 2

# Test 6: -300 cents
echo ""
echo "═══════════════════════════════════════"
echo "TEST 6: -300 cents (3 semitoni più grave)"
echo "═══════════════════════════════════════"
echo "Dovrebbe essere MOLTO più grave/profondo"
read -p "Premi INVIO per avviare..."
AC_ANTICHEAT_PITCH_ENABLED=1 AC_ANTICHEAT_PITCH_CENTS=-300 ./source/src/ac_client
echo ""
echo "❓ Hai sentito differenza?"
read -p "Nota qui: " nota6

# Riepilogo
echo ""
echo "═══════════════════════════════════════"
echo "📊 RIEPILOGO TEST MITRAGLIATRICE"
echo "═══════════════════════════════════════"
echo "Test 2 (+200): $nota2"
echo "Test 3 (+300): $nota3"
echo "Test 4 (+400): $nota4"
echo "Test 5 (+500): $nota5"
echo "Test 6 (-300): $nota6"
echo ""
echo "✅ Test completati!"

