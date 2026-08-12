"""Built-in addons.

Each submodule exposes a `COMPONENTS` list. Addons render after the template, in
`order`, so a later addon can deliberately replace a file an earlier one wrote —
the CLI reports every override it performs.
"""
