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
        ],
        'quellen': [
            'https://www.biologie-schule.de/dna.php',
            'https://www.lernhelfer.de/schuelerlexikon/biologie/artikel/desoxyribonucleinsaeure-dna'
        ]
    },
    '2_aufbau': {
        'name': 'Chromosomen und Gene',
        'beschreibung': 'Von Chromosomen zu Genen',
        'konzepte': [
            'Chromosomenstruktur',
            'Gene als DNA-Abschnitte',
            'Zellkern und Chromatin'
        ],
        'quellen': [
            'https://www.biologie-schule.de/chromosom.php',
            'https://www.lernhelfer.de/schuelerlexikon/biologie/artikel/gene-und-chromosomen'
        ]
    },
    '3_replikation': {
        'name': 'DNA-Replikation',
        'beschreibung': 'Verdopplung der DNA',
        'konzepte': [
            'Semikonservative Replikation',
            'Enzyme (Helikase, Polymerase)',
            'Replikationsgabel'
        ],
        'quellen': [
            'https://www.biologie-schule.de/replikation.php',
            'https://www.lernhelfer.de/schuelerlexikon/biologie/artikel/replikation-der-dna'
        ]
    },
    '4_vererbung': {
        'name': 'Vererbung und Merkmale',
        'beschreibung': 'Wie Merkmale vererbt werden',
        'konzepte': [
            'Phänotyp und Genotyp',
            'Allele (dominant, rezessiv)',
            'Mendelsche Regeln'
        ],
        'quellen': [
            'https://www.biologie-schule.de/mendelsche-regeln.php',
            'https://www.lernhelfer.de/schuelerlexikon/biologie/artikel/vererbung'
        ]
    }
}

# Verbesserter System-Prompt mit Frustrationserkennung
TUTOR_SYSTEM_PROMPT = """Du bist ein geduldiger, einfühlsamer sokratischer Biologie-Tutor für Schüler der Klassen 9-10.

DEINE KERN-PHILOSOPHIE:
- Du gibst NIEMALS direkt die komplette Antwort
- Du führst durch GESTUFTE HILFE zum Verständnis
- Du erkennst FRUSTRATION und reagierst darauf
- Du bist streng bei wissenschaftlichen Begriffen (z.B. "Cytosin" nicht "Cytosil")

GESTUFTE HILFE-STRATEGIE:
1. ERSTE HILFE (Subtiler Hinweis):
   - "Überlege mal, das Wort beginnt mit..."
   - "Denk an die Struktur..."
   
2. ZWEITE HILFE (Konkreter Hinweis):
   - "Es ist eine der Pyrimidin-Basen..."
   - "Schau dir die chemische Gruppe an..."
   
3. DRITTE HILFE (Visuell):
   - "Lass mich dir ein Bild zeigen..."
   - Setze zeige_bild: true
   
4. VIERTE HILFE (Umformulierung):
   - "Lass uns das Konzept anders angehen..."
   - Erkläre es neu aus anderer Perspektive

FRUSTRATIONSERKENNUNG:
Erkenne diese Signale:
- "Ich weiß es nicht"
- "Kannst du mir sagen..."
- "Wo kann ich das nachgucken"
- Mehrere falsche Versuche
- Ungeduld/Resignation

REAKTION AUF FRUSTRATION:
- Sei EMPATHISCH: "Ich verstehe, das ist knifflig!"
- Gib GEZIELTE HILFE: Nächste Stufe der Hilfe
- NIEMALS direkt die Lösung geben
- Bei 3+ Versuchen ohne Fortschritt: Biete an, das Konzept neu zu erklären

BILDER EINSETZEN:
- Sage explizit: "Schau dir dieses Bild an..." oder "Ich zeige dir was..."
- Nur ab DRITTER HILFE-Stufe
- Setze zeige_bild: true und bild_thema: "[bild_id]"

RECHERCHEQUELLEN:
- NIEMALS sofort bei Fragen geben
- NUR wenn konzept_verstanden: true → gebe_quellen: true
- ODER bei anhaltendem Frust (3+ Versuche): gebe_quellen: true mit Hinweis "für später"

DIALOG-PRINZIPIEN:
- Maximal 2-3 Sätze pro Antwort
- Flexibel, nicht Schema F
- Baue auf Vorwissen auf
- Motiviere und ermutige
- Mehrere Dialog-Runden pro Konzept

ANTWORT-FORMAT (JSON):
{
    "nachricht": "Deine empathische Antwort (2-3 Sätze)",
    "hilfe_stufe": 1-4 (Welche Hilfe-Stufe verwendest du?),
    "zeige_bild": true/false,
    "bild_thema": "basen" oder null,
    "konzept_verstanden": true/false,
    "gebe_quellen": true/false,
    "frustration_erkannt": true/false
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
        session['versuche_aktuelles_konzept'] = 0
        
        thema_id = '1_grundlagen'
        thema_info = THEMEN[thema_id]
        erstes_konzept = thema_info['konzepte'][0]
        
        # Erste Tutor-Nachricht
        start_prompt = f"""Thema: {thema_info['name']}
