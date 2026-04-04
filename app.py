from __future__ import annotations

import csv
import os
import threading
import unicodedata
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from logic import emitir_lote_nfse

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"csv", "xls", "xlsx"}
COLUMN_ALIASES = {
    "cpf": {"cpf", "cpf_cnpj", "documento", "inscricao", "tomador_cpf"},
    "cep": {"cep", "codigo_postal", "tomador_cep"},
    "email": {"email", "e-mail", "tomador_email", "mail"},
    "telefone": {"telefone", "tel", "celular", "fone", "tomador_telefone"},
    "numero": {"numero", "num", "n", "tomador_numero"},
    "valor_servico": {"valor_servico", "valor", "valor_do_servico", "valor_servico_prestado"},
}

stats_lock = threading.Lock()
stats = {
    "processed": 0,
    "queue": 0,
    "history": [],
    "job_running": False,
    "job_total": 0,
    "job_done": 0,
    "job_failed": 0,
    "job_message": "",
}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")


def _map_columns(headers: list[str]) -> dict:
    normalized = {_normalize(h): h for h in headers if h}
    mapped = {}
    for key, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapped[key] = normalized[alias]
                break
    return mapped


def parse_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return []
        col_map = _map_columns(reader.fieldnames)
        return _rows_to_clients(reader, col_map)


def parse_excel(path: Path) -> list[dict]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("Para planilha XLS/XLSX instale: pip install pandas openpyxl xlrd") from exc

    suffix = path.suffix.lower()
    engine = None
    if suffix == ".xlsx":
        engine = "openpyxl"
    elif suffix == ".xls":
        engine = "xlrd"

    df = pd.read_excel(path, dtype=str, engine=engine)
    if df.empty:
        return []

    rows = df.fillna("").to_dict(orient="records")
    headers = list(rows[0].keys()) if rows else []
    col_map = _map_columns(headers)
    return _rows_to_clients(rows, col_map)


def _rows_to_clients(rows, col_map: dict) -> list[dict]:
    clients = []
    for row in rows:
        cpf = str(row.get(col_map.get("cpf", ""), "")).strip()
        cep = str(row.get(col_map.get("cep", ""), "")).strip()

        if not cpf or not cep:
            continue

        clients.append(
            {
                "cpf": cpf,
                "cep": cep,
                "email": str(row.get(col_map.get("email", ""), "")).strip(),
                "telefone": str(row.get(col_map.get("telefone", ""), "")).strip(),
                "numero": str(row.get(col_map.get("numero", ""), "")).strip() or "S/A",
                "valor_servico": str(row.get(col_map.get("valor_servico", ""), "")).strip(),
            }
        )
    return clients


def read_clients_from_spreadsheet(path: Path) -> list[dict]:
    ext = path.suffix.lower()
    if ext == ".csv":
        return parse_csv(path)
    if ext in {".xls", ".xlsx"}:
        return parse_excel(path)
    raise RuntimeError("Formato inválido. Use CSV, XLS ou XLSX.")


def _push_history(item: dict) -> None:
    stats["history"].insert(0, item)
    stats["history"] = stats["history"][:30]


def process_batch_in_background(spreadsheet_path: Path) -> None:
    try:
        clients = read_clients_from_spreadsheet(spreadsheet_path)
    except Exception as exc:
        with stats_lock:
            stats["job_running"] = False
            stats["job_message"] = f"Falha ao ler planilha: {exc}"
        return

    if not clients:
        with stats_lock:
            stats["job_running"] = False
            stats["job_total"] = 0
            stats["queue"] = 0
            stats["job_message"] = "Nenhum cliente válido encontrado (CPF e CEP são obrigatórios)."
        return

    with stats_lock:
        stats["job_total"] = len(clients)
        stats["job_done"] = 0
        stats["job_failed"] = 0
        stats["queue"] = len(clients)
        stats["job_message"] = "Processando lote..."

    intervalo = int(os.getenv("NFSE_INTERVALO_SEGUNDOS", "180"))

    def on_result(idx: int, total: int, client: dict, result: dict) -> None:
        status_label = "Concluído" if result.get("success") else "Falhou"
        history_item = {
            "file": f"Cliente CPF {client.get('cpf', 'N/A')}",
            "time": datetime.now().strftime("%H:%M"),
            "status": status_label,
        }

        with stats_lock:
            if result.get("success"):
                stats["processed"] += 1
            else:
                stats["job_failed"] += 1

            stats["job_done"] = idx
            stats["queue"] = max(total - idx, 0)
            _push_history(history_item)

    result = emitir_lote_nfse(
        clients,
        config={"intervalo_segundos": intervalo},
        on_result=on_result,
    )

    with stats_lock:
        stats["job_running"] = False
        stats["job_message"] = result.get("message", "Lote finalizado")


def _job_snapshot() -> dict:
    return {
        "running": stats["job_running"],
        "total": stats["job_total"],
        "donez": stats["job_done"],
        "failed": stats["job_failed"],
        "message": stats["job_message"],
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/status")
def status():
    with stats_lock:
        return jsonify(
            {
                "processed": stats["processed"],
                "queue": stats["queue"],
                "history": stats["history"][:10],
                "job": _job_snapshot(),
            }
        )


@app.post("/process")
def process_spreadsheet():
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"success": False, "message": "Arquivo não enviado."}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Use CSV, XLS ou XLSX."}), 400

    with stats_lock:
        if stats["job_running"]:
            return jsonify({"success": False, "message": "Já existe um lote em execução."}), 409

    safe_name = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_name = f"{timestamp}_{safe_name}"
    output_path = UPLOAD_DIR / final_name
    file.save(output_path)

    with stats_lock:
        stats["job_running"] = True
        stats["job_total"] = 0
        stats["job_done"] = 0
        stats["job_failed"] = 0
        stats["queue"] = 0
        stats["job_message"] = "Lote iniciado. Lendo planilha..."

    worker = threading.Thread(target=process_batch_in_background, args=(output_path,), daemon=True)
    worker.start()

    return jsonify(
        {
            "success": True,
            "message": "Lote iniciado com sucesso.",
            "job": {
                "running": True,
                "total": 0,
                "done": 0,
                "failed": 0,
                "message": "Lendo planilha...",
            },
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(debug=True, host="127.0.0.1", port=port, use_reloader=False)
