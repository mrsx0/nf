import unittest
import xml.etree.ElementTree as ET
from nf import InvoiceValidator, InvoiceAuditTool

class TestInvoiceValidator(unittest.TestCase):
    def setUp(self):
        self.validator = InvoiceValidator()
        self.audit_tool = InvoiceAuditTool()

    def test_tax_rules_loading(self):
        tax_rules = self.validator._load_tax_rules()
        self.assertIn("ICMS", tax_rules)
        self.assertIn("IPI", tax_rules)
        self.assertEqual(tax_rules["ICMS"]["standard_rate"], 0.18)

    def test_customer_database_loading(self):
        customer_db = self.validator._load_customer_database()
        self.assertIn("customers", customer_db)
        self.assertIn("123", customer_db["customers"])
        self.assertEqual(customer_db["customers"]["123"]["name"], "Company A")

    def test_supplier_database_loading(self):
        supplier_db = self.validator._load_supplier_database()
        self.assertIn("suppliers", supplier_db)
        self.assertIn("789", supplier_db["suppliers"])
        self.assertEqual(supplier_db["suppliers"]["789"]["name"], "Supplier X")

    def test_valid_invoice_audit(self):
        # Create a test XML invoice
        root = ET.Element("invoice")
        ET.SubElement(root, "invoice_id").text = "INV001"
        ET.SubElement(root, "customer_id").text = "123"
        ET.SubElement(root, "supplier_id").text = "789"
        
        items = ET.SubElement(root, "items")
        item = ET.SubElement(items, "item")
        ET.SubElement(item, "description").text = "Item1"
        ET.SubElement(item, "quantity").text = "1"
        ET.SubElement(item, "unit_price").text = "100.00"
        
        taxes = ET.SubElement(root, "taxes")
        ET.SubElement(taxes, "ICMS").text = "18.00"
        
        ET.SubElement(root, "total").text = "118.00"
        
        xml_string = ET.tostring(root, encoding='unicode')
        result = self.audit_tool._run(xml_string)
        self.assertIn("PASSED", result)

    def test_invalid_xml_format(self):
        invalid_xml = "<invalid>This is not a valid invoice XML</invalid>"
        result = self.audit_tool._run(invalid_xml)
        self.assertIn("Error", result)

if __name__ == '__main__':
    unittest.main()