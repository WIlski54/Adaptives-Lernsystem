from flask import Flask, render_template, request, jsonify, session
import openai
import os
import secrets
from image_resources import finde_passendes_bild

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# OpenAI API Key
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Themen-Definitionen
THEMEN = {
    '1_grundlagen': {
        'name': 'DNA-Grundlagen',
        'beschreibung': 'Aufbau und Struktur der DNA'
    },
    '2_aufbau': {
        'name': 'Chromosomen und Gene',
        'beschreibung': 'Von Chromosomen zu Genen'
    },
    '3_replikation': {
        'name': 'DNA-Replikation',
        'beschreibung': 'Verdopplung der DNA'
    },
    '4_vererbung': {
        'name': 'Vererbung und Merkmale',
        'beschreibung': 'Wie Merkmale vererbt werden'
    }
}

# System-Prompt für OpenAI
SYSTEM_PROMPT = """Du bist ein geduldiger, freundlicher Biologie-Tutor für Schüler der Klassen 9-10.

WICHTIGE REGELN:
1. Sei SEHR STRENG bei wissenschaftlichen Begriffen - akzeptiere nur 100% korrekte Schreibweisen
   - "Cytosin" ist korrekt, "Cytosil" oder "Cytozin" sind FALSCH
   - "Thymin" ist korrekt, "Timin" ist FALSCH
   
2. Stelle adaptive Fragen basierend auf dem Verständnis des Schülers:
   - Bei gutem Verständnis: Stelle schwierigere Fragen
   - Bei mittlerem Verständnis: Bleibe auf dem Level
   - Bei Schwierigkeiten: Stelle einfachere Fragen und erkläre mehr

3. Gib konstruktives Feedback:
   - Bei richtigen Antworten: Kurzes Lob + nächste Frage
   - Bei teilweise richtigen Antworten: Was war gut + was fehlt
   - Bei falschen Antworten: Korrektur + Erklärung

4. Passe die Schwierigkeit an das Niveau an"""


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
        session['fragen_historie'] = []
        session['schwierigkeit'] = 'mittel'
        
        # Erste Frage generieren
        thema_id = '1_grundlagen'
        thema_info = THEMEN[thema_id]
        
        prompt = f"""Thema: {thema_info['name']} - {thema_info['beschreibung']}

Erstelle eine erste Frage auf MITTLEREM Niveau für einen Schüler der 9./10. Klasse.
Die Frage soll das Grundverständnis testen.

Antworte NUR mit der Frage, ohne zusätzlichen Text."""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        erste_frage = response.choices[0].message.content.strip()
        session['aktuelle_frage'] = erste_frage
        session['fragen_historie'].append({
            'frage': erste_frage,
            'thema': thema_id
        })
        
        # BILDINTEGRATION: Suche passendes Bild
        bild_info = finde_passendes_bild(erste_frage, thema_id)
        
        response_data = {
            'success': True,
            'thema': thema_info['name'],
            'frage': erste_frage
        }
        
        if bild_info:
            response_data['bild'] = bild_info
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Fehler in /start: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/antworten', methods=['POST'])
def antworten():
    """Bewertet die Antwort und generiert die nächste Frage"""
    try:
        data = request.json
        antwort = data.get('antwort', '').strip()
        
        if not antwort:
            return jsonify({'success': False, 'error': 'Bitte Antwort eingeben'}), 400
        
        aktuelle_frage = session.get('aktuelle_frage', '')
        aktueller_schwierigkeit = session.get('schwierigkeit', 'mittel')
        aktuelles_thema = session.get('aktuelles_thema', '1_grundlagen')
        thema_info = THEMEN[aktuelles_thema]
        
        # Antwort bewerten
        bewertungs_prompt = f"""Frage: {aktuelle_frage}

Schüler-Antwort: {antwort}

Bewerte die Antwort und gib ein JSON zurück:
{{
    "verständnis": "gut" oder "mittel" oder "hilfe",
    "feedback": "Kurzes Feedback (1-2 Sätze)",
    "erklärung": "Erklärung falls verständnis nicht 'gut' ist, sonst null",
    "punkte": 10 bei "gut", 5 bei "mittel", 0 bei "hilfe"
}}

Antworte NUR mit dem JSON, nichts anderes!"""

        bewertung_response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": bewertungs_prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        # JSON parsen
        bewertung_text = bewertung_response.choices[0].message.content.strip()
        bewertung_text = bewertung_text.replace('```json', '').replace('```', '').strip()
        
        import json
        bewertung = json.loads(bewertung_text)
        
        verständnis = bewertung.get('verständnis', 'mittel')
        feedback_text = bewertung.get('feedback', '')
        erklärung = bewertung.get('erklärung', None)
        punkte_gewinn = bewertung.get('punkte', 0)
        
        # Punkte aktualisieren
        session['punkte'] = session.get('punkte', 0) + punkte_gewinn
        
        # Schwierigkeit anpassen
        if verständnis == 'gut':
            neue_schwierigkeit = 'schwer'
        elif verständnis == 'hilfe':
            neue_schwierigkeit = 'leicht'
        else:
            neue_schwierigkeit = aktueller_schwierigkeit
        
        session['schwierigkeit'] = neue_schwierigkeit
        
        # Nächste Frage generieren (ADAPTIV!)
        naechste_frage_prompt = f"""Thema: {thema_info['name']}

Bisheriges Verständnis: {verständnis}
Neue Schwierigkeit: {neue_schwierigkeit}

Generiere die NÄCHSTE Frage für diesen Schüler.

- Bei 'schwer': Stelle eine anspruchsvolle Frage (Transfer, Zusammenhänge)
- Bei 'mittel': Stelle eine normale Frage (Verständnis)
- Bei 'leicht': Stelle eine einfache Frage (Grundwissen)

Antworte NUR mit der Frage, ohne zusätzlichen Text."""

        naechste_frage_response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": naechste_frage_prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        nächste_frage = naechste_frage_response.choices[0].message.content.strip()
        session['aktuelle_frage'] = nächste_frage
        
        # BILDINTEGRATION: Suche passendes Bild zur nächsten Frage
        bild_info = finde_passendes_bild(nächste_frage, aktuelles_thema)
        
        response_data = {
            'success': True,
            'feedback': feedback_text,
            'verständnis': verständnis,
            'erklärung': erklärung,
            'nächste_frage': nächste_frage,
            'punkte': session['punkte']
        }
        
        if bild_info:
            response_data['bild'] = bild_info
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Fehler in /antworten: {str(e)}")
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
        session['schwierigkeit'] = 'mittel'  # Reset Schwierigkeit
        
        # Neue erste Frage für das Thema
        prompt = f"""Thema: {thema_info['name']} - {thema_info['beschreibung']}

Erstelle eine erste Frage auf MITTLEREM Niveau für einen Schüler der 9./10. Klasse.

Antworte NUR mit der Frage, ohne zusätzlichen Text."""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        neue_frage = response.choices[0].message.content.strip()
        session['aktuelle_frage'] = neue_frage
        
        # BILDINTEGRATION: Suche passendes Bild
        bild_info = finde_passendes_bild(neue_frage, thema_id)
        
        response_data = {
            'success': True,
            'thema': thema_info['name'],
            'frage': neue_frage
        }
        
        if bild_info:
            response_data['bild'] = bild_info
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Fehler in /thema_wechseln: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)