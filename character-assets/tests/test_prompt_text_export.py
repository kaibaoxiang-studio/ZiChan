import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from export_prompt_text import render_prompt_text, write_prompt_text


class PromptTextExportTest(unittest.TestCase):
    def package(self, *texts):
        return {'schema_version': 'CharacterPromptPackageV1',
                'prompts': [{'id': str(i), 'text': text} for i, text in enumerate(texts)]}

    def test_original_paragraphs_and_unicode_are_preserved(self):
        text = '原创头像。\n\n右侧分缝、耳后发片。'
        self.assertEqual(render_prompt_text(self.package(text)), text + '\n')

    def test_alternatives_keep_json_order_without_new_headings(self):
        self.assertEqual(render_prompt_text(self.package('第一案完整正文', '第二案完整正文')),
                         '第一案完整正文\n\n第二案完整正文\n')

    def test_export_writes_exact_utf8_and_keeps_json_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); package = self.package('人物完整提示词。')
            source = root / 'prompt-package.json'; source.write_text(json.dumps(package, ensure_ascii=False), encoding='utf-8')
            before = source.read_bytes(); output = root / '提示词.txt'
            result = write_prompt_text(package, output)
            self.assertEqual(output.read_bytes(), '人物完整提示词。\n'.encode('utf-8'))
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(result['source'], 'prompts[].text')

    def test_empty_body_is_not_exported(self):
        with self.assertRaises(ValueError):
            render_prompt_text(self.package('   '))

    def test_export_rejects_linked_output_without_altering_target(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            actual = root / 'existing.txt'
            actual.write_bytes(b'previous canonical output')
            output = root / '提示词.txt'
            output.symlink_to(actual.name)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                write_prompt_text(self.package('新的完整正文。'), output)
            self.assertEqual(actual.read_bytes(), b'previous canonical output')


if __name__ == '__main__':
    unittest.main()
