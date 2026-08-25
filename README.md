## apk2zpk

Convert every Alpine Linux `.apk` below a repository directory into a
corresponding `.zip` archive:

```console
apk2zpk /repo
apk2zpk /repo --jobs 4
```

The converter uses Alpine's `apk extract` command and Info-ZIP. Conversion
runs in parallel using one process per CPU by default. ZIP files are staged in
unique temporary directories and moved into place only after they are
complete; the source APKs are retained.
