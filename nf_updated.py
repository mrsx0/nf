from typing import Dict, List, Optional, Tuple
from langchain_core.tools import BaseTool
import google.generativeai as genai
import json
import os
import sys
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import tkinter as tk
from tkinter import filedialog

# Initialize Gemini model
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-pro')

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
    
    def _remove_namespaces(self, xml_string: str) -> str:
        """Remove namespaces from XML string for easier parsing."""
        import re
        # Remove namespace declarations
        xml_string = re.sub(r'\sxmlns="[^"]+"', '', xml_string)
        xml_string = re.sub(r'\sxmlns:[^=]+="[^"]+"', '', xml_string)
        # Remove namespace prefixes
        xml_string = re.sub(r'<[^/>]+:', '<', xml_string)
        xml_string = re.sub(r'</[^>]+:', '</', xml_string)
        return xml_string

    def _xml_to_dict(self, xml_string: str) -> Dict:
        """Convert XML string to dictionary format."""
        try:
            # Remove namespaces for easier parsing
            xml_string = self._remove_namespaces(xml_string)
            root = ET.fromstring(xml_string)
            
            # Localiza os elementos principais
            nfe = root.find('.//NFe') or root
            inf_nfe = nfe.find('.//infNFe')
            emit = inf_nfe.find('.//emit')
            dest = inf_nfe.find('.//dest')
            total = inf_nfe.find('.//ICMSTot')
            
            # Monta o dicionário com os dados da nota
            invoice = {
                "invoice_id": inf_nfe.find('.//nNF').text,
                "supplier_id": emit.find('CNPJ').text,
                "supplier_name": emit.find('xNome').text,
                "customer_id": dest.find('CPF').text if dest.find('CPF') is not None else dest.find('CNPJ').text,
                "customer_name": dest.find('xNome').text,
                "items": [],
                "taxes": {},
                "total": float(total.find('vNF').text)
            }
            
            # Parse items
            for det in inf_nfe.findall('.//det'):
                prod = det.find('prod')
                imposto = det.find('imposto')
                
                item = {
                    "description": prod.find('xProd').text,
                    "quantity": float(prod.find('qCom').text),
                    "unit_price": float(prod.find('vUnCom').text),
                    "total": float(prod.find('vProd').text)
                }
                invoice["items"].append(item)
                
                # Parse impostos do item
                if imposto is not None:
                    icms = imposto.find('.//ICMS/*')
                    if icms is not None:
                        for elem in icms:
                            if 'vICMS' in elem.tag:
                                invoice["taxes"]["ICMS"] = float(elem.text) if elem.text else 0.0
                    
                    ipi = imposto.find('.//IPI/*')
                    if ipi is not None:
                        for elem in ipi:
                            if 'vIPI' in elem.tag:
                                invoice["taxes"]["IPI"] = float(elem.text) if elem.text else 0.0
                    
                    pis = imposto.find('.//PIS/*')
                    if pis is not None:
                        for elem in pis:
                            if 'vPIS' in elem.tag:
                                invoice["taxes"]["PIS"] = float(elem.text) if elem.text else 0.0
                    
                    cofins = imposto.find('.//COFINS/*')
                    if cofins is not None:
                        for elem in cofins:
                            if 'vCOFINS' in elem.tag:
                                invoice["taxes"]["COFINS"] = float(elem.text) if elem.text else 0.0
            
            # Adiciona totais dos impostos do total da nota
            try:
                invoice["taxes"].update({
                    "ICMS_TOTAL": float(total.find('vICMS').text) if total.find('vICMS') is not None else 0.0,
                    "IPI_TOTAL": float(total.find('vIPI').text) if total.find('vIPI') is not None else 0.0,
                    "PIS_TOTAL": float(total.find('vPIS').text) if total.find('vPIS') is not None else 0.0,
                    "COFINS_TOTAL": float(total.find('vCOFINS').text) if total.find('vCOFINS') is not None else 0.0
                })
            except (AttributeError, TypeError):
                pass  # Ignora erros se algum dos campos não existir
            
            return invoice
        except ET.ParseError as e:
            raise ValueError(f"Formato XML inválido: {str(e)}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Erro ao processar valores numéricos: {str(e)}")
    
    def _run(self, invoice_data: str) -> str:
        validator = InvoiceValidator()
        try:
            invoice = self._xml_to_dict(invoice_data)
            audit_results = self._perform_audit(invoice, validator)
            return self._generate_audit_report(audit_results)
        except Exception as e:
            return f"Erro ao processar nota fiscal: {str(e)}"

    def _perform_audit(self, invoice: Dict, validator: InvoiceValidator) -> Dict:
        issues = []
        
        # Check tax calculations
        if not self._validate_tax_calculations(invoice, validator.tax_rules):
            issues.append("Cálculos dos impostos estão incorretos")
            
        # Check fiscal codes
        if not self._validate_fiscal_codes(invoice):
            issues.append("Códigos fiscais inconsistentes detectados")
            
        # Check purchase order alignment
        if not self._validate_purchase_order(invoice):
            issues.append("Divergência entre pedido de compra e nota fiscal")
            
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
        Relatório de Auditoria da Nota Fiscal
        ------------------------------------
        Número da NF: {audit_results['invoice_id']}
        Data da Auditoria: {audit_results['audit_date']}
        Status: {'FALHOU' if audit_results['status'] == 'FAILED' else 'APROVADO'}
        
        Problemas Encontrados:
        {chr(10).join([f'- {issue}' for issue in audit_results['issues']]) if audit_results['issues'] else 'Nenhum problema encontrado'}
        """
        return report