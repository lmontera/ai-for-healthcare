"""Default catalog of document categories for the clinical classifier."""

DEFAULT_CATEGORIES: list[dict] = [
    {
        "key": "lab_report",
        "label": "Referto di laboratorio",
        "description": "Esami del sangue, urine, biochimica, ematologia, sierologia, microbiologia.",
    },
    {
        "key": "imaging_report",
        "label": "Referto strumentale / di imaging",
        "description": "Radiografia, ecografia, TC, RMN, mammografia, OCT, fluorangiografia, ECG, holter.",
    },
    {
        "key": "specialist_visit",
        "label": "Visita specialistica",
        "description": "Referto di una visita specialistica (oculistica, cardiologica, dermatologica, ecc.) con anamnesi, esame obiettivo, diagnosi e terapia.",
    },
    {
        "key": "discharge_letter",
        "label": "Lettera di dimissione ospedaliera",
        "description": "Documento di dimissione da ricovero, contiene motivo del ricovero, decorso, terapie ed indicazioni alla dimissione.",
    },
    {
        "key": "prescription",
        "label": "Prescrizione / Ricetta medica",
        "description": "Ricetta SSN/bianca con farmaci, dosaggi, posologia.",
    },
    {
        "key": "clinical_record",
        "label": "Cartella clinica / Anamnesi",
        "description": "Documenti di raccolta anamnestica e dati clinici, schede paziente.",
    },
    {
        "key": "informed_consent",
        "label": "Consenso informato",
        "description": "Modulo di consenso del paziente alla procedura, intervento o trattamento dati.",
    },
    {
        "key": "vaccination_certificate",
        "label": "Certificato vaccinale",
        "description": "Documento attestante una o più vaccinazioni.",
    },
    {
        "key": "medical_certificate",
        "label": "Certificato medico",
        "description": "Certificati di idoneità, malattia, esenzione, invalidità.",
    },
    {
        "key": "other",
        "label": "Altro / Non identificabile",
        "description": "Documento che non rientra chiaramente in nessuna delle altre categorie.",
    },
]
