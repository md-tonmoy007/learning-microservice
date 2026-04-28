import sys
from pathlib import Path


def ensure_grpc_generated_on_path() -> None:
    generated_dir = str(Path(__file__).parent / "grpc_generated")
    if generated_dir not in sys.path:
        sys.path.insert(0, generated_dir)
