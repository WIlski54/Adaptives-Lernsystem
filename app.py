from flask import Flask, render_template, request, jsonify, session
import openai
import os
import secrets
import json
from image_resources import finde_passendes_bild, BILDER

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# OpenAI API Key
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Themen-Definitionen
THEMEN = {
    '1_grundlagen': {
        'name': 'DNA-Grundlagen',
        'beschreibung': 'Aufbau und Struktur der DNA',
        'konzepte': [
            'Nukleotide als Bausteine',
            'Die vier Basen (A, T, G, C)',
            'Basenpaarungsregeln',
            'Doppelhelix-Struktur'
        ]
    },
    '2_aufbau': {
        'name': 'Chromosomen und Gene',
        'beschreibung': 'Von Chromosomen zu Genen',
        'konzepte': [
            'Chromosomenstruktur',
            'Gene als DNA-Abschnitte',
            'Zellkern und Chromatin'
        ]
    },
    '3_replikation': {
        'name': 'DNA-Replikation',
        'beschreibung': 'Verdopplung der DNA',
        'konzepte': [
            'Semikonservative Replikation',
            'Enzyme (Helikase, Polymerase)',
            'Replikationsgabel'
        ]
    },
    '4_vererbung': {
        'name': 'Vererbung und Merkmale',
        'beschreibung': 'Wie Merkmale vererbt werden',
        'konzepte': [
            'Phänotyp und Genotyp',
            'Allele (dominant, rezessiv)',
            'Mendelsche Regeln'
        ]
    }
}

# System-Prompt für sokratischen Dialog-Tutor
TUTOR_SYSTEM_PROMPT = """Du bist ein geduldiger, sokratischer Biologie-Tutor für Schüler der Klassen 9-10.

DEINE PHILOSOPHIE:
- Du gibst NIEMALS direkt die Antwort
- Du führst den Schüler durch RÜCKFRAGEN und HINWEISE zum Verständnis
- Du baust auf dem Vorwissen des Schülers auf
- Du bist streng bei wissenschaftlichen Begriffen (z.B. "Cytosin" nicht "Cytosil")

DIALOG-STRATEGIE:
1. ERKUNDE das Vorwissen: "Was weißt du schon über...?"
2. LEITE durch Fragen: "Überleg mal, wenn..."
3. GEBE HINWEISE statt Lösungen: "Denk an..."
4. BIETE BILDER AN falls hilfreich: "Schau dir mal das Bild zu [Thema] an"
5. BESTÄTIGE Verständnis: "Genau! Und was bedeutet das für...?"

BILDER EINSETZEN:
- Sage explizit: "Schau dir mal das Bild zu [Thema] an" oder "Ich zeige dir ein Bild..."
- Nur wenn es dem Verständnis WIRKLICH hilft
- NICHT bei jeder Nachricht

WICHTIG:
- Mehrere Dialog-Turns pro Konzept
- Erst wenn Schüler das Konzept verstanden hat → nächstes Konzept
- Bleibe im Dialog, keine abrupten Themenwechsel
- Maximal 2-3 Sätze pro Antwort (kurz und fokussiert!)

ANTWORT-FORMAT (JSON):
{
    "nachricht": "Deine Antwort an den Schüler (2-3 Sätze)",
    "zeige_bild": true/false,
    "bild_thema": "basen" oder null (welches Bild aus BILDER zeigen),
    "konzept_verstanden": true/false (Ist das aktuelle Konzept verstanden?)
}"""


@app.route('/')
def index():
    """Hauptseite"""
    return render_template('index.html')


