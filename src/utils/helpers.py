"""Funções auxiliares diversas, compartilhadas entre ferramentas e UI."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def format_duration(seconds: float) -> str:
    """Formata segundos como "1 min 42 s" ou "47 s"."""
    seconds = max(0, int(round(seconds)))
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours} h")
    if minutes:
        parts.append(f"{minutes} min")
    parts.append(f"{secs} s")
    return " ".join(parts)


def format_elapsed_clock(seconds: float) -> str:
    """Formata segundos como relógio "00:47" ou "01:02:03"."""
    seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def open_folder(path: Path) -> None:
    """Abre uma pasta no explorador de arquivos do sistema operacional.

    Falha silenciosamente (registrando em log, via chamador) caso a
    plataforma não seja suportada ou o caminho não exista.
    """
    path = Path(path)
    if not path.exists():
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError:
        pass


def app_data_dir() -> Path:
    """Diretório para dados locais do aplicativo (logs, preferências).

    Usa %LOCALAPPDATA% no Windows quando disponível, com fallback para
    a pasta pessoal do usuário em outras plataformas. Nunca depende de
    caminhos fixos da máquina de desenvolvimento.
    """
    base = os.getenv("LOCALAPPDATA")
    if base:
        return Path(base) / "MaxPDF"
    return Path.home() / ".maxpdf"


def resource_path(relative_path: str) -> Path:
    """Resolve o caminho de um recurso (ex.: ícone), funcionando tanto em
    desenvolvimento quanto dentro de um executável gerado pelo PyInstaller
    (modo --onefile, que extrai recursos para uma pasta temporária
    referenciada por `sys._MEIPASS`).
    """
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path:
        return Path(base_path) / relative_path
    # Em desenvolvimento, os recursos ficam na raiz do projeto (dois
    # níveis acima de src/utils/).
    project_root = Path(__file__).resolve().parents[2]
    return project_root / relative_path


def bytes_to_human(num_bytes: int) -> str:
    """Formata um tamanho em bytes de forma legível (ex.: '3.2 MB')."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def free_disk_space(path: Path) -> int:
    """Retorna o espaço livre em bytes no disco que contém `path`."""
    try:
        usage = os.statvfs(path) if hasattr(os, "statvfs") else None
        if usage is not None:
            return usage.f_bavail * usage.f_frsize
    except OSError:
        pass
    try:
        import shutil

        return shutil.disk_usage(path).free
    except OSError:
        return -1
