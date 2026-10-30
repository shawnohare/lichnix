# lichnix

A Nix development environment and standalone Ruby launcher for running
[Lich 5](https://github.com/elanthia-online/lich-5), the Ruby scripting engine
and game proxy for Simutronics' Gemstone IV and DragonRealms.

This project started as a mechanism for a macOS Nix user to easily get started
using Lich, without contaminating their global environment or setting up ruby
version managers.

Targets:

- Apple Silicon macOS (`aarch64-darwin`)
- Ruby 4.0.9
- Native GTK dependencies so script config GUIs can activate
- Lich v5.23.0

WARNING: Interfaces and overarching goals are still under revision.

## Quickstart

To expose a `lich` executable that starts the lich server and a `ruby-lich`
executable that exposes a ruby interpreter with native dependencies required by
Lich, run:

### From flake


```sh
nix profile add github:shawnohare/lichnix#packaged
# check versions
lich --version && ruby-lich --version
```

### From repo checkout

If you want to build the launchers from a clone this repo, run:

```sh
nix build .#packaged
./result/bin/lich --version
# optionally
nix profile add .#packaged
```

### Saga Settings

Saga is the official Simutronics client for GemStone IV and DragonRealms. It
has native Lich integration that uses a ruby executable and path to
the Lich entry poinnt script (`lich.rbw`).

In Saga enable connecting via Lich (in the Menu options) and set

- Ruby executable to the absolute path of: `~/.nix-profile/bin/ruby-lich` or
  `$PWD/result/bin/ruby-lich`
- Lich directory to absolute path of: `~/.local/share/lichnix/runtime`


## Mode Details

This flake exposes two modes: `packaged` and `writeble`.

Both modes supply Ruby 4.0, GTK, and native dependencies on Apple Silicon
macOS.

`writeable` mode offers a more flexible installation of Lich with
the fewest feature restrictions, and it closer to a standard installation of
Lich and all its dependencies. This mode is also suitable for Lich development
itself.

`packaged` mode offers stronger guarantees of a working installation, but at
the expense of locking gems and the specific version of Lich. Lich update and
repair features will fail.


| Mode | Gems | Source |
|---|---|---|
| `writeable` | Bundler installs writable gems; scripts may add gems | Your chosen Lich checkout and its Gemfile/lockfile. Akin to an "editable mode" useful for Lich feature development. |
| `packaged` | Immutable gems built by Nix | Immutable core at the flake's pinned Lich revision. Geared toward the average end user. Cannot update lich or repair gems.|

Existing `nix develop` and `ruby-lich` packages keep using packaged gems.
Writeable mode is an explicit choice. It supports other Lich versions when they
work with this Ruby and native dependency set; new native dependencies still
require a flake change.


## Packaged mode: use pinned Lich and gems


Lich self-update, core rollback, engine replacement, gem repair/refresh, and
runtime gem additions are unsupported. Normal startup warns about these limits;
the package does not intercept those commands. They may attempt downloads or
writes and fail. Upgrade/rebuild or roll back the Nix package instead. Script
downloads, maps, logs, settings, and data synchronization remain writable.

From this repository:

```sh
nix build .#packaged
./result/bin/lich --version
```

`packaged` provides both `lich` and `ruby-lich`. Keep `result` to retain the
runtime against garbage collection. Alternatively, install the executables into
a profile, including without cloning this repository:

```sh
nix profile add github:shawnohare/lichnix#packaged
lich --version
```

The packaged `ruby-lich` also initializes the runtime home when it runs a script;
Ruby-only probes (`--version` or `-v`) do not trigger setup. Run `lich --version`
once before selecting the Lich folder in Saga, so the folder already exists.
A new package selects its new core on launch while preserving existing runtime
files. Package rollback does not roll back user data or downloaded scripts.
For Saga, select `$LICHNIX_DATA_HOME/runtime` as the Lich folder
and the absolute path to
`./result/bin/ruby-lich` or `~/.nix-profile/bin/ruby-lich` as the Ruby executable.
Expand `~` to your full home directory. If needed, enable Saga's
`Menu > Session > Allow login with Lich` after a Direct login.

`nix develop` retains the packaged development shell, including all upstream
gem groups. The standalone package excludes `development` and `vscode`.
No `bundle install` is needed or supported in packaged mode. Its launcher
activates the pinned bundle and ignores local Bundler configuration. Additional
script gems require changing the Nix gem package and rebuilding; upstream gem
repair cannot write to the Nix store.

## Checkout location

`LICHNIX_DATA_HOME` is the shared project data root, defaulting to
`${XDG_DATA_HOME:-$HOME/.local/share}/lichnix`.

| Mode | Default writable directory | Source override |
|---|---|---|
| Writeable | `$LICHNIX_DATA_HOME/src/lich-5` | `LICHNIX_WRITEABLE_SRC_HOME` or the helper's checkout argument |
| Packaged | `$LICHNIX_DATA_HOME/runtime` | None; change `LICHNIX_DATA_HOME` to relocate the whole project layout |

With defaults, these are `~/.local/share/lichnix/src/lich-5` and
`~/.local/share/lichnix/runtime`. Gems and saved launchers for writeable
mode stay under its checkout's `.bundle`. Packaged gems remain in the Nix store.

Existing state and checkouts are not moved automatically. If you already used
`$LICHNIX_DATA_HOME/packaged/runtime`, stop Lich sessions and move that directory
to `$LICHNIX_DATA_HOME/runtime` before launching the updated package, provided
the new destination does not already exist. This preserves maps, settings,
scripts, and saved logins. Update Saga's Lich folder to the new runtime path.

For writeable mode, you can move the old `$LICHNIX_DATA_HOME/writeable/lich-5`
checkout to `$LICHNIX_DATA_HOME/src/lich-5` while sessions are stopped, then rerun
`prepare-writeable` to refresh its gem paths and saved launchers. Alternatively, point
`LICHNIX_WRITEABLE_SRC_HOME` at your existing checkout and rerun preparation.
If you previously used native mode, replace `LICHNIX_NATIVE_SRC_HOME` with
`LICHNIX_WRITEABLE_SRC_HOME` and run `prepare-writeable` for that checkout.
This also lets you keep a checkout at the former `native/lich-5` path.
The former packaged checkout at `$LICHNIX_DATA_HOME/packaged/lich-5` is left
untouched. For migration, stop existing sessions, back up that checkout, and copy
the contents of its `data`, `scripts`, `maps`, `logs`, `backup`, and `temp`
directories into the corresponding new runtime directories before first launch.
Copy any additional script-owned assets you need. Do not copy `lib`, `lich.rbw`,
or `.bundle`: the new runtime manages its entry point and core-library links.
The old `LICHNIX_SRC_HOME` setting is no longer used. To keep writeable source
in this repository, use `export LICHNIX_WRITEABLE_SRC_HOME="$PWD/upstream/lich-5"`.

Writeable mode keeps source and mutable data together. The `lich-w` executable
changes into its checkout; `ruby-lich-w` preserves the caller's working
directory, as Ruby does. The existing packaged `ruby-lich` changes into the
runtime home before running Ruby. Generic profile/build launchers use environment
variables at launch time. For custom writeable paths in Finder, use the helper's
checkout-bound launchers. The profile launchers use the default checkout or
`LICHNIX_WRITEABLE_SRC_HOME`; they require that checkout to be prepared first.

Both modes can be installed in the same profile:

```sh
nix profile add .#packaged .#writeable
```

Packaged executables are `lich` and `ruby-lich`; writeable executables are
`lich-w` and `ruby-lich-w`. Individual writeable launchers are also available as
`.#lich-w` and `.#ruby-lich-w`. For Saga with the default writeable checkout,
select `$LICHNIX_DATA_HOME/src/lich-5` as the Lich folder and the absolute path
to `~/.nix-profile/bin/ruby-lich-w` as Ruby. For a custom checkout in Finder,
use its `.bundle/bin/ruby-lich-w` launcher, which remembers the chosen paths.

See [docs/packaged_lich.md](docs/packaged_lich.md) for the packaged source/state
boundary and verification limits, and [docs/gem_modes.md](docs/gem_modes.md)
for gem-mode background.

## Writeable mode: use your own checkout

Writeable mode offers the least restrictions on how Lich is used. The source code
can be edited, arbitrary branches used, and scripts that install Gems should in
theory be runnable.

You need Nix with flakes enabled and Git. From this repository:

```sh
export LICHNIX_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/lichnix"
nix run .#prepare-writeable
"$LICHNIX_DATA_HOME/src/lich-5/.bundle/bin/lich-w" --version
```
This will clone the Lich 5 source if it is not already.

Set `LICHNIX_WRITEABLE_SRC_HOME` to your chosen absolute path, or pass it to
`bin/prepare-writeable /path/to/lich-5`. If the target dir does not exist, the
helper clones upstream Lich and checks out the **exact commit pinned by this
flake**, detached from any branch—not the upstream default branch or latest
release. An existing Git checkout (including a worktree) keeps its current
revision and local changes. To use another release, switch your checkout
yourself and rerun the helper. Bundler may update the checkout's lockfile to
add the local Ruby/platform; review those changes as you would after a normal
`bundle install`.

You can also use the flake without cloning `lichnix`:

```sh
nix run github:shawnohare/lichnix#prepare-writeable -- /absolute/path/to/lich-5
```

Use a branch/revision containing this feature until it reaches the default branch.
The helper installs the checkout's bundle, checks SQLite and GTK, retains the
Nix runtime/toolchain against garbage collection, and writes these executables:

- `<checkout>/.bundle/bin/lich-w`: starts `lich.rbw` in that checkout; pass Lich
  arguments such as `--no-gtk` or `--login CHARACTER`.
- `<checkout>/.bundle/bin/ruby-lich-w`: acts like Ruby, retaining the caller's
  working directory and forwarding its arguments. In Saga, use its absolute
  path as the Ruby executable, and select the checkout as the Lich folder.

These launchers remember the source and gem directories, including when Saga
is opened from Finder. They can also be added to your terminal's `PATH`.
The helper puts gems in `<checkout>/.bundle/gems-<toolchain-id>` and retains
its runtime via `toolchain-root` inside that directory. Keep that symlink.
A changed toolchain gets a separate gem directory; old directories are not
automatically deleted.

### When to rerun `prepare-writeable`

Run the helper once for each checkout, then rerun it when:

- You edit `Gemfile` or `Gemfile.lock`, or switch to a Lich release/branch
  that changes either file.
- You change the gem groups to install, such as including development tools.
- You adopt an updated lichnix runtime/toolchain. The saved launchers retain
  their previous runtime until preparation rewrites them.
- You move the checkout or delete its `.bundle` directory, gems, or launchers.

For example, after adding a gem to your checkout's `Gemfile`, run this from
the **lichnix repository**:

```sh
bin/prepare-writeable /absolute/path/to/lich-5
```

That runs `bundle install` in the selected checkout: Bundler resolves the new
requirement, updates `Gemfile.lock` as needed, and installs missing gems into
the writable gem home. Review the Gemfile/lockfile changes, then restart Lich
or reconnect through Saga to use the installed gem. No `gemset.nix` generation
or Nix gem rebuild is needed. A gem needing additional system libraries may
require adding those native dependencies to lichnix first.

You do not need to rerun the helper for ordinary Ruby/script edits, source
updates that leave gem requirements unchanged, or every launch. Gems installed
dynamically by scripts are available in the same writable gem home without
rerunning preparation. Preparation installs in place; it does not remove extra
gems or roll back changes if installation fails.

When using lichnix remotely, rerun the earlier `nix run …#prepare-writeable`
command with the same checkout path and your chosen lichnix revision. Merely
rerunning it against a pinned revision does not update that revision. Likewise,
updating a Nix profile or `result-writeable` does not rewrite the helper's saved
checkout-bound launchers; rerun preparation using the updated flake as well.

### Manual setup commands

For interactive development, run `nix develop .#writeable` from this repository.
The commands the helper runs **inside the Lich checkout** are:

```sh
cd "$LICHNIX_WRITEABLE_SRC_HOME"
BUNDLE_PATH__SYSTEM=true BUNDLE_FORCE_RUBY_PLATFORM=1 \
  BUNDLE_WITHOUT=development:vscode ruby-lich-w -S bundle install
ruby-lich-w -e 'require "sqlite3"; require "gtk3"; GObjectIntrospection::Repository.default.require("Gtk", "3.0")'
lich-w --version
```

`BUNDLE_PATH__SYSTEM=true` tells Bundler to install into this launcher's
`GEM_HOME`; `BUNDLE_WITHOUT` skips development/editor tools. Set
`BUNDLE_WITHOUT=''` when running the helper to include them.
The helper additionally creates the GC root and checkout-bound launchers;
prefer it for persistent Saga use. A development shell alone is not a durable
GC root. For a manually managed installation, retain a build symlink with
`nix build .#writeable --out-link result-writeable` or install `.#writeable` into your profile.

Writeable mode sets `GEM_HOME`/`GEM_PATH` and preloads a small RubyGems user-directory
setter through `RUBYOPT`. This makes ordinary installs and `user_install: true`
use the same writable location, including raw Ruby children that inherit the
environment. It does **not** activate `bundler/setup` globally: runtime gem
selection can include gems installed by scripts. Explicit installation paths,
removed environment variables, or another Ruby executable can bypass this.
The checkout's lockfile governs initial Bundler installation, rather than
restricting every runtime `require`. Upstream repair/update and game login
still need manual end-to-end verification.


## Maintaining Ruby dependencies (packaged mode)

Run this helper from any directory. The script contains detailed comments
describing its commands and the files it changes.

- [`bin/update-lich-dependencies`](bin/update-lich-dependencies) handles a Lich
  release bump. First edit the revision in `inputs.lich-src.url` in `flake.nix`, then
  run this helper. It updates the Lich input lock, regenerates `gemset.nix`
  from the pinned upstream Gemfile and Gemfile.lock, builds the launcher and
  development gems, and runs all flake checks. Gem versions follow upstream's
  lockfile; individual gem names are not accepted.

To verify the runtime without updating dependencies, run `nix build .#ruby-lich`,
`nix build --no-link .#lich-development-gems`, and `nix flake check` from the repository.

The Gemfile and Gemfile.lock come directly from the pinned Lich source in the
Nix store. The input uses a Git checkout because upstream marks Gemfile.lock
as `export-ignore`, omitting it from GitHub source archives. Only the generated
`nix/gems/gemset.nix` is committed here: Nix still needs this metadata to fetch
and build gems reproducibly. Group membership comes from that generated
metadata; the launcher excludes `development` and `vscode`, while the
development shell includes all groups. The flake checks verify that the
metadata matches upstream's Gemfile and lockfile.

Entering `nix develop` does not refresh metadata or switch your writable Lich
clone. Review and commit `gemset.nix` together with `flake.nix` and `flake.lock`
for a Lich release bump. Do not run `bundle install` against the packaged
environment.

## TODO

### Installation and runtime layout

- [x] Support locating the Lich checkout under `~/.local/share/lichnix/{writeable,packaged}/lich-5/` instead
  of requiring `upstream/lich-5`.
- [x] Make the Lich source directory configurable rather than assuming its
  location relative to this repository.
- [x] Separate packaged core source from mutable runtime state, including
  credentials, saved logins, maps, scripts, databases, and logs.
- [x] Investigate a standalone Nix-provided Ruby launcher that can be executed
  by Saga without first launching Saga from a Nix shell.

### GTK support

- [x] Resolve the native Ruby `glib2` build failure involving the missing `sysprof-capture-4.pc` pkg-config dependency.
- [x] Install the complete `gtk` Bundler dependency group on Apple Silicon macOS.
- [ ] Verify Lich's native GTK launcher and GTK-dependent scripting functionality.
- [x] Retest Saga integration with GTK enabled and remove the temporary `--no-gtk` workaround.

See `docs/gtk_troubleshooting.md` for investigation notes.

### Development environments

- [ ] Retain a full default development shell (`nix develop`) including GTK, Ruby development tools, and test dependencies.
- [ ] Add a smaller headless/runtime shell (`nix develop .#headless`) without GTK dependencies.
- [ ] Share the same pinned Ruby 4 toolchain and common native dependencies across both shells.
- [ ] Determine which Ruby gems are strictly required for headless operation.

### Headless operation and frontend integration

- [ ] Establish a successful direct Lich character login from the CLI.
- [ ] Test `lich --login CHARACTER --headless 8000` without the Saga launcher.
- [ ] Connect VellumFE or ProfanityFE to the detached Lich session.
- [ ] Determine which functionality requires GTK and which is available with a headless proxy.
- [ ] Evaluate Saga's integration against the full GTK-enabled Lich runtime.

### Nix packaging

- [x] Package Ruby gems using `bundix` and `bundlerEnv`.
- [x] Create a Nix derivation for Lich itself.
- [x] Provide a standalone `lich` executable using the packaged Ruby environment.
- [x] Put managed mutable application data outside the immutable Nix store.
  Arbitrary script writes are not sandboxed; GUI/gameplay verification remains.
