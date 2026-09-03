"""Deploy to a home k3s cluster fronted by an ArgoCD app-of-apps GitOps repo."""

from __future__ import annotations

from pathlib import Path

from bootstrapper.core.component import Addon

ADDON = Addon(
    id="deploy-k3s",
    summary=(
        "k8s manifests for a k3s + ArgoCD + MetalLB homelab, plus a workflow that "
        "builds, pushes to ghcr.io and bumps the pinned tag in your GitOps repo."
    ),
    root=Path(__file__).parent,
    requires=("docker", "github-actions"),
    group="deploy",
    order=40,
)

COMPONENTS = [ADDON]
