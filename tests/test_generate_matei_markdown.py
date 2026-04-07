import unittest

from scripts.generate_matei_markdown import (
    parse_chapter_from_filename,
    parse_book_index_from_filename,
    parse_old_testament_book_ids,
    parse_new_testament_book_ids,
    extract_verses,
)


class GenerateMateiMarkdownTests(unittest.TestCase):
    def test_parse_book_index_for_nt_file(self):
        self.assertEqual(
            parse_book_index_from_filename("NT02-Marcu--09---Biblia-Ortodoxa-2020.mp3"),
            2,
        )

    def test_parse_book_index_for_vt_file(self):
        self.assertEqual(
            parse_book_index_from_filename("VT38-Zaharia-07---Biblia-Ortodoxa-2020.mp3"),
            38,
        )

    def test_parse_chapter_for_standard_nt_file(self):
        self.assertEqual(
            parse_chapter_from_filename("NT01-Matei--09---Biblia-Ortodoxa-2020.mp3"),
            9,
        )

    def test_parse_chapter_for_standard_vt_file(self):
        self.assertEqual(
            parse_chapter_from_filename("VT01-Facerea-09---Biblia-Ortodoxa-2020.mp3"),
            9,
        )

    def test_parse_chapter_for_single_chapter_nt_file(self):
        self.assertEqual(
            parse_chapter_from_filename("NT18-Filimon---Biblia-Ortodoxa-2020.mp3"),
            1,
        )

    def test_parse_new_testament_book_ids_from_homepage_select(self):
        homepage_html = '''
        <select name="carte">
          <option value="-1">VECHIUL TESTAMENT</option>
          <option value="25">Facerea</option>
          <option value="-2">NOUL TESTAMENT</option>
          <option value="55">Matei</option>
          <option value="53">Marcu</option>
          <option value="4">Apocalipsa</option>
        </select>
        '''
        self.assertEqual(parse_new_testament_book_ids(homepage_html), [55, 53, 4])

    def test_parse_old_testament_book_ids_from_homepage_select(self):
        homepage_html = '''
        <select name="carte">
          <option value="-1">VECHIUL TESTAMENT</option>
          <option value="25">Facerea</option>
          <option value="32">Ieşirea</option>
          <option value="54">Manase</option>
          <option value="-2">NOUL TESTAMENT</option>
          <option value="55">Matei</option>
        </select>
        '''
        self.assertEqual(parse_old_testament_book_ids(homepage_html), [25, 32, 54])

    def test_extract_verses_from_chapter_html(self):
        chapter_html = '''
        <tr id=verset1>
          <td><a name=1></a><span class=nr>1.</span></td>
          <td>Primul verset.</td>
        </tr>
        <tr id=verset2>
          <td><a name=2></a><span class=nr>2.</span></td>
          <td>Al doilea <b>verset</b>.</td>
        </tr>
        '''
        self.assertEqual(extract_verses(chapter_html), ["Primul verset.", "Al doilea verset."])


if __name__ == "__main__":
    unittest.main()
