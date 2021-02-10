from io import StringIO

from django.test import TestCase

from bptl.work_units.xential.utils import SnakeXMLParser


class SnakeXMLParserTests(TestCase):
    def test_xml_to_snakecase(self):
        xml_data = StringIO(
            '<data xmlns:sup="nl.inext.statusupdates"><oneVariable>Hello!</oneVariable><anotherVariable>Bye!</anotherVariable></data>'
        )

        parser = SnakeXMLParser()
        parsed_data = parser.parse(stream=xml_data)

        self.assertIn("one_variable", parsed_data)
        self.assertIn("another_variable", parsed_data)
