# image_resources.py
# Bildressourcen für das adaptive DNA-Lernsystem
# Diese Bilder werden bei passenden Fragen OPTIONAL angezeigt

"""
WICHTIG: Diese Integration verändert NICHT die adaptive Logik!
Die Bilder sind eine zusätzliche visuelle Hilfe, die angezeigt wird,
wenn eine Frage zu einem bestimmten Bild passt.
"""

# Bildverzeichnis - organisiert nach Themen
BILDER = {
    "1_grundlagen": {
        "basen": {
            "datei": "Basen.png",
            "keywords": ["basen", "adenin", "thymin", "guanin", "cytosin", "purin", "pyrimidin"],
            "beschreibung": "Die vier DNA-Basen und ihre Struktur"
        },
        "basenpaarung": {
            "datei": "Basenpaarungen.png",
            "keywords": ["basenpaarung", "paarung", "wasserstoff", "a-t", "g-c", "komplementär"],
            "beschreibung": "Komplementäre Basenpaarung mit Wasserstoffbrücken"
        },
        "nucleotid": {
            "datei": "Nucleotidstruktur.png",
            "keywords": ["nukleotid", "aufbau", "phosphat", "zucker", "desoxyribose"],
            "beschreibung": "Aufbau eines DNA-Nukleotids"
        },
        "leiter": {
            "datei": "Leitermodell.png",
            "keywords": ["leitermodell", "struktur", "strickleiter"],
            "beschreibung": "DNA-Leitermodell (vereinfachte Darstellung)"
        },
        "helix": {
            "datei": "DNA_Helix.png",
            "keywords": ["helix", "doppelhelix", "spirale", "windung"],
            "beschreibung": "Die DNA-Doppelhelix-Struktur"
        },
        "doppelhelix": {
            "datei": "Doppelhelix.png",
            "keywords": ["doppelhelix", "antiparallel", "3'", "5'"],
            "beschreibung": "Detaillierte Doppelhelix mit antiparallelen Strängen"
        }
    },
    
    "2_aufbau": {
        "chromosom": {
            "datei": "Chromosom_Aufbau.png",
            "keywords": ["chromosom", "chromatid", "zentromer", "aufbau"],
            "beschreibung": "Aufbau eines Chromosoms"
        },
        "karyogramm": {
            "datei": "Chromosomensatz.png",
            "keywords": ["chromosomensatz", "karyogramm", "diploid", "haploid", "autosomen"],
            "beschreibung": "Menschlicher Chromosomensatz"
        },
        "gen": {
            "datei": "Gen.png",
            "keywords": ["gen", "dna-abschnitt", "merkmal"],
            "beschreibung": "Ein Gen als DNA-Abschnitt"
        },
        "zellkern": {
            "datei": "Zellkern.png",
            "keywords": ["zellkern", "nucleus", "chromatin", "wo liegt"],
            "beschreibung": "Der Zellkern mit DNA"
        }
    },
    
    "3_replikation": {
        "replikation": {
            "datei": "Replikation.png",
            "keywords": ["replikation", "verdopplung", "kopie", "zellteilung"],
            "beschreibung": "Der DNA-Replikationsprozess"
        },
        "schema": {
            "datei": "Replikationsschema.png",
            "keywords": ["semikonservativ", "helikase", "polymerase", "replikationsgabel"],
            "beschreibung": "Schema der semikonservativen Replikation"
        }
    },
    
    "4_vererbung": {
        "mendel1": {
            "datei": "Mendelregel_1.png",
            "keywords": ["mendel", "uniformität", "erste regel", "f1"],
            "beschreibung": "1. Mendelsche Regel (Uniformitätsregel)"
        },
        "mendel2": {
            "datei": "Mendelregel_2.png",
            "keywords": ["spaltung", "zweite regel", "f2", "3:1"],
            "beschreibung": "2. Mendelsche Regel (Spaltungsregel)"
        },
        "erbgang": {
            "datei": "Erbgang_Beispiel.png",
            "keywords": ["erbgang", "stammbaum", "vererbung", "generationen"],
            "beschreibung": "Beispiel eines Erbgangs"
        },
        "phänotyp": {
            "datei": "Phanotyp_Genotyp.png",
            "keywords": ["phänotyp", "genotyp", "erscheinungsbild", "erbanlage"],
            "beschreibung": "Unterschied zwischen Phänotyp und Genotyp"
        },
        "allele": {
            "datei": "Allelschema.png",
            "keywords": ["allel", "homozygot", "heterozygot", "dominant", "rezessiv"],
            "beschreibung": "Schema verschiedener Allel-Kombinationen"
        }
    }
}


def finde_passendes_bild(frage_text, thema_id):
    """
    Findet ein passendes Bild zu einer Frage basierend auf Keywords.
    
    Args:
        frage_text (str): Der Text der Frage
        thema_id (str): ID des aktuellen Themas (z.B. '1_grundlagen')
    
    Returns:
        dict oder None: Bildinfo falls gefunden, sonst None
    """
    if not frage_text or not thema_id:
        return None
    
    frage_lower = frage_text.lower()
    
    # Suche nur in Bildern des aktuellen Themas
    if thema_id not in BILDER:
        return None
    
    thema_bilder = BILDER[thema_id]
    
    # Durchsuche alle Bilder des Themas
    for bild_id, bild_info in thema_bilder.items():
        # Prüfe ob Keywords in der Frage vorkommen
        for keyword in bild_info["keywords"]:
            if keyword in frage_lower:
                # Gefunden! Gib Bildinfo zurück
                return {
                    "datei": bild_info["datei"],
                    "beschreibung": bild_info["beschreibung"],
                    "url": f"/static/{bild_info['datei']}"
                }
    
    return None


def alle_bilder_für_thema(thema_id):
    """
    Gibt alle verfügbaren Bilder für ein Thema zurück.
    
    Args:
        thema_id (str): ID des Themas
    
    Returns:
        list: Liste aller Bilder des Themas
    """
    if thema_id not in BILDER:
        return []
    
    bilder_liste = []
    for bild_id, bild_info in BILDER[thema_id].items():
        bilder_liste.append({
            "datei": bild_info["datei"],
            "beschreibung": bild_info["beschreibung"],
            "url": f"/static/{bild_info['datei']}"
        })
    
    return bilder_liste