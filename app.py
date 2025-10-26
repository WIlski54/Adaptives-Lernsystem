from flask import Flask, render_template, request, jsonify, session
import os
import json
from datetime import datetime
from openai import OpenAI

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dna-learning-secret-key-change-in-production')

# OpenAI API Client
client = OpenAI(
    api_key=os.environ.get('OPENAI_API_KEY', '')
)

# DNA-Curriculum für Klasse 9/10
CURRICULUM = {
    "1_grundlagen": {
        "titel": "DNA-Grundlagen",
        "themen": ["Nukleotide", "Doppelhelix-Struktur", "Basenpaarung (A-T, G-C)"],
        "schwierigkeit": 1
    },
    "2_aufbau": {
        "titel": "Chromosomen & Gene",
        "themen": ["Chromosomen im Zellkern", "Gene als DNA-Abschnitte", "Erbinformation"],
        "schwierigkeit": 2
    },
    "3_replikation": {
        "titel": "DNA-Verdopplung",
        "themen": ["Replikation vor Zellteilung", "Identische Kopien", "Enzyme"],
        "schwierigkeit": 3
    },
    "4_vererbung": {
        "titel": "Vererbung & Merkmale",
        "themen": ["Mendel-Regeln (vereinfacht)", "Allele", "Dominant/Rezessiv"],
        "schwierigkeit": 2
    }
}

def get_system_prompt():
    """Erstellt den System-Prompt für OpenAI"""
    return """Du bist ein geduldiger, motivierender Biologielehrer für die Klassen 9 und 10.

WICHTIGE REGELN:
- Erkläre auf Niveau Sekundarstufe I (KEINE Oberstufen-Konzepte!)
- Verwende einfache, klare Sprache
- Nutze Alltagsbeispiele und Analogien
- Sei ermutigend und geduldig
- Passe Erklärungen an das Verständnis des Schülers an
- Bei falschen Antworten: Erkläre WARUM etwas falsch ist, dann leite zur richtigen Antwort

KRITISCH - FACHBEGRIFFE:
- Achte SEHR GENAU auf korrekte Schreibweise von Fachbegriffen!
- Bei falscher Schreibweise (z.B. "Cytosil" statt "Cytosin"): 
  * Bewerte als "mittel" statt "gut"
  * Korrigiere die Schreibweise im Feedback
  * Erkläre: "Du meinst Cytosin (mit -n am Ende). Achte auf die korrekte Schreibweise!"
- Wichtige Begriffe: Adenin, Guanin, Cytosin, Thymin, Nukleotid, Chromosom, Gen, Allel, etc.

THEMA: DNA als zentraler Baustein der Vererbung

ABLAUF:
1. Stelle eine passende Frage zum aktuellen Thema
2. Bewerte die Antwort des Schülers
3. Gib konstruktives Feedback
4. Bei Bedarf: Erkläre das Konzept neu oder tiefer
5. Stelle die nächste Frage (angepasst an Verständnisniveau)

Antworte IMMER im JSON-Format:
{
    "feedback": "Dein Feedback zur Antwort",
    "erklärung": "Zusätzliche Erklärung (wenn nötig)",
    "nächste_frage": "Die nächste Frage",
    "schwierigkeit": 1-4,
    "verständnis_niveau": "gut/mittel/braucht_hilfe"
}"""

def call_openai(schüler_historie, aktuelles_thema, schüler_antwort=None):
    """Ruft OpenAI API auf und gibt strukturierte Antwort zurück"""
    
    # Baue Conversation History auf
    messages = [
        {
            "role": "system",
            "content": get_system_prompt()
        }
    ]
    
    # Füge bisherigen Verlauf hinzu
    for eintrag in schüler_historie:
        if eintrag.get('typ') == 'frage':
            messages.append({
                "role": "assistant",
                "content": eintrag['inhalt']
            })
        elif eintrag.get('typ') == 'antwort':
            messages.append({
                "role": "user",
                "content": eintrag['inhalt']
            })
    
    # Aktuelle Schülerantwort
    if schüler_antwort:
        user_message = f"""THEMA: {aktuelles_thema['titel']}

Schülerantwort: {schüler_antwort}

Bewerte die Antwort, gib Feedback und stelle die nächste Frage."""
    else:
        # Erste Frage zum Thema
        user_message = f"""THEMA: {aktuelles_thema['titel']}
Unterthemen: {', '.join(aktuelles_thema['themen'])}

Stelle die erste Einstiegsfrage zu diesem Thema."""
    
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Günstiger und schnell, alternativ: "gpt-4o"
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
            response_format={"type": "json_object"}  # Erzwingt JSON-Ausgabe
        )
        
        # Parse JSON response
        response_text = response.choices[0].message.content
        
        # Entferne mögliche Markdown-Backticks
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        
        result = json.loads(response_text)
        return result
        
    except Exception as e:
        print(f"Fehler bei OpenAI API: {e}")
        # Fallback
        return {
            "feedback": "Entschuldigung, es gab einen technischen Fehler. Versuche es bitte nochmal.",
            "erklärung": "",
            "nächste_frage": "Lass uns nochmal von vorne beginnen.",
            "schwierigkeit": 1,
            "verständnis_niveau": "mittel"
        }

