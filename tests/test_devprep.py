import contextlib
import hashlib
import io
import json
import os
import subprocess
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from devprep.catalog import load_catalog, select_tools
from devprep.cli import main
from devprep.managers import install_commands, refresh_command, successful
from devprep.planner import build_plan
from devprep.platforms import Host, MANAGERS, detect, read_os_release
from devprep.recipes import validate_archive, validate_zip, download_verified, install_vscode, install_java_tool
from devprep.runner import execute


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()

    def test_default_is_the_entire_catalog(self):
        selected = select_tools(self.catalog, [], [], [])
        self.assertEqual({t['id'] for t in selected}, {t['id'] for t in self.catalog['tools']})
        self.assertGreaterEqual(len(selected), 50)

    def test_custom_resolves_dependencies_in_order(self):
        selected = select_tools(self.catalog, [], ['maven', 'rust'], [])
        ids = [t['id'] for t in selected]
        self.assertEqual(ids, ['build-tools', 'rust', 'java', 'maven'])

    def test_custom_category_and_tools_are_a_union(self):
        selected = select_tools(self.catalog, ['core'], ['python'], [])
        self.assertTrue(all(t['category'] == 'core' or t['id'] == 'python' for t in selected))
        self.assertIn('python', [t['id'] for t in selected])

    def test_dependency_cannot_be_excluded(self):
        with self.assertRaisesRegex(ValueError, 'Required tool is excluded: java'):
            select_tools(self.catalog, [], ['maven'], ['java'])

    def test_unrelated_exclusion(self):
        selected = select_tools(self.catalog, [], [], ['julia'])
        self.assertNotIn('julia', [t['id'] for t in selected])

    def test_bad_selections(self):
        for categories, tools, excluded in [(['typo'], [], []), ([], ['oops'], []), ([], [], ['oops'])]:
            with self.subTest(categories=categories, tools=tools, excluded=excluded), self.assertRaises(ValueError):
                select_tools(self.catalog, categories, tools, excluded)

    def test_cycles_are_rejected(self):
        sample = {'categories': {'test': ''}, 'tools': [
            {'id': 'a', 'category': 'test', 'requires': ['b']},
            {'id': 'b', 'category': 'test', 'requires': ['a']}]}
        with self.assertRaisesRegex(ValueError, 'cycle'):
            select_tools(sample, [], [], [])

    def test_all_manager_plans_serialize(self):
        for manager in MANAGERS:
            with self.subTest(manager=manager):
                host = Host('windows' if manager == 'winget' else 'macos' if manager == 'brew' else 'linux',
                            'test', 'x86_64', manager)
                plan = build_plan(host, select_tools(self.catalog, [], [], []))
                self.assertEqual(len(plan.steps), len(self.catalog['tools']))
                json.dumps(plan.to_dict())
                self.assertTrue(all(s.commands or s.recipe or s.reason for s in plan.steps))

    def test_vscode_fallback_respects_architecture_and_libc(self):
        tools = select_tools(self.catalog, [], ['vscode'], [])
        for manager, arch, recipe in [('apt', 'x86_64', 'vscode'), ('dnf', 'aarch64', 'vscode'),
                                      ('apk', 'x86_64', ''), ('apt', 'riscv64', '')]:
            with self.subTest(manager=manager, arch=arch):
                step = build_plan(Host('linux', 'test', arch, manager), tools).steps[0]
                self.assertEqual(step.recipe, recipe)

    def test_desktop_compose_is_included_with_docker(self):
        for system, manager in [('windows', 'winget'), ('macos', 'brew')]:
            plan = build_plan(Host(system, 'test', 'x86_64', manager),
                              select_tools(self.catalog, [], ['compose'], []))
            self.assertEqual(plan.steps[-1].reason, 'included with Docker Desktop')


