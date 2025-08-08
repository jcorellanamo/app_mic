"""
Streamlit app para extraer datos de MIC de un PDF y exportarlos a Excel.
El archivo Excel tendrá el mismo nombre (cambiando la extensión) que el PDF subido.
Título visible: «WINCENTCAR »
"""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

import pandas as pd
import pdfplumber
import streamlit as st

# ---------------------------------------------------------------------------
# Configuración de la página
# ---------------------------------------------------------------------------
st.set_page_config(page_title="WINCENTCAR ", page_icon="🚢", layout="centered")
st.title("WINCENTCAR ")

# ---------------------------------------------------------------------------
# Utilidades de regex y limpieza
# ---------------------------------------------------------------------------
UPPER_NAME_RE = re.compile(r"^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ ]{4,}$")
PATENTE_RE = re.compile(r"^(?:[A-Z]{2,}\d{3,}|\d{2,}[A-Z]{2,}|[A-Z0-9-]{5,10})$")


def clean(txt: str) -> str:
    return " ".join(txt.split()).strip(" :;.-")

# ---------------------------------------------------------------------------
# Funciones de extracción de datos
# ---------------------------------------------------------------------------

def find_patente(lines: list[str]) -> str | None:
    for i, ln in enumerate(lines):
        if re.search(r"Placa\s+del\s+cam[íi]on|Placa\s+do\s+caminh", ln, re.IGNORECASE):
            for nl in lines[i + 1 : i + 6]:
                for token in re.findall(r"[A-Z0-9-]+", nl):
                    if token.upper() not in {"COD", "NIT", "CI", "DNI"} and PATENTE_RE.match(token):
                        return token
            break
    return None


def find_dni_nombre(lines: list[str]) -> tuple[str | None, str | None]:
    for i, ln in enumerate(lines):
        if re.search(r"\b(?:CI|DNI)\b", ln, re.IGNORECASE):
            mnum = re.search(r"(?:CI|DNI)[\s.:]*([0-9.]+)", ln, re.IGNORECASE)
            dni = mnum.group(1) if mnum else None
            for nl in lines[i + 1 : i + 6]:
                cand = clean(nl)
                if cand and UPPER_NAME_RE.match(cand) and len(cand.split()) >= 2:
                    return dni, cand
            return dni, None
    return None, None


def extract_destino(text: str) -> str | None:
    m = re.search(r"8\s+Ciudad y país de destino final[^\n]*\n\s*(.+)", text, re.IGNORECASE)
    if not m:
        return None
    raw = clean(m.group(1))
    raw = re.sub(r"^COD/NIT\s*\d+\s*", "", raw, flags=re.IGNORECASE)
    return clean(raw.split("-")[0])


def parse_fields(text: str) -> dict:
    lines = [clean(l) for l in text.splitlines()]
    data: dict[str, str | None] = {}

    # Empresa
    m = re.search(r"1\s+Nombre y domicilio[^\n]*\n\s*(.+)", text, re.IGNORECASE)
    data["empresa"] = clean(m.group(1)) if m else None

    # Patente
    data["patente"] = find_patente(lines)

    # Aduana
    m = re.search(r"7\s+Aduana[^\n]*\n\s*(.+)", text, re.IGNORECASE)
    data["aduana"] = clean(m.group(1)) if m else None

    # Destino
    data["destino"] = extract_destino(text)

    # MIC
    m = re.search(r"N[º°]?\s*MIC[^\d]*(\w+)", text, re.IGNORECASE) or re.search(
        r"MIC Electr[oó]nico\s+(\w+)", text, re.IGNORECASE
    )
    data["mic"] = clean(m.group(1)) if m else None

    # DNI + Nombre conductor
    dni, nombre = find_dni_nombre(lines)
    data["dni"] = dni
    data["nombre_conductor"] = nombre

    return data


def extract_chasis(text: str) -> list[str]:
    return [c.strip() for c in re.findall(r"CH:([A-Z0-9]+)", text)]


def process_pdf(file) -> pd.DataFrame:
    with pdfplumber.open(file) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    fields = parse_fields(text)
    chasis_list = extract_chasis(text) or [None]

    rows = [{"chasis": ch, **fields} for ch in chasis_list]
    return pd.DataFrame(rows, columns=[
        "chasis",
        "empresa",
        "patente",
        "nombre_conductor",
        "dni",
        "destino",
        "mic",
        "aduana",
    ])

# ---------------------------------------------------------------------------
# Interfaz Streamlit
# ---------------------------------------------------------------------------

with st.form(key="extract_form", clear_on_submit=True):
    uploaded_file = st.file_uploader("Adjunta tu archivo PDF MIC", type=["pdf"], key="mic_pdf")
    submitted = st.form_submit_button("Ejecutar")

if submitted:
    if uploaded_file is None:
        st.error("⚠️ Debes adjuntar un archivo PDF.")
    else:
        try:
            df = process_pdf(uploaded_file)
            base_name = Path(uploaded_file.name).stem
            excel_name = f"{base_name}.xlsx"

            with BytesIO() as buffer:
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False)
                buffer.seek(0)
                st.download_button(
                    label="Descargar Excel",
                    data=buffer,
                    file_name=excel_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            st.success("✅ Extracción completada.")
        except Exception as err:
            st.error(f"❌ Error al procesar el PDF: {err}")