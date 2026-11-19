"""Keep t3assistant's managed skills aligned with native email authority boundaries."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
PROFILE = ROOT / 'dot_config/pi/profiles/t3assistant'
MAIL = PROFILE / 'skills/coursework-mail'


class NativeEmailProfileTests(unittest.TestCase):
    def test_native_entrypoint_and_no_shell_helper_contract(self):
        text = (MAIL / 'SKILL.md').read_text()
        for name in ('external_connectors', 'email_accounts', 'email_search', 'email_read',
                     'email_attachment', 'email_refresh', 'email_tag', 'Settings → Email'):
            self.assertIn(name, text)
        all_text = '\n'.join(path.read_text() for path in MAIL.rglob('*.md'))
        for obsolete in ('helper_argv', 'helper_cwd', 'python -B -m t3assistant.mail_triage',
                         'notmuch search', 'notmuch show', 'notmuch tag'):
            self.assertNotIn(obsolete, all_text)
        self.assertFalse((PROFILE / 'skills/symlink_aerc-email').exists())
        self.assertIn('.config/pi/profiles/t3assistant/skills/aerc-email', (ROOT / '.chezmoiremove').read_text())
        self.assertNotIn('.config/pi/profiles/t3assistant/skills/aerc-email', (ROOT / '.chezmoiignore').read_text())

    def test_assignment_is_read_only_and_daily_state_is_resumable(self):
        assignment = (MAIL / 'references/assignment-context.md').read_text()
        self.assertIn('read and unread', assignment)
        self.assertIn('No `email_refresh`, `email_tag`', assignment)
        flags = (MAIL / 'references/read-flags.md').read_text()
        for contract in ('expected_revision', 'readEvidence', 'markEligible', 'remove: ["unread"]',
                         'add: []', 'nextOffset', 'later', 'Legacy'):
            self.assertIn(contract.lower(), flags.lower())
        private = (MAIL / 'references/private-config.md').read_text()
        self.assertIn('even after midnight', private)
        self.assertIn('never import a legacy read as native', private)

    def test_referenced_skill_files_exist(self):
        for path in PROFILE.glob('skills/**/SKILL.md'):
            for target in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', path.read_text()):
                if '://' not in target:
                    self.assertTrue((path.parent / target).is_file(), f'{path}: {target}')
        for path in MAIL.rglob('*.md'):
            for target in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', path.read_text()):
                if '://' not in target:
                    self.assertTrue((path.parent / target).is_file(), f'{path}: {target}')

    def test_existing_daily_schedule_and_private_journal_description(self):
        timer = (ROOT / 'dot_config/systemd/user/t3assistant-email.timer').read_text()
        self.assertIn('OnCalendar=*-*-* 08:05:00 America/Chicago', timer)
        self.assertIn('Persistent=true', timer)
        service = (ROOT / 'dot_config/systemd/user/t3assistant-email.service').read_text()
        self.assertIn(' mail-tick', service)
        self.assertIn('UMask=0077', service)
        self.assertIn('dedicated daily native-email review journal', (PROFILE / 'mcp.json.tmpl').read_text())
        delegation = (MAIL / 'references/delegated-review.md').read_text()
        self.assertIn('Haiku 5.5', delegation)
        self.assertIn('(account, messageId)', delegation)
        priorities = (MAIL / 'references/priorities.md').read_text()
        self.assertIn('selective public reporting', priorities)
        self.assertIn('GitHub', priorities)


if __name__ == '__main__':
    unittest.main()
