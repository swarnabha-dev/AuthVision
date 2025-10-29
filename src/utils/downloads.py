"""
Automated model downloader with SHA256 verification.

TODO: Implement in Module 2+ as models are needed.
"""

from typing import Literal


class ModelDownloader:
    """Download and verify pretrained models (stub implementation)."""

    def __init__(self) -> None:
        """Initialize model downloader."""
        raise NotImplementedError("ModelDownloader not implemented - see Module 2+")

    def download_adaface(self, target_dir: str) -> str:
        """Download AdaFace pretrained weights.

        Args:
            target_dir: Target directory for download

        Returns:
            Path to downloaded model

        Raises:
            NotImplementedError: Module not yet implemented
        """
        raise NotImplementedError("AdaFace download not implemented - see Module 7")

    def download_yolov10_tiny(self, target_dir: str) -> str:
        """Download YOLOv10-tiny weights.

        Args:
            target_dir: Target directory for download

        Returns:
            Path to downloaded model

        Raises:
            NotImplementedError: Module not yet implemented
        """
        raise NotImplementedError("YOLOv10-tiny download not implemented - see Module 3")

    def download_movenet_thunder(self, target_dir: str) -> str:
        """Download MoveNet-Thunder model.

        Args:
            target_dir: Target directory for download

        Returns:
            Path to downloaded model

        Raises:
            NotImplementedError: Module not yet implemented
        """
        raise NotImplementedError("MoveNet-Thunder download not implemented - see Module 4")

    def download_osnet_x025(self, target_dir: str) -> str:
        """Download OSNet-x0.25 ReID model.

        Args:
            target_dir: Target directory for download

        Returns:
            Path to downloaded model

        Raises:
            NotImplementedError: Module not yet implemented
        """
        raise NotImplementedError("OSNet-x0.25 download not implemented - see Module 8")

    def verify_checksum(self, file_path: str, expected_sha256: str) -> bool:
        """Verify file SHA256 checksum.

        Args:
            file_path: Path to file
            expected_sha256: Expected SHA256 hash

        Returns:
            True if checksum matches

        Raises:
            NotImplementedError: Module not yet implemented
        """
        raise NotImplementedError("Checksum verification not implemented - see Module 2+")


def download_model(
    model_name: Literal["adaface", "yolov10-tiny", "movenet-thunder", "osnet-x025"],
    target_dir: str,
) -> str:
    """Download a pretrained model by name.

    Args:
        model_name: Name of model to download
        target_dir: Target directory

    Returns:
        Path to downloaded model

    Raises:
        NotImplementedError: Module not yet implemented
    """
    raise NotImplementedError(f"Model download not implemented for {model_name}")
