from typing import Dict, List
from langchain_core.tools import BaseTool
import google.generativeai as genai
import json
import os
from datetime import datetime
import json
import os
from datetime import datetime

# Initialize Gemini model
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-pro')

class InvoiceValidator:
    def __init__(self):
        self.tax_rules = self._load_tax_rules()
        self.customer_database = self._load_customer_database()
        self.supplier_database = self._load_supplier_database()

    def _load_tax_rules(self) -> Dict:
        # Mock tax rules database
        return {
            "ICMS": {"standard_rate": 0.18, "reduced_rate": 0.12},
            "IPI": {"standard_rate": 0.15},
            "PIS": {"rate": 0.0165},
            "COFINS": {"rate": 0.076}
        }

    def _load_customer_database(self) -> Dict:
        # Mock customer database
        return {
            "customers": {
                "123": {"name": "Company A", "tax_regime": "normal"},
                "456": {"name": "Company B", "tax_regime": "simplified"}
            }
        }

    def _load_supplier_database(self) -> Dict:
        # Mock supplier database
        return {
            "suppliers": {
                "789": {"name": "Supplier X", "tax_regime": "normal"},
                "012": {"name": "Supplier Y", "tax_regime": "simplified"}
            }
        }

class InvoiceAuditTool(BaseTool):
    name: str = "invoice_auditor"
    description: str = "Validates and audits invoice data for tax compliance"
    
    def _run(self, invoice_data: str) -> str:
        validator = InvoiceValidator()
        try:
            invoice = json.loads(invoice_data)
            audit_results = self._perform_audit(invoice, validator)
            return self._generate_audit_report(audit_results)
        except Exception as e:
            return f"Error processing invoice: {str(e)}"

    def _perform_audit(self, invoice: Dict, validator: InvoiceValidator) -> Dict:
        issues = []
        
        # Check tax calculations
        if not self._validate_tax_calculations(invoice, validator.tax_rules):
            issues.append("Tax calculations are incorrect")
            
        # Check fiscal codes
        if not self._validate_fiscal_codes(invoice):
            issues.append("Inconsistent fiscal codes detected")
            
        # Check purchase order alignment
        if not self._validate_purchase_order(invoice):
            issues.append("Divergence between purchase order and invoice")
            
        return {
            "invoice_id": invoice.get("invoice_id"),
            "audit_date": datetime.now().isoformat(),
            "issues": issues,
            "status": "FAILED" if issues else "PASSED"
        }

    def _validate_tax_calculations(self, invoice: Dict, tax_rules: Dict) -> bool:
        # Implement tax calculation validation logic
        return True

    def _validate_fiscal_codes(self, invoice: Dict) -> bool:
        # Implement fiscal code validation logic
        return True

    def _validate_purchase_order(self, invoice: Dict) -> bool:
        # Implement purchase order validation logic
        return True

    def _generate_audit_report(self, audit_results: Dict) -> str:
        report = f"""
        Invoice Audit Report
        -------------------
        Invoice ID: {audit_results['invoice_id']}
        Audit Date: {audit_results['audit_date']}
        Status: {audit_results['status']}
        
        Issues Found:
        {chr(10).join([f'- {issue}' for issue in audit_results['issues']]) if audit_results['issues'] else 'No issues found'}
        """
        return report

# Example usage
if __name__ == "__main__":
    # Configure Gemini
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    sample_invoice = {
        "invoice_id": "INV-2025-001",
        "supplier_id": "789",
        "customer_id": "123",
        "items": [
            {"description": "Product A", "quantity": 2, "unit_price": 100.00},
            {"description": "Product B", "quantity": 1, "unit_price": 150.00}
        ],
        "taxes": {
            "ICMS": 63.00,
            "IPI": 52.50,
            "PIS": 5.78,
            "COFINS": 26.60
        },
        "total": 350.00
    }

    # Process the invoice
    audit_tool = InvoiceAuditTool()
    result = audit_tool._run(json.dumps(sample_invoice))
    
    # Generate analysis with Gemini
    prompt = f"""
    You are a tax audit assistant. Analyze this audit report and provide insights:
    
    {result}
    
    Please provide:
    1. Summary of findings
    2. Risk assessment
    3. Recommended actions
    """
    
    response = model.generate_content(prompt)
    print("\nAudit Report:")
    print(result)
    print("\nAI Analysis:")
    print(response.text)