class PlatformTests(unittest.TestCase):
    def test_families_and_derivatives(self):
        cases = [('ubuntu', '', 'apt'), ('linuxmint', 'ubuntu debian', 'apt'),
                 ('custom', 'debian', 'apt'), ('fedora', '', 'dnf'), ('rocky', 'rhel fedora', 'dnf'),
                 ('arch', '', 'pacman'), ('opensuse-tumbleweed', 'opensuse suse', 'zypper'),
                 ('alpine', '', 'apk'), ('void', '', 'xbps'), ('gentoo', '', 'emerge'), ('nixos', '', 'nix')]
        for distro, like, expected in cases:
            with self.subTest(distro=distro):
                host = detect('Linux', {'ID': distro, 'ID_LIKE': like}, which=lambda x: x, immutable=False)
                self.assertEqual(host.manager, expected)

    def test_identity_beats_incidental_package_manager(self):
        host = detect('Linux', {'ID': 'arch'}, which=lambda name: name, immutable=False)
        self.assertEqual(host.manager, 'pacman')

    def test_yum_fallback(self):
        host = detect('Linux', {'ID': 'centos'}, which=lambda name: name if name == 'yum' else None, immutable=False)
        self.assertEqual(host.manager, 'yum')

    def test_native_desktops(self):
        self.assertEqual(detect('Windows').manager, 'winget')
        self.assertEqual(detect('Darwin').manager, 'brew')

    def test_unsupported_and_immutable_hosts(self):
        for system, release, immutable in [('Linux', {'ID': 'unknown'}, False),
                                           ('Linux', {'ID': 'fedora'}, True), ('FreeBSD', {}, False)]:
            with self.subTest(system=system, immutable=immutable), self.assertRaises(ValueError):
                detect(system, release, immutable=immutable)

    def test_release_data_is_not_executable(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'os-release'
            marker = Path(temp) / 'executed'
            path.write_text('ID=ubuntu\nID_LIKE="debian"\nPRETTY_NAME="$(touch ' + str(marker) + ')"\n')
            values = read_os_release(path)
            self.assertEqual(values['ID_LIKE'], 'debian')
            self.assertFalse(marker.exists())


class CommandTests(unittest.TestCase):
    @patch('devprep.managers.executable', side_effect=lambda x: x)
    def test_arch_never_uses_partial_refresh(self, _):
        self.assertEqual(refresh_command('pacman'), ['pacman', '-Syu', '--noconfirm'])
        self.assertEqual(install_commands('pacman', ['git']), [['pacman', '-S', '--needed', '--noconfirm', 'git']])

    def test_winget_exact_ids_and_no_upgrades(self):
        args = install_commands('winget', ['Git.Git'])[0]
        self.assertIn('--exact', args)
        self.assertIn('--no-upgrade', args)
        self.assertIn('--disable-interactivity', args)
        self.assertEqual(args[args.index('--id') + 1], 'Git.Git')

    def test_winget_installed_code_is_success(self):
        self.assertTrue(successful('winget', 0x8A15002B))
        self.assertTrue(successful('winget', -1978335189))
        self.assertFalse(successful('apt', 0x8A15002B))
        self.assertFalse(successful('winget', 1))

    def test_visual_studio_installs_the_cpp_workload(self):
        tool = select_tools(load_catalog(), [], ['build-tools'], [])
        args = build_plan(Host('windows', 'windows', 'AMD64', 'winget'), tool).steps[0].commands[0]
        self.assertIn('Microsoft.VisualStudio.Workload.VCTools', args[args.index('--override') + 1])


class CliTests(unittest.TestCase):
    def invoke(self, args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    @patch('devprep.cli.execute', side_effect=AssertionError('must not install'))
    @patch('subprocess.run', side_effect=AssertionError('must not run commands'))
    @patch('urllib.request.urlopen', side_effect=AssertionError('must not download'))
    def test_default_dry_run_has_no_install_side_effects(self, *_):
        code, output, _ = self.invoke(['--dry-run', '--manager', 'apt'])
        self.assertEqual(code, 0)
        self.assertIn('notebooks', output)
        self.assertIn('vscode', output)

    def test_json_implies_preview(self):
        code, output, _ = self.invoke(['--json', '--manager', 'winget', '--tools', 'git', '--no-refresh'])
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertIsNone(data['refresh'])
        self.assertEqual([s['id'] for s in data['steps']], ['git'])

    @patch('devprep.cli.execute', side_effect=AssertionError('must not install'))
    def test_cross_platform_execution_is_rejected(self, _):
        code, _, error = self.invoke(['--manager', 'winget', '--yes'])
        self.assertEqual(code, 2)
        self.assertIn('previews only', error)

    def test_conflicting_all_selection(self):
        code, _, error = self.invoke(['--all', '--tools', 'git', '--dry-run'])
        self.assertEqual(code, 2)
        self.assertIn('cannot be combined', error)

    def test_empty_explicit_selection_never_means_install_everything(self):
        for option in ('--tools', '--categories', '--exclude'):
            with self.subTest(option=option), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main([option, ',', '--yes'])
            self.assertEqual(caught.exception.code, 2)

    @patch('sys.stdin.isatty', return_value=False)
    def test_noninteractive_custom_needs_selection(self, _):
        code, _, error = self.invoke(['--custom', '--yes'])
        self.assertEqual(code, 2)
        self.assertIn('terminal', error)

    @patch('sys.stdin.isatty', return_value=True)
    @patch('builtins.input', side_effect=['1,3'])
    def test_custom_menu_selects_categories(self, *_):
        code, output, _ = self.invoke(['--custom', '--dry-run', '--manager', 'apt'])
        self.assertEqual(code, 0)
        self.assertIn('node', output)
        self.assertNotIn('jupyterlab', output)

    @patch('devprep.cli.execute', return_value=0)
    @patch('devprep.cli.detect', return_value=Host('linux', 'ubuntu', 'x86_64', 'apt'))
    @patch('sys.stdin.isatty', return_value=True)
    @patch('builtins.input', side_effect=['custom', 'core', 'y'])
    def test_custom_is_selectable_at_default_confirmation(self, _input, _tty, _host, execute_mock):
        code, _, _ = self.invoke([])
        self.assertEqual(code, 0)
        self.assertTrue(all(s.category == 'core' for s in execute_mock.call_args.args[0].steps))

    @patch('devprep.cli.detect', return_value=Host('linux', 'ubuntu', 'x86_64', 'apt'))
    @patch('sys.stdin.isatty', return_value=False)
    def test_noninteractive_install_requires_yes(self, *_):
        code, _, error = self.invoke(['--tools', 'git'])
        self.assertEqual(code, 2)
        self.assertIn('--yes', error)


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'report.json'
        self.host = Host('linux', 'ubuntu', 'x86_64', 'apt')

    def plan(self, ids):
        return build_plan(self.host, select_tools(load_catalog(), [], ids, []))

    def execute_mocked(self, plan, returncodes, **kwargs):
        results = [subprocess.CompletedProcess([], code) for code in returncodes]
        with patch('devprep.runner.privilege_prefix', return_value=['sudo']), \
             patch('devprep.runner.shutil.which', return_value='/fake/manager'), \
             patch('devprep.runner.subprocess.run', side_effect=results) as run, \
             contextlib.redirect_stdout(io.StringIO()):
            code = execute(plan, report_path=self.path, **kwargs)
        return code, json.loads(self.path.read_text()), run

    def test_refresh_failure_stops_installs_and_is_reported(self):
        code, report, run = self.execute_mocked(self.plan(['git']), [1])
        self.assertEqual(code, 1)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(report['results'], [])
        self.assertIn('refresh failed', report['error'])

    def test_failure_blocks_dependents_but_continues_unrelated_tools(self):
        plan = self.plan(['git', 'java', 'maven', 'neovim'])
        code, report, run = self.execute_mocked(plan, [0, 0, 1, 0])
        self.assertEqual(code, 1)
        self.assertEqual({r['id']: r['status'] for r in report['results']},
                         {'git': 'installed', 'java': 'failed', 'maven': 'blocked', 'neovim': 'installed'})
        self.assertEqual(run.call_count, 4)

    def test_no_refresh_executes_only_installs(self):
        code, report, run = self.execute_mocked(self.plan(['git']), [0], no_refresh=True)
        self.assertEqual(code, 0)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][0], 'sudo')
        self.assertFalse(run.call_args.kwargs.get('shell', False))

    def test_missing_mappings_are_not_success(self):
        code, report, _ = self.execute_mocked(self.plan(['opentofu']), [])
        self.assertEqual(code, 1)
        self.assertEqual(report['results'][0]['status'], 'unavailable')

    def test_unavailable_can_be_allowed_explicitly(self):
        code, _, _ = self.execute_mocked(self.plan(['opentofu']), [], allow_unavailable=True)
        self.assertEqual(code, 0)

    def test_interrupt_retains_completed_results(self):
        with patch('devprep.runner.privilege_prefix', return_value=[]), \
             patch('devprep.runner.shutil.which', return_value='/fake/manager'), \
             patch('devprep.runner.subprocess.run', side_effect=[subprocess.CompletedProcess([], 0), KeyboardInterrupt]), \
             contextlib.redirect_stdout(io.StringIO()):
            code = execute(self.plan(['git', 'jq']), no_refresh=True, report_path=self.path)
        self.assertEqual(code, 130)
        report = json.loads(self.path.read_text())
        self.assertEqual(report['results'][0]['id'], 'git')
        self.assertIn('Interrupted', report['error'])


