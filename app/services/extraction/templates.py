"""Templates di questionari per specialità.

Ogni specialità ha:
- `glossary`: termini tipici della specialità (usati come `context` per il LLM)
- `questionnaires`: lista di questionari nel formato atteso da /transcription/extract
"""

QUESTIONNAIRE_TEMPLATES: dict[str, dict] = {
    "Oculistica": {
        "glossary": (
            "visus, acuità visiva, diottrie, miopia, ipermetropia, astigmatismo, "
            "presbiopia, cornea, cristallino, retina, macula, fovea, iride, pupilla, "
            "sclera, congiuntiva, coroide, nervo ottico, papilla, vitreo, camera "
            "anteriore, tonometria, pressione intraoculare, PIO, IOP, glaucoma, "
            "cataratta, retinopatia diabetica, maculopatia, degenerazione maculare, "
            "distacco di retina, FACO, IOL, LASIK, PRK, vitrectomia, blefarite, "
            "congiuntivite, uveite, cheratite, ambliopia, strabismo"
        ),
        "questionnaires": [
            {
                "id": 1,
                "name": "Anamnesi",
                "fields": [
                    {"name": "allergie", "description": "Allergie note"},
                    {"name": "motivo_visita", "description": "Motivo principale della visita"},
                    {"name": "terapia_preesistente", "description": "Terapie già in corso"},
                ],
                "existing_data": {},
            },
            {
                "id": 2,
                "name": "Esame Obiettivo Oculistico",
                "fields": [
                    {"name": "cornea_od", "description": "Aspetto cornea OD"},
                    {"name": "cristallino_od", "description": "Aspetto cristallino OD"},
                    {"name": "sfera_od", "description": "Refrazione sferica OD (diottrie)", "type": "number"},
                    {"name": "cilindro_od", "description": "Refrazione cilindrica OD (diottrie)", "type": "number"},
                    {"name": "asse_od", "description": "Asse del cilindro OD (gradi)", "type": "number"},
                    {"name": "pressione_oculare_od", "description": "Tono oculare OD (mmHg)", "type": "number"},
                    {"name": "pressione_oculare_os", "description": "Tono oculare OS (mmHg)", "type": "number"},
                ],
                "existing_data": {},
            },
            {
                "id": 3,
                "name": "Diagnosi e Terapia",
                "fields": [
                    {"name": "diagnosi", "description": "Diagnosi clinica (max 150 caratteri)"},
                    {"name": "terapia", "description": "Terapia prescritta oggi"},
                ],
                "existing_data": {},
            },
        ],
    },
    "Cardiologia": {
        "glossary": (
            "ECG, frequenza cardiaca, ritmo sinusale, fibrillazione atriale, "
            "ipertensione, infarto miocardico, angina, scompenso cardiaco, "
            "ecocardiogramma, frazione di eiezione, holter, pacemaker, troponina, BNP"
        ),
        "questionnaires": [
            {
                "id": 1,
                "name": "Anamnesi",
                "fields": [
                    {"name": "motivo_visita", "description": "Motivo della visita"},
                    {"name": "fattori_rischio", "description": "Fattori di rischio cardiovascolare"},
                    {"name": "terapia_in_atto", "description": "Terapie in corso"},
                ],
                "existing_data": {},
            },
            {
                "id": 2,
                "name": "Esame Obiettivo",
                "fields": [
                    {"name": "pa_sistolica", "description": "PA sistolica (mmHg)", "type": "number"},
                    {"name": "pa_diastolica", "description": "PA diastolica (mmHg)", "type": "number"},
                    {"name": "fc", "description": "Frequenza cardiaca (bpm)", "type": "number"},
                    {"name": "ritmo", "description": "Ritmo cardiaco"},
                    {"name": "toni", "description": "Toni cardiaci"},
                ],
                "existing_data": {},
            },
            {
                "id": 3,
                "name": "Diagnosi e Terapia",
                "fields": [
                    {"name": "diagnosi", "description": "Diagnosi"},
                    {"name": "terapia", "description": "Terapia prescritta"},
                ],
                "existing_data": {},
            },
        ],
    },
    "Generale": {
        "glossary": (
            "anamnesi, sintomi, terapia in atto, diagnosi, esame obiettivo, "
            "prescrizione, dosaggio"
        ),
        "questionnaires": [
            {
                "id": 1,
                "name": "Anamnesi",
                "fields": [
                    {"name": "allergie", "description": "Allergie note"},
                    {"name": "motivo_visita", "description": "Motivo della visita"},
                    {"name": "anamnesi_patologica", "description": "Patologie pregresse o in corso"},
                    {"name": "terapia_in_atto", "description": "Farmaci attualmente assunti"},
                ],
                "existing_data": {},
            },
            {
                "id": 2,
                "name": "Diagnosi e Terapia",
                "fields": [
                    {"name": "diagnosi", "description": "Diagnosi conclusiva"},
                    {"name": "terapia", "description": "Terapia prescritta"},
                ],
                "existing_data": {},
            },
        ],
    },
}

DEFAULT_SPECIALTY = "Oculistica"
