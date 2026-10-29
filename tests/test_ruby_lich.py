"""Run after `nix build .#packaged`: python3 tests/test_ruby_lich.py.

Launcher regression checks run without Nix on the executable search path:

These cover Ruby version probes, missing-install diagnostics, desktop path
configuration, argument forwarding, exit status, and GTK runtime asset paths.
Packaged native gems are loaded with an empty home and stale Bundler settings
to prove the launcher does not depend on a user's bundle installation.
Saga login and extended gameplay remain separate manual checks.
"""

import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest


LAUNCHER = Path(os.environ.get(
    "RUBY_LICH", str(Path(__file__).resolve().parents[1] / "result/bin/ruby-lich")
))


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ruby-lich-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.env = {"HOME": str(self.home), "PATH": "/usr/bin:/bin"}

    def run_ruby(self, *args):
        return subprocess.run(
            [str(LAUNCHER), *args],
            env=self.env,
            cwd="/",
            capture_output=True,
            text=True,
            timeout=30,
        )

    def install_fixture(self, checkout=None):
        checkout = checkout or self.home / ".local/share/lichnix/runtime"
        result = self.run_ruby('-e', 'exit')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((checkout / 'lich.rbw').is_file())
        return checkout

    def test_version_without_nix_or_checkout(self):
        for option in ("--version", "-v"):
            result = self.run_ruby(option)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ruby 4.0.", result.stdout)
            self.assertFalse((self.home / ".local/share/lichnix/runtime").exists())

    def test_missing_arguments_and_invalid_destination(self):
        self.assertEqual(self.run_ruby().returncode, 2)
        destination = self.home / ".local/share/lichnix/runtime"
        destination.mkdir(parents=True)
        (destination / "lich.rbw").write_text("keep me")
        result = self.run_ruby("lich.rbw")
        self.assertEqual(result.returncode, 1)
        self.assertIn(str(destination), result.stderr)
        self.assertEqual((destination / 'lich.rbw').read_text(), 'keep me')

    def test_arguments_environment_and_exit_status(self):
        checkout = self.install_fixture()
        script = checkout / "script with spaces.rb"
        script.write_text(
            'require "json"\n'
            'puts JSON.generate([ARGV, Dir.pwd, ENV.to_h])\n'
            'exit 17\n'
        )
        result = self.run_ruby(str(script), "argument with spaces", "--no-gtk")
        self.assertEqual(result.returncode, 17, result.stderr)
        args, cwd, env = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(args, ["argument with spaces", "--no-gtk"])
        self.assertEqual(cwd, str(checkout.resolve()))
        self.assertNotIn("BUNDLE_PATH", env)
        self.assertTrue(env["BUNDLE_GEMFILE"].startswith("/nix/store/"))
        self.assertTrue(env["GEM_HOME"].startswith("/nix/store/"))
        self.assertEqual(env["GEM_HOME"], env["GEM_PATH"])
        self.assertTrue(Path(env["FONTCONFIG_FILE"]).is_file())
        self.assertTrue(Path(env["GDK_PIXBUF_MODULE_FILE"]).is_file())
        self.assertTrue(any(
            (Path(p) / "Atk-1.0.typelib").is_file()
            for p in env["GI_TYPELIB_PATH"].split(":")
        ))

    def test_data_root_override_ignores_writeable_source_override(self):
        data_root = self.home / "custom data root"
        self.env["LICHNIX_DATA_HOME"] = str(data_root)
        checkout = self.install_fixture(data_root / "runtime")
        self.env["LICHNIX_WRITEABLE_SRC_HOME"] = "/missing/writeable"
        self.env["LICHNIX_SRC_HOME"] = "/missing/obsolete"
        result = self.run_ruby("-e", 'puts Dir.pwd')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(checkout.resolve()))

    def test_packaged_lich_uses_fixed_subdirectory(self):
        data_root = self.home / "custom data root"
        self.env.update(LICHNIX_DATA_HOME=str(data_root),
                        LICHNIX_WRITEABLE_SRC_HOME="/missing/writeable")
        checkout = data_root / 'runtime'
        launcher = os.environ.get("LICH", str(LAUNCHER.parent / "lich"))
        result = subprocess.run([launcher, "--version"], env=self.env,
                                cwd="/", text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r'(?m)^The Lich, version \d+\.\d+\.\d+\S*$')
        self.assertTrue(str((checkout / 'lich.rbw').resolve()).startswith('/nix/store/'))
        self.assertTrue(str((checkout / 'lib').resolve()).startswith('/nix/store/'))

    def test_raw_children_inherit_layout_and_bundle(self):
        checkout = self.install_fixture()
        installed = (checkout / 'lich.rbw').resolve().parent
        package = self.home / 'fixture package with spaces'
        shutil.copytree(installed, package)
        # Exercise the real upstream argument/constant initialization and session
        # launcher, then stop before login/GTK. No store file is changed.
        upstream = (package / 'upstream.rbw').read_text()
        prefix = upstream.split("require File.join(LIB_DIR, 'gemcheck.rb')")[0]
        (package / 'upstream.rbw').chmod(0o644)
        (package / 'upstream.rbw').write_text(prefix + '''
require 'json'
require 'rbconfig'
require File.join(LIB_DIR, 'util', 'util.rb')
require File.join(LIB_DIR, 'common', 'session_launcher.rb')
if ARGV.include?('--spawn')
  flags = Lich::Common::SessionLauncher.send(:optional_spawn_flags, {})
  exec RbConfig.ruby, $PROGRAM_NAME, '--child', *flags
end
puts JSON.generate([LICH_DIR, LIB_DIR, DATA_DIR, SCRIPT_DIR, TEMP_DIR,
                    MAP_DIR, LOG_DIR, BACKUP_DIR, ACTIVE_SESSION_DIR,
                    Gem.loaded_specs.fetch('sqlite3').full_gem_path, ARGV])
''')
        (package / 'upstream.rbw').chmod(0o444)
        alternate = self.home / 'alternate runtime'
        paths = {name: self.home / ('custom ' + name) for name in
                 ('data', 'scripts', 'temp', 'maps', 'logs', 'backup', 'active-session-dir')}
        flags = ['--home=' + str(alternate)] + [f'--{name}={path}' for name, path in paths.items()]
        for mode in ('--direct', '--spawn'):
            result = self.run_ruby(str(package / 'lich.rbw'), mode, *flags)
            self.assertEqual(result.returncode, 0, result.stderr)
            values = json.loads(result.stdout.splitlines()[-1])
            self.assertEqual(values[:9], [str(alternate), str(package / 'lib'),
                                        *map(str, paths.values())])
            self.assertTrue(values[9].startswith('/nix/store/'))
            self.assertIn('self-update/rollback', result.stderr)
            self.assertTrue((alternate / 'lich.rbw').is_file())
        # Home-relative entry point used by elogin, with inherited environment.
        result = self.run_ruby(str(alternate / 'lich.rbw'), '--child', '--home=' + str(alternate))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_core_initializes_with_store_source_and_writable_database(self):
        checkout = self.install_fixture()
        package = (checkout / 'lich.rbw').resolve().parent
        lines = (package / 'upstream.rbw').read_text().splitlines()
        stop_line = lines.index("require File.join(LIB_DIR, 'main', 'main.rb')") + 1
        preload = self.home / 'stop before login.rb'
        preload.write_text('''
require 'json'
probe = TracePoint.new(:line) do |event|
  if event.path == ENV.fetch('PROBE_UPSTREAM') && event.lineno == Integer(ENV.fetch('PROBE_LINE'))
    probe.disable
    raise 'database not writable' unless Lich.db.get_first_value('select 42') == 42
    STDOUT.puts JSON.generate([LICH_DIR, LIB_DIR, DATA_DIR, Dir.pwd])
    STDOUT.flush
    exit! 0
  end
end
probe.enable
''')
        self.env.update(PROBE_UPSTREAM=str(package / 'upstream.rbw'), PROBE_LINE=str(stop_line))
        result = self.run_ruby('-r', str(preload), str(checkout / 'lich.rbw'), '--no-gtk')
        debug = '\n'.join(p.read_text(errors='replace') for p in (checkout / 'temp').glob('*.log'))
        self.assertEqual(result.returncode, 0, result.stderr + debug)
        self.assertEqual(json.loads(result.stdout.splitlines()[-1]),
                         [str(checkout), str(package / 'lib'), str(checkout / 'data'), str(checkout)])
        self.assertTrue((checkout / 'data/lich.db3').is_file())
        self.assertTrue(str(package).startswith('/nix/store/'))

    def test_packaged_native_gems_with_empty_home_and_stale_config(self):
        checkout = self.install_fixture()
        (checkout / ".bundle").mkdir()
        (checkout / ".bundle/config").write_text(
            'BUNDLE_PATH: "/missing"\nBUNDLE_WITHOUT: "gtk:profanity"\n'
        )
        self.env.update({
            "BUNDLE_GEMFILE": "/missing/Gemfile",
            "BUNDLE_PATH": "/missing/bundle",
            "GEM_HOME": "/missing/gems",
            "GEM_PATH": "/missing/gems",
            "BUNDLE_WITHOUT": "gtk:profanity",
            "BUNDLE_WITH": "development:vscode",
        })
        result = self.run_ruby("-e", '''
require "sqlite3"
require "curses"
require "openssl"
require "ffi"
require "yaml"
require "zlib"
require "glib2"
require "gobject-introspection"
require "gtk3"
# Load GTK's typelib and shared libraries without opening a display/window.
GObjectIntrospection::Repository.default.require("Gtk", "3.0")
db = SQLite3::Database.new(":memory:")
raise "SQLite failed" unless db.get_first_value("select 42") == 42
names = %w[sqlite3 curses openssl ffi yaml zlib glib2 gobject-introspection gtk3]
raise "external gem loaded" unless names.all? { |name|
  Gem.loaded_specs.fetch(name).full_gem_path.start_with?("/nix/store/")
}
puts "packaged native gems loaded"
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("packaged native gems loaded", result.stdout)


if __name__ == "__main__":
    unittest.main()
