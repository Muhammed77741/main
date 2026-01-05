"""
Automatic fixer for 'TelegramNotifier' object has no attribute 'bot' error

This script automatically finds and fixes all instances of incorrect
.bot usage in Python files.

Usage:
    python fix_notifier_bot_attribute.py <file_path>
    python fix_notifier_bot_attribute.py live_bot_mt5_fullauto.py
"""

import re
import sys
import os
from pathlib import Path


class NotifierBotFixer:
    """Fix incorrect .bot attribute usage in TelegramNotifier"""

    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.changes_made = []

    def read_file(self):
        """Read file content"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return None

    def write_file(self, content):
        """Write file content"""
        try:
            # Create backup
            backup_path = str(self.file_path) + '.backup'
            with open(self.file_path, 'r', encoding='utf-8') as f:
                with open(backup_path, 'w', encoding='utf-8') as backup:
                    backup.write(f.read())

            print(f"📋 Backup created: {backup_path}")

            # Write fixed content
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except Exception as e:
            print(f"❌ Error writing file: {e}")
            return False

    def fix_content(self, content):
        """Fix all .bot attribute issues"""

        original_content = content
        line_number = 0

        # Pattern 1: self.notifier.bot.method_name() -> self.notifier.method_name()
        pattern1 = r'self\.notifier\.bot\.'
        replacement1 = 'self.notifier.'

        matches1 = list(re.finditer(pattern1, content))
        if matches1:
            for match in matches1:
                # Find line number
                line_num = content[:match.start()].count('\n') + 1
                self.changes_made.append(f"Line {line_num}: self.notifier.bot. → self.notifier.")

            content = re.sub(pattern1, replacement1, content)
            print(f"✅ Fixed {len(matches1)} instance(s) of 'self.notifier.bot.'")

        # Pattern 2: notifier.bot. -> notifier.
        pattern2 = r'(?<!self\.)notifier\.bot\.'
        replacement2 = 'notifier.'

        matches2 = list(re.finditer(pattern2, content))
        if matches2:
            for match in matches2:
                line_num = content[:match.start()].count('\n') + 1
                self.changes_made.append(f"Line {line_num}: notifier.bot. → notifier.")

            content = re.sub(pattern2, replacement2, content)
            print(f"✅ Fixed {len(matches2)} instance(s) of 'notifier.bot.'")

        # Pattern 3: if self.notifier.bot: -> if self.notifier:
        pattern3 = r'if\s+self\.notifier\.bot\s*:'
        replacement3 = 'if self.notifier:'

        matches3 = list(re.finditer(pattern3, content))
        if matches3:
            for match in matches3:
                line_num = content[:match.start()].count('\n') + 1
                self.changes_made.append(f"Line {line_num}: if self.notifier.bot: → if self.notifier:")

            content = re.sub(pattern3, replacement3, content)
            print(f"✅ Fixed {len(matches3)} instance(s) of 'if self.notifier.bot:'")

        # Pattern 4: hasattr(self.notifier, 'bot') -> self.notifier
        pattern4 = r'hasattr\(self\.notifier,\s*[\'"]bot[\'"]\)'
        replacement4 = 'self.notifier'

        matches4 = list(re.finditer(pattern4, content))
        if matches4:
            for match in matches4:
                line_num = content[:match.start()].count('\n') + 1
                self.changes_made.append(f"Line {line_num}: hasattr(self.notifier, 'bot') → self.notifier")

            content = re.sub(pattern4, replacement4, content)
            print(f"✅ Fixed {len(matches4)} instance(s) of hasattr checks")

        # Pattern 5: if self.notifier and self.notifier.bot: -> if self.notifier:
        pattern5 = r'if\s+self\.notifier\s+and\s+self\.notifier\.bot\s*:'
        replacement5 = 'if self.notifier:'

        matches5 = list(re.finditer(pattern5, content))
        if matches5:
            for match in matches5:
                line_num = content[:match.start()].count('\n') + 1
                self.changes_made.append(f"Line {line_num}: if self.notifier and self.notifier.bot: → if self.notifier:")

            content = re.sub(pattern5, replacement5, content)
            print(f"✅ Fixed {len(matches5)} instance(s) of redundant checks")

        if content == original_content:
            print("ℹ️  No .bot attributes found in file")
            return None

        return content

    def analyze_file(self, content):
        """Analyze file for .bot usage"""
        print(f"\n{'='*80}")
        print(f"🔍 Analyzing: {self.file_path}")
        print(f"{'='*80}\n")

        issues = []

        # Find all .bot references
        for i, line in enumerate(content.split('\n'), 1):
            if '.bot' in line and 'notifier' in line:
                issues.append((i, line.strip()))

        if issues:
            print(f"Found {len(issues)} line(s) with potential .bot issues:\n")
            for line_num, line_content in issues:
                print(f"   Line {line_num}: {line_content}")
            print()

        return issues

    def fix_file(self):
        """Main method to fix file"""

        print(f"\n{'='*80}")
        print(f"🔧 NOTIFIER BOT ATTRIBUTE FIXER")
        print(f"{'='*80}")

        # Check file exists
        if not self.file_path.exists():
            print(f"\n❌ File not found: {self.file_path}")
            return False

        # Read file
        print(f"\n📂 Reading file: {self.file_path}")
        content = self.read_file()
        if content is None:
            return False

        # Analyze first
        issues = self.analyze_file(content)

        if not issues:
            print("✅ File looks good - no .bot attributes found!")
            return True

        # Ask for confirmation
        print(f"\n{'='*80}")
        response = input("🔧 Apply automatic fixes? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("❌ Cancelled by user")
            return False

        # Fix content
        print(f"\n{'='*80}")
        print("🔧 Applying fixes...")
        print(f"{'='*80}\n")

        fixed_content = self.fix_content(content)

        if fixed_content is None:
            return True

        # Show changes
        if self.changes_made:
            print(f"\n📋 Changes made:")
            for change in self.changes_made:
                print(f"   • {change}")

        # Write file
        print(f"\n💾 Writing fixed file...")
        if not self.write_file(fixed_content):
            return False

        print(f"\n{'='*80}")
        print("✅ FILE FIXED SUCCESSFULLY!")
        print(f"{'='*80}")
        print(f"\n💡 Recommendations:")
        print(f"   1. Test the file: python {self.file_path.name}")
        print(f"   2. If issues occur, restore from backup: {self.file_path.name}.backup")
        print(f"   3. Review changes manually to ensure correctness")

        return True


def main():
    """Main entry point"""

    print(f"\n{'='*80}")
    print("🤖 TELEGRAM NOTIFIER BOT ATTRIBUTE FIXER")
    print("="*80)

    if len(sys.argv) < 2:
        print("\n❌ Usage: python fix_notifier_bot_attribute.py <file_path>")
        print("\nExample:")
        print("   python fix_notifier_bot_attribute.py live_bot_mt5_fullauto.py")
        print("   python fix_notifier_bot_attribute.py live_bot_mt5_semiauto.py")
        return

    file_path = sys.argv[1]

    fixer = NotifierBotFixer(file_path)
    success = fixer.fix_file()

    if success:
        print(f"\n✅ Done!")
    else:
        print(f"\n❌ Failed to fix file")
        sys.exit(1)


if __name__ == "__main__":
    main()
