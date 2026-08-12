"""Build to Azure Container Registry and roll out to Azure Container Apps."""

from __future__ import annotations

from pathlib import Path

from bootstrapper.core.component import Addon

ADDON = Addon(
    id="deploy-azure-aca",
    summary="Push to ACR and deploy to Azure Container Apps on the default branch.",
    root=Path(__file__).parent,
    requires=("docker", "github-actions"),
    group="deploy",
    order=40,
)

COMPONENTS = [ADDON]
