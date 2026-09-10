"""Terminal interface for the first project milestone."""

from __future__ import annotations

import argparse
import json

from dotenv import load_dotenv

from .agent import QuantumChemAgent
from .tools import mapping_example


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente de química quântica (terminal)")
    parser.add_argument("--demo", action="store_true", help="Executa um mapeamento local, sem API.")
    args = parser.parse_args()
    if args.demo:
        print(json.dumps(mapping_example(1, "+", "jordan_wigner"), ensure_ascii=False, indent=2))
        return

    load_dotenv()
    try:
        agent = QuantumChemAgent()
    except RuntimeError as exc:
        print(f"Erro de configuração: {exc}")
        return
    print("Agente pronto. Pergunte sobre química quântica; digite 'sair' para encerrar.")
    while True:
        try:
            question = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté mais.")
            return
        if question.lower() in {"sair", "exit", "quit"}:
            print("Até mais.")
            return
        if not question:
            continue
        try:
            print(f"\nAgente: {agent.reply(question)}")
        except Exception as exc:  # API/network errors are presented cleanly to the user.
            print(f"\nErro ao consultar o modelo: {exc}")


if __name__ == "__main__":
    main()