class ArchiveTests(unittest.TestCase):
    def test_vscode_installs_verified_archive_and_reruns_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
                member = tarfile.TarInfo('VSCode-linux-x64/bin/code')
                content = b'#!/bin/sh\nexit 0\n'
                member.size = len(content)
                member.mode = 0o755
                archive.addfile(member, io.BytesIO(content))
            data = buffer.getvalue()
            metadata = json.dumps({'url': 'https://example.test/code.tar.gz',
                                   'sha256hash': hashlib.sha256(data).hexdigest()}).encode()
            with patch('devprep.recipes.data_dir', return_value=root / 'data'), \
                 patch('pathlib.Path.home', return_value=root / 'home'), \
                 patch('urllib.request.urlopen', side_effect=[io.BytesIO(metadata), io.BytesIO(data)]) as network:
                host = Host('linux', 'ubuntu', 'x86_64', 'apt')
                try:
                    self.assertTrue(install_vscode(host))
                except OSError as error:
                    if os.name == 'nt' and getattr(error, 'winerror', None) == 1314:
                        self.skipTest('Windows account cannot create symlinks; recipe is Linux-only')
                    raise
                self.assertTrue((root / 'home/.local/bin/code').is_symlink())
                self.assertTrue(install_vscode(host))
                self.assertEqual(network.call_count, 2)

    def test_java_archive_install_and_rerun(self):
        with tempfile.TemporaryDirectory() as temp:
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w') as archive:
                archive.writestr('gradle-9.0/bin/gradle.bat', '@echo gradle')
            data = buffer.getvalue()
            metadata = json.dumps({'downloadUrl': 'https://example.test/gradle.zip',
                                   'checksum': hashlib.sha256(data).hexdigest()}).encode()
            with patch('devprep.recipes.data_dir', return_value=Path(temp)), \
                 patch('urllib.request.urlopen', side_effect=[io.BytesIO(metadata), io.BytesIO(data)]) as network, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(install_java_tool('gradle'))
                self.assertTrue(install_java_tool('gradle'))
                self.assertEqual(network.call_count, 2)

    def test_tar_rejects_traversal_links_and_devices(self):
        for name, kind in [('../outside', tarfile.REGTYPE), ('/outside', tarfile.REGTYPE),
                           ('link', tarfile.SYMTYPE), ('device', tarfile.CHRTYPE)]:
            with self.subTest(name=name, kind=kind):
                member = tarfile.TarInfo(name)
                member.type = kind
                archive = Mock()
                archive.getmembers.return_value = [member]
                with self.assertRaises(ValueError):
                    validate_archive(archive)

    def test_zip_rejects_windows_and_posix_traversal(self):
        for name in ('../bad', '/bad', '..\\bad', 'C:/bad'):
            with self.subTest(name=name):
                archive = Mock()
                archive.infolist.return_value = [zipfile.ZipInfo(name)]
                with self.assertRaises(ValueError):
                    validate_zip(archive)

    def test_checksum_mismatch_fails(self):
        response = io.BytesIO(b'wrong content')
        with tempfile.TemporaryDirectory() as temp, patch('urllib.request.urlopen', return_value=response):
            with self.assertRaisesRegex(ValueError, 'checksum'):
                download_verified('https://example.test/file', Path(temp) / 'download', '0' * 64)

    def test_non_https_downloads_fail(self):
        with self.assertRaises(ValueError):
            download_verified('http://example.test/file', Path('unused'), '0' * 64)


if __name__ == '__main__':
    unittest.main()
