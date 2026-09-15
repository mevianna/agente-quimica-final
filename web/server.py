"""Servidor web mínimo para a interface de chat."""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dotenv import load_dotenv  # noqa: E402

from quantum_chem_agent.agent import QuantumChemAgent, direct_mapping_result  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

INDEX_FILE = Path(__file__).with_name("index.html")
MAX_BODY_SIZE = 32_000


class ChatService:
    """Cria o agente sob demanda e serializa as mensagens da conversa."""

    def __init__(self) -> None:
        self._agent: QuantumChemAgent | None = None
        self._pending_direct_exchanges: list[tuple[str, dict[str, Any]]] = []
        self._lock = threading.Lock()

    def reply(self, message: str) -> dict[str, Any]:
        with self._lock:
            if self._agent is None:
                direct_result = direct_mapping_result(message)
                if direct_result is not None:
                    self._pending_direct_exchanges.append((message, direct_result))
                    return direct_result
                self._agent = QuantumChemAgent()
                for previous_message, previous_result in self._pending_direct_exchanges:
                    self._agent.remember_direct_exchange(previous_message, previous_result)
                self._pending_direct_exchanges.clear()
            return self._agent.reply_result(message)


CHAT = ChatService()


class ChatHandler(BaseHTTPRequestHandler):
    server_version = "QuantumChemChat/1.0"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/index.html"}:
            body = INDEX_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/health":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"error": "Página não encontrada."})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/chat":
            self._send_json(404, {"error": "Rota não encontrada."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Requisição inválida."})
            return
        if content_length <= 0 or content_length > MAX_BODY_SIZE:
            self._send_json(413, {"error": "Mensagem vazia ou muito grande."})
            return

        try:
            data = json.loads(self.rfile.read(content_length))
            message = data.get("message", "").strip()
        except (json.JSONDecodeError, AttributeError, UnicodeDecodeError):
            self._send_json(400, {"error": "JSON inválido."})
            return
        if not message:
            self._send_json(400, {"error": "Digite uma mensagem."})
            return

        try:
            result = CHAT.reply(message)
        except Exception as exc:  # A interface deve exibir erros de configuração/API.
            self._send_json(500, {"error": str(exc)})
            return
        self._send_json(200, result)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def main() -> None:
    host, port = "127.0.0.1", 8000
    server = ThreadingHTTPServer((host, port), ChatHandler)
    print(f"Chat disponível em http://{host}:{port}")
    print("Pressione Ctrl+C para encerrar.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
