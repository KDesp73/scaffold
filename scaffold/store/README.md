# scaffold store

Each directory must include at least a fetch script which will accept the
destination as the first argument with the version as the second optional
argument and the platform as the third.

When a project is scaffolded, `scaffold` runs each selected package's fetch
script directly from the store, so the dependency's files end up inside the
project's deps directory (the scripts themselves are never copied in).

The name of the directory will be used as the key for the dependency.

The `flags` file should include the `CFLAGS` and `LDFLAGS` necessary to include
and link with the library. If missing no flags will be added to the build step.