@app.route('/')
def index():
    """Startseite mit Schüler-Login"""
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_learning():
    """Startet eine neue Lernsession"""
    data = request.json
    schüler_name = data.get('name', 'Schüler')
    
    # Initialisiere Session
    session['schüler_name'] = schüler_name
    session['aktuelles_thema'] = '1_grundlagen'
    session['historie'] = []
    session['start_zeit'] = datetime.now().isoformat()
    session['punkte'] = 0
    
    # Hole erstes Thema
    thema = CURRICULUM['1_grundlagen']
    
    # Generiere erste Frage
    antwort = call_openai([], thema)
    
    # Speichere in Historie
    session['historie'] = [{
        'typ': 'frage',
        'inhalt': antwort['nächste_frage'],
        'zeit': datetime.now().isoformat()
    }]
    session.modified = True
    
    return jsonify({
        'success': True,
        'thema': thema['titel'],
        'frage': antwort['nächste_frage']
    })

@app.route('/antworten', methods=['POST'])
def antworten():
    """Verarbeitet Schülerantwort und gibt Feedback + neue Frage"""
    data = request.json
    antwort = data.get('antwort', '')
    
    if not antwort.strip():
        return jsonify({'error': 'Bitte gib eine Antwort ein.'}), 400
    
    # Hole aktuelle Session-Daten
    historie = session.get('historie', [])
    aktuelles_thema_id = session.get('aktuelles_thema', '1_grundlagen')
    thema = CURRICULUM[aktuelles_thema_id]
    
    # Speichere Antwort in Historie
    historie.append({
        'typ': 'antwort',
        'inhalt': antwort,
        'zeit': datetime.now().isoformat()
    })
    
    # Rufe OpenAI auf
    openai_response = call_openai(historie, thema, antwort)
    
    # Speichere neue Frage in Historie
    historie.append({
        'typ': 'frage',
        'inhalt': openai_response['nächste_frage'],
        'zeit': datetime.now().isoformat(),
        'verständnis': openai_response['verständnis_niveau']
    })
    
    # Update Session
    session['historie'] = historie
    
    # Punkte vergeben
    if openai_response['verständnis_niveau'] == 'gut':
        session['punkte'] = session.get('punkte', 0) + 10
    elif openai_response['verständnis_niveau'] == 'mittel':
        session['punkte'] = session.get('punkte', 0) + 5
    
    session.modified = True
    
    return jsonify({
        'success': True,
        'feedback': openai_response['feedback'],
        'erklärung': openai_response.get('erklärung', ''),
        'nächste_frage': openai_response['nächste_frage'],
        'punkte': session.get('punkte', 0),
        'verständnis': openai_response['verständnis_niveau']
    })

@app.route('/thema_wechseln', methods=['POST'])
def thema_wechseln():
    """Wechselt zu einem anderen Curriculum-Thema"""
    data = request.json
    neues_thema_id = data.get('thema_id')
    
    if neues_thema_id not in CURRICULUM:
        return jsonify({'error': 'Ungültiges Thema'}), 400
    
    session['aktuelles_thema'] = neues_thema_id
    session['historie'] = []  # Reset Historie für neues Thema
    session.modified = True
    
    thema = CURRICULUM[neues_thema_id]
    
    # Generiere erste Frage für neues Thema
    antwort = call_openai([], thema)
    
    session['historie'] = [{
        'typ': 'frage',
        'inhalt': antwort['nächste_frage'],
        'zeit': datetime.now().isoformat()
    }]
    session.modified = True
    
    return jsonify({
        'success': True,
        'thema': thema['titel'],
        'frage': antwort['nächste_frage']
    })

@app.route('/fortschritt')
def fortschritt():
    """Zeigt Lernfortschritt des Schülers"""
    historie = session.get('historie', [])
    
    # Analysiere Verständnisniveau
    verständnis_levels = [h.get('verständnis', 'mittel') for h in historie if h.get('typ') == 'frage']
    
    gut_count = verständnis_levels.count('gut')
    mittel_count = verständnis_levels.count('mittel')
    hilfe_count = verständnis_levels.count('braucht_hilfe')
    
    return jsonify({
        'schüler_name': session.get('schüler_name', ''),
        'punkte': session.get('punkte', 0),
        'fragen_beantwortet': len([h for h in historie if h.get('typ') == 'antwort']),
        'verständnis': {
            'gut': gut_count,
            'mittel': mittel_count,
            'braucht_hilfe': hilfe_count
        },
        'aktuelles_thema': CURRICULUM[session.get('aktuelles_thema', '1_grundlagen')]['titel']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
