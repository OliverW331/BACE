"""Synthetic regression tests for the reviewed writing-tool subset."""
import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

PROJECT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT / '.agents/skills/citation-management/scripts'
sys.path.insert(0, str(SCRIPTS))
from doi_to_bibtex import DOIConverter, main as doi_main
from format_bibtex import BibTeXFormatter
from _common import parse_bibtex

spec = importlib.util.spec_from_file_location(
    'package_checker', PROJECT / '.agents/skills/bace-nature-response/scripts/check_package_consistency.py')
checker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = checker
spec.loader.exec_module(checker)

BIB = '@article{Fixture2026, title={Synthetic {BACE} fixture}, author={Doe, J.}, year={2026}, doi={10.0000/fixture}}'


class CitationTests(unittest.TestCase):
    def converter(self, body, status=200):
        converter = DOIConverter()
        converter.session.get = Mock(return_value=Mock(status_code=status, text=body))
        return converter

    def test_http_success_with_html_is_not_bibtex_success(self):
        self.assertIsNone(self.converter('<html>Temporary error</html>').doi_to_bibtex('10.0000/fixture'))

    def test_valid_metadata_and_title_braces_survive(self):
        self.assertEqual(self.converter(BIB).doi_to_bibtex('10.0000/fixture'), BIB)

    def test_wrong_doi_record_is_rejected(self):
        self.assertIsNone(self.converter(BIB).doi_to_bibtex('10.0000/different'))

    def test_invalid_identifier_does_not_make_network_request(self):
        converter = self.converter(BIB)
        self.assertIsNone(converter.doi_to_bibtex('not-a-doi'))
        converter.session.get.assert_not_called()

    def test_partial_batch_does_not_write_output_or_exit_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'out.bib'
            with patch.object(sys, 'argv', ['doi_to_bibtex.py', '10.0000/fixture', '10.0000/missing', '-o', str(output)]), \
                 patch.object(DOIConverter, 'convert_multiple', return_value=[BIB]), \
                 self.assertRaises(SystemExit) as caught:
                doi_main()
            self.assertEqual(caught.exception.code, 2)
            self.assertFalse(output.exists())

    def test_formatter_preserves_nested_titles_and_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'input.bib';p.write_text(BIB)
            before=hashlib.sha256(p.read_bytes()).hexdigest()
            result=BibTeXFormatter().format_file(str(p), fix_issues=False)
            self.assertEqual(parse_bibtex(result)[0]['fields']['title'], 'Synthetic {BACE} fixture')
            self.assertEqual(parse_bibtex(result)[0]['key'], 'Fixture2026')
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), before)

    def test_formatter_rejects_lossy_inputs_before_writing(self):
        invalid = [BIB+'\n@article{Broken, title={unfinished}',
                   '@string{venue="Synthetic"}\n'+BIB,
                   '@article{X, title=macro, year={2026}}',
                   '@article{X, title={A}, title={B}}',
                   '@article{X, title={A} # {B}}',
                   '@article{X, title="A" # "B"}',
                   '@article(X, title={A})',
                   '@article{X, title={A}, broken field}']
        with tempfile.TemporaryDirectory() as tmp:
            for text in invalid:
                with self.subTest(text=text):
                    p=Path(tmp)/'input.bib';p.write_text(text)
                    out=Path(tmp)/'out.bib'
                    with self.assertRaises(ValueError):BibTeXFormatter().format_file(str(p),output=str(out))
                    self.assertFalse(out.exists())
                    self.assertEqual(p.read_text(),text)

    def test_standard_month_literal_is_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'input.bib';p.write_text(BIB[:-1]+', month=July}')
            result=BibTeXFormatter().format_file(str(p),fix_issues=False)
            self.assertEqual(parse_bibtex(result)[0]['fields']['month'],'July')


class PackageTests(unittest.TestCase):
    def test_stale_revision_quote_is_detected(self):
        findings=checker.check_quotes('We analysed the supplied synthetic cases.',
            r'\RevisedExcerpt{We completed extensive human validation of every model output.}',
            'synthetic-response.tex', ['RevisedExcerpt'], 20)
        self.assertEqual([f.code for f in findings], ['QUOTE_NOT_IN_MANUSCRIPT'])

    def test_clean_marked_equivalence_and_difference(self):
        self.assertFalse(checker.check_clean_marked('Synthetic result.',r'\added{Synthetic result.}','a','b'))
        self.assertTrue(checker.check_clean_marked('Synthetic result.',r'\added{Different result.}','a','b'))

    def test_unanswered_reviewer_comment(self):
        findings=checker.check_response_counts(r'\ReviewerComment{Please clarify the source.}', 'fixture.tex')
        self.assertEqual([f.code for f in findings], ['COMMENT_RESPONSE_COUNT_MISMATCH'])

    def test_cyclic_include_fails_instead_of_hanging(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'fixture.tex';p.write_text(r'\input{fixture}')
            with self.assertRaises(ValueError):checker.read_latex_project(p)


if __name__ == '__main__':
    unittest.main(verbosity=2)