@app.route('/start', methods=['POST'])
def start():
    """Startet eine neue Lernsession"""
    try:
        data = request.json
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Bitte Namen eingeben'}), 400
        
        # Session initialisieren
        session['name'] = name
        session['punkte'] = 0
        session['aktuelles_thema'] = '1_grundlagen'
        session['aktuelles_konzept_index'] = 0
        session['conversation_history'] = []
        
        thema_id = '1_grundlagen'
        thema_info = THEMEN[thema_id]
        erstes_konzept = thema_info['konzepte'][0]
        
        # Erste Tutor-Nachricht
        start_prompt = f"""Thema: {thema_info['name']}
Erstes Konzept: {erstes_konzept}

Der Schüler heißt {name} und startet gerade.

Begrüße ihn kurz und beginne mit einer Frage, um sein VORWISSEN zu diesem Konzept zu erkunden.
Sei freundlich und motivierend!

Antworte im JSON-Format."""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
                {"role": "user", "content": start_prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        # Parse Response
        antwort_text = response.choices[0].message.content.strip()
        antwort_text = antwort_text.replace('```json', '').replace('```', '').strip()
        antwort = json.loads(antwort_text)
        
        # Conversation History speichern
        session['conversation_history'] = [
            {"role": "assistant", "content": antwort['nachricht']}
        ]
        
        response_data = {
            'success': True,
            'thema': thema_info['name'],
            'nachricht': antwort['nachricht'],
            'konzept': erstes_konzept
        }
        
        # Bild hinzufügen falls KI es entschieden hat
        if antwort.get('zeige_bild') and antwort.get('bild_thema'):
            bild_info = hole_bild(thema_id, antwort['bild_thema'])
            if bild_info:
                response_data['bild'] = bild_info
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Fehler in /start: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/chat', methods=['POST'])
def chat():
    """Führt den Dialog mit dem Schüler"""
    try:
        data = request.json
        schueler_nachricht = data.get('nachricht', '').strip()
        
        if not schueler_nachricht:
            return jsonify({'success': False, 'error': 'Bitte Nachricht eingeben'}), 400
        
        aktuelles_thema = session.get('aktuelles_thema', '1_grundlagen')
        thema_info = THEMEN[aktuelles_thema]
        konzept_index = session.get('aktuelles_konzept_index', 0)
        aktuelles_konzept = thema_info['konzepte'][konzept_index]
        
        # Conversation History holen
        conversation_history = session.get('conversation_history', [])
        
        # Schüler-Nachricht hinzufügen
        conversation_history.append({
            "role": "user",
            "content": schueler_nachricht
        })
        
        # Verfügbare Bilder für dieses Thema auflisten
        verfuegbare_bilder = []
        if aktuelles_thema in BILDER:
            for bild_id in BILDER[aktuelles_thema].keys():
                verfuegbare_bilder.append(bild_id)
        
        # Dialog-Prompt
        dialog_prompt = f"""Thema: {thema_info['name']}
Aktuelles Konzept: {aktuelles_konzept}

Verfügbare Bilder für dieses Thema: {', '.join(verfuegbare_bilder)}

Führe den Dialog weiter. Denke daran:
- KEINE direkten Antworten geben
- Durch FRAGEN und HINWEISE leiten
- Falls ein Bild hilft, sage "Schau dir mal das Bild zu [Thema] an" und setze zeige_bild: true
- Setze konzept_verstanden: true nur wenn der Schüler das Konzept WIRKLICH verstanden hat

Antworte im JSON-Format."""

        # OpenAI mit vollständiger Conversation History
        messages = [{"role": "system", "content": TUTOR_SYSTEM_PROMPT}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": dialog_prompt})
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=400,
            temperature=0.7
        )
        
        # Parse Response
        antwort_text = response.choices[0].message.content.strip()
        antwort_text = antwort_text.replace('```json', '').replace('```', '').strip()
        antwort = json.loads(antwort_text)
        
        # Tutor-Antwort zur History hinzufügen
        conversation_history.append({
            "role": "assistant",
            "content": antwort['nachricht']
        })
        session['conversation_history'] = conversation_history
        
        # Punkte vergeben (kontinuierlich)
        session['punkte'] = session.get('punkte', 0) + 2
        
        response_data = {
            'success': True,
            'nachricht': antwort['nachricht'],
            'punkte': session['punkte'],
            'konzept': aktuelles_konzept
        }
        
        # Bild hinzufügen falls KI es entschieden hat
        if antwort.get('zeige_bild') and antwort.get('bild_thema'):
            bild_info = hole_bild(aktuelles_thema, antwort['bild_thema'])
            if bild_info:
                response_data['bild'] = bild_info
        
        # Wenn Konzept verstanden → nächstes Konzept
        if antwort.get('konzept_verstanden'):
            neuer_index = konzept_index + 1
            if neuer_index < len(thema_info['konzepte']):
                session['aktuelles_konzept_index'] = neuer_index
                naechstes_konzept = thema_info['konzepte'][neuer_index]
                response_data['neues_konzept'] = naechstes_konzept
                response_data['nachricht'] += f"\n\n✅ Super! Lass uns zum nächsten Thema gehen: {naechstes_konzept}"
            else:
                response_data['thema_abgeschlossen'] = True
                response_data['nachricht'] += "\n\n🎉 Fantastisch! Du hast alle Konzepte dieses Themas verstanden!"
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Fehler in /chat: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/thema_wechseln', methods=['POST'])
def thema_wechseln():
    """Wechselt das Thema"""
    try:
        data = request.json
        thema_id = data.get('thema_id', '1_grundlagen')
        
        if thema_id not in THEMEN:
            return jsonify({'success': False, 'error': 'Ungültiges Thema'}), 400
        
        thema_info = THEMEN[thema_id]
        session['aktuelles_thema'] = thema_id
        session['aktuelles_konzept_index'] = 0
        session['conversation_history'] = []
        
        erstes_konzept = thema_info['konzepte'][0]
        
        # Neue Intro-Nachricht
        intro_prompt = f"""Thema: {thema_info['name']}
Erstes Konzept: {erstes_konzept}

Der Schüler wechselt zu einem neuen Thema.

Begrüße ihn kurz für dieses neue Thema und erkunde sein Vorwissen zum ersten Konzept.

Antworte im JSON-Format."""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
                {"role": "user", "content": intro_prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        antwort_text = response.choices[0].message.content.strip()
        antwort_text = antwort_text.replace('```json', '').replace('```', '').strip()
        antwort = json.loads(antwort_text)
        
        session['conversation_history'] = [
            {"role": "assistant", "content": antwort['nachricht']}
        ]
        
        response_data = {
            'success': True,
            'thema': thema_info['name'],
            'nachricht': antwort['nachricht'],
            'konzept': erstes_konzept
        }
        
        if antwort.get('zeige_bild') and antwort.get('bild_thema'):
            bild_info = hole_bild(thema_id, antwort['bild_thema'])
            if bild_info:
                response_data['bild'] = bild_info
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Fehler in /thema_wechseln: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def hole_bild(thema_id, bild_id):
    """Holt ein spezifisches Bild für ein Thema"""
    if thema_id in BILDER and bild_id in BILDER[thema_id]:
        bild_info = BILDER[thema_id][bild_id]
        return {
            'datei': bild_info['datei'],
            'beschreibung': bild_info['beschreibung'],
            'url': f'/static/{bild_info["datei"]}'
        }
    return None


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)