from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from livethetrader.ml.pipeline import MLPipeline, build_supervised_dataset


def _load_rows(dataset_path: Path) -> list[dict[str, Any]]:
    if dataset_path.suffix.lower() == ".jsonl":
        rows: list[dict[str, Any]] = []
        for line in dataset_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("Cada linha do JSONL deve ser um objeto")
            rows.append(payload)
        return rows

    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Arquivo JSON de treino deve conter uma lista de objetos")
    return [row for row in payload if isinstance(row, dict)]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Treina pipeline ML supervisionado e salva artefato versionado."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        type=Path,
        help="Caminho para dataset supervisionado (.json ou .jsonl).",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("artifacts/ml"),
        help="Diretório de saída para o artefato versionado.",
    )
    parser.add_argument(
        "--artifact-prefix",
        default="signal-gate",
        help="Prefixo no nome do arquivo de artefato.",
    )
    parser.add_argument(
        "--version-tag",
        default="",
        help="Tag opcional no nome do artefato (ex.: dev, staging, prod).",
    )
    return parser


def run_training(
    *,
    dataset_path: Path,
    artifact_dir: Path,
    artifact_prefix: str,
    version_tag: str,
) -> Path:
    rows = _load_rows(dataset_path)
    samples = build_supervised_dataset(rows, lambda row: MLPipeline.build_sample(**row))

    pipeline = MLPipeline()
    dataset = pipeline.temporal_split(samples)
    pipeline.train(dataset)

    if not pipeline.model_ready:
        raise RuntimeError("Pipeline não treinou modelo válido: dataset de treino vazio")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    version_suffix = f"-{version_tag}" if version_tag.strip() else ""
    artifact_path = artifact_dir / f"{artifact_prefix}{version_suffix}-{timestamp}.json"
    pipeline.save_artifact(artifact_path)
    return artifact_path


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    artifact_path = run_training(
        dataset_path=args.dataset,
        artifact_dir=args.artifact_dir,
        artifact_prefix=args.artifact_prefix,
        version_tag=args.version_tag,
    )
    print(str(artifact_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
