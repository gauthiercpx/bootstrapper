"""Discovery of templates and addons.

Built-ins are imported from `bootstrapper.templates` / `bootstrapper.addons`.
Third-party packages register their own by exposing the `bootstrapper.templates`
and `bootstrapper.addons` entry point groups — that is the extension seam that
makes "modular" real rather than aspirational, and it is why nothing in this
module hardcodes a template name.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable
from dataclasses import dataclass, field
from importlib.metadata import entry_points

from .component import Addon, Component, Template
from .errors import IncompatibleSelection, UnknownComponent

TEMPLATE_GROUP = "bootstrapper.templates"
ADDON_GROUP = "bootstrapper.addons"


@dataclass
class Registry:
    """Everything the generator is allowed to render."""

    templates: dict[str, Template] = field(default_factory=dict)
    addons: dict[str, Addon] = field(default_factory=dict)

    # --- registration ---

    def register(self, component: Component) -> None:
        if isinstance(component, Template):
            self.templates[component.id] = component
        elif isinstance(component, Addon):
            self.addons[component.id] = component
        else:  # pragma: no cover - defensive
            raise TypeError(f"cannot register {type(component).__name__}")

    def register_all(self, components: Iterable[Component]) -> None:
        for component in components:
            self.register(component)

    # --- lookup ---

    def template(self, template_id: str) -> Template:
        try:
            return self.templates[template_id]
        except KeyError:
            raise UnknownComponent("template", template_id, list(self.templates)) from None

    def addon(self, addon_id: str) -> Addon:
        try:
            return self.addons[addon_id]
        except KeyError:
            raise UnknownComponent("addon", addon_id, list(self.addons)) from None

    def addons_for(self, template_id: str) -> list[Addon]:
        """Addons compatible with a template, in render order."""
        compatible = [addon for addon in self.addons.values() if addon.supports(template_id)]
        return sorted(compatible, key=lambda addon: (addon.order, addon.id))

    def resolve(self, template_id: str, addon_ids: Iterable[str]) -> list[Addon]:
        """Validate a selection and return it in render order.

        Pulls in `requires` transitively, then rejects conflicts, exclusive
        groups and addons that do not apply to this template.
        """
        template = self.template(template_id)
        selected: dict[str, Addon] = {}
        pending = list(addon_ids)
        while pending:
            addon_id = pending.pop(0)
            if addon_id in selected:
                continue
            addon = self.addon(addon_id)
            if not addon.supports(template.id):
                raise IncompatibleSelection(
                    f"addon {addon.id!r} does not apply to template {template.id!r}"
                )
            selected[addon.id] = addon
            pending.extend(required for required in addon.requires if required not in selected)

        for addon in selected.values():
            clashing = [other for other in addon.conflicts if other in selected]
            if clashing:
                raise IncompatibleSelection(
                    f"addon {addon.id!r} conflicts with {', '.join(sorted(clashing))}"
                )

        groups: dict[str, list[str]] = {}
        for addon in selected.values():
            if addon.group:
                groups.setdefault(addon.group, []).append(addon.id)
        for group, members in groups.items():
            if len(members) > 1:
                raise IncompatibleSelection(
                    f"only one {group!r} addon can be selected, got {', '.join(sorted(members))}"
                )

        return sorted(selected.values(), key=lambda addon: (addon.order, addon.id))


def _load_package(package_name: str) -> list[Component]:
    """Import every submodule of a package and collect its COMPONENTS lists."""
    package = importlib.import_module(package_name)
    found: list[Component] = []
    for module_info in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package_name}.{module_info.name}")
        found.extend(getattr(module, "COMPONENTS", ()))
    return found


def _load_entry_points(group: str) -> list[Component]:
    """Collect components contributed by installed third-party packages."""
    found: list[Component] = []
    for entry_point in entry_points(group=group):
        loaded = entry_point.load()
        # An entry point may point at a component, or at a callable/iterable of them.
        candidates = loaded() if callable(loaded) else loaded
        if isinstance(candidates, Component):
            found.append(candidates)
        else:
            found.extend(candidates)
    return found


def default_registry(*, include_plugins: bool = True) -> Registry:
    """The registry the CLI uses: built-ins plus any installed plugins."""
    registry = Registry()
    registry.register_all(_load_package("bootstrapper.templates"))
    registry.register_all(_load_package("bootstrapper.addons"))
    if include_plugins:
        registry.register_all(_load_entry_points(TEMPLATE_GROUP))
        registry.register_all(_load_entry_points(ADDON_GROUP))
    return registry
