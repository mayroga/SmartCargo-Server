# config.py
import os

# Identidad de la Aplicación
APP_NAME = "AL CIELO - SmartCargo Advisory by May Roga"
VERSION = "1.0"

# Límites Técnicos Operativos
MAX_HEIGHT_PAX = 63      # Pulgadas (Bellies / Aviones de pasajeros)
MAX_HEIGHT_FRT = 96      # Pulgadas (Cargueros puros)
MAX_WEIGHT_SHORING = 150 # KG (Límite antes de requerir distribución de peso)

# Definición Técnica de ULDs (Pallets)
ULD_TYPES = {
    "PMC": {"largo": 125, "ancho": 96, "max_height": 96, "rating": 6800},
    "PAG": {"largo": 125, "ancho": 88, "max_height": 96, "rating": 4626},
    "PAJ": {"largo": 125, "ancho": 88, "max_height": 63, "rating": 4626},
    "PQA": {"largo": 125, "ancho": 96, "max_height": 96, "rating": 11340},
}

# Mensajes de Asesoría Profesional (Evitando lenguaje de auditoría)
MSJ_ASESORIA = {
    "itn_miss": "⚠ Falta ITN: Obligatorio para exportaciones > $2,500 USD (Evite retención CBP).",
    "nimf_error": "❌ Pallet sin NIMF-15: Se sugiere cambiar por pallet plástico para evitar rechazo.",
    "height_crit": "❌ Altura Crítica: Excede el límite de fuselaje de Avianca Cargo.",
    "weight_warn": "⚠ Peso Concentrado: Se sugiere uso de shoring para proteger la malla del ULD.",
    "dgr_warn": "⚠ Contenido DGR: Requiere Shipper's Declaration original firmada.",
    "overhang_crit": "⚠ Overhang: Re-estibar carga dentro de los bordes del pallet para evitar rechazo."
}
