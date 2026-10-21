# scaffold store

Each directory must include at least a fetch script which will accept the
destination as the first argument with the version as the second optional
argument and the platform as the third

The name of the directory will be used as the key for the dependency.

The `flags` file should include the `CFLAGS` and `LDFLAGS` necessary to include
and link with the library. If missing no flags will be added to the build step.