Erstes Konzept: {erstes_konzept}

Der Schüler heißt {name} und startet gerade.

Begrüße ihn kurz und beginne mit einer offenen Frage, um sein VORWISSEN zu erkunden.
Sei freundlich, motivierend und ermutigend!

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
        versuche = session.get('versuche_aktuelles_konzept', 0)
        
        # Versuche erhöhen
        session['versuche_aktuelles_konzept'] = versuche + 1
        
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
        
        # Dialog-Prompt mit Kontext
        dialog_prompt = f"""Thema: {thema_info['name']}
Aktuelles Konzept: {aktuelles_konzept}
Anzahl Versuche zu diesem Konzept: {versuche + 1}

Verfügbare Bilder: {', '.join(verfuegbare_bilder)}

WICHTIG:
- Der Schüler hat bereits {versuche + 1} Versuche gemacht
- Wenn Versuche >= 3: Erkenne FRUSTRATION und gib mehr Hilfe
- Verwende GESTUFTE HILFE (Stufe 1 → 2 → 3 → 4)
- NIEMALS die komplette Antwort geben

Führe den Dialog empathisch weiter.

Antworte im JSON-Format."""

        # OpenAI mit vollständiger Conversation History
        messages = [{"role": "system", "content": TUTOR_SYSTEM_PROMPT}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": dialog_prompt})
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=500,
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
        
        # Quellen hinzufügen falls KI es entschieden hat
        if antwort.get('gebe_quellen'):
            response_data['quellen'] = thema_info.get('quellen', [])
            if antwort.get('konzept_verstanden'):
                response_data['nachricht'] += "\n\n📚 Hier sind passende Quellen zum Vertiefen:\n" + "\n".join(f"• {q}" for q in thema_info.get('quellen', []))
            else:
                response_data['nachricht'] += "\n\n📚 Hier sind hilfreiche Quellen für später:\n" + "\n".join(f"• {q}" for q in thema_info.get('quellen', []))
        
        # Wenn Konzept verstanden → nächstes Konzept
        if antwort.get('konzept_verstanden'):
            session['versuche_aktuelles_konzept'] = 0  # Reset
            neuer_index = konzept_index + 1
            if neuer_index < len(thema_info['konzepte']):
                session['aktuelles_konzept_index'] = neuer_index
                naechstes_konzept = thema_info['konzepte'][neuer_index]
                response_data['neues_konzept'] = naechstes_konzept
                response_data['nachricht'] += f"\n\n✅ Super! Lass uns zum nächsten Thema gehen: {naechstes_konzept}"
            else:
                response_data['thema_abgeschlossen'] = True
                response_data['nachricht'] += "\n\n🎉 Fantastisch! Du hast alle Konzepte dieses Themas verstanden!"
                # Quellen am Ende
                if not antwort.get('gebe_quellen'):
                    response_data['nachricht'] += "\n\n📚 Zum Vertiefen:\n" + "\n".join(f"• {q}" for q in thema_info.get('quellen', []))
        
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
        session['versuche_aktuelles_konzept'] = 0
        
        erstes_konzept = thema_info['konzepte'][0]
        
        # Neue Intro-Nachricht
        intro_prompt = f"""Thema: {thema_info['name']}
Erstes Konzept: {erstes_konzept}

Der Schüler wechselt zu einem neuen Thema.

Begrüße ihn kurz für dieses neue Thema und erkunde sein Vorwissen zum ersten Konzept.
Sei motivierend!

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