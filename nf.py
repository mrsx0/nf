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
import re
import tkinter as tk
from tkinter import filedialog, messagebox
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
    
    def _sanitize_xml(self, xml_string: str) -> str:
        """Sanitiza e formata o XML para processamento."""
        import re
        
        # Remove caracteres inválidos
        xml_string = ''.join(char for char in xml_string if ord(char) < 128)
        
        # Remove quebras de linha e espaços extras
        xml_string = re.sub(r'\s+', ' ', xml_string)
        
        # Garante que há apenas uma declaração XML
        if xml_string.count('<?xml') > 1:
            xml_string = re.sub(r'<\?xml[^>]*\?>', '', xml_string, count=xml_string.count('<?xml')-1)
        
        # Remove BOM se presente
        if xml_string.startswith('\ufeff'):
            xml_string = xml_string[1:]
            
        return xml_string.strip()

    def _remove_namespaces(self, xml_string: str) -> str:
        """Remove namespaces from XML string for easier parsing."""
        import re
        try:
            # Remove namespace declarations
            xml_string = re.sub(r'\sxmlns="[^"]+"', '', xml_string)
            xml_string = re.sub(r'\sxmlns:[^=]+="[^"]+"', '', xml_string)
            # Remove namespace prefixes
            xml_string = re.sub(r'<[^/>]+:', '<', xml_string)
            xml_string = re.sub(r'</[^>]+:', '</', xml_string)
            return xml_string
        except Exception as e:
            raise ValueError(f"Erro ao processar namespaces do XML: {str(e)}")

    def _sanitize_xml(self, xml_string: str) -> str:
        """Sanitize XML string before parsing."""
        # Remove BOM if present
        if xml_string.startswith('\ufeff'):
            xml_string = xml_string[1:]
            
        # Remove invalid characters
        xml_string = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', xml_string)
        
        # Remove all namespaces for easier parsing
        xml_string = re.sub(r'\sxmlns(?::\w+)?="[^"]*"', '', xml_string)
        
        return xml_string

    def _get_element_text(self, element, paths, default=''):
        """Try multiple paths to find an element and get its text."""
        for path in paths:
            found = element.find(path)
            if found is not None and found.text:
                return found.text
        return default

    def _xml_to_dict(self, xml_string: str) -> dict:
        """Convert XML string to dictionary."""
        try:
            # Sanitize XML before parsing
            xml_string = self._sanitize_xml(xml_string)
            root = ET.fromstring(xml_string)
            
            # Initialize data dictionary
            data = {}
            
            # Extract nota fiscal number (try multiple paths)
            nf_paths = ['.//nNF', './/ide/nNF', './/infNFe//nNF']
            data['numero_nf'] = self._get_element_text(root, nf_paths)
                
            # Extract emission date (try multiple paths)
            date_paths = ['.//dhEmi', './/ide/dhEmi', './/infNFe//dhEmi']
            data['data_emissao'] = self._get_element_text(root, date_paths)
                
            # Extract total value (try multiple paths)
            value_paths = ['.//vNF', './/ICMSTot/vNF', './/infNFe//vNF']
            total_value = self._get_element_text(root, value_paths, '0')
            try:
                data['valor_total'] = float(total_value)
            except ValueError:
                data['valor_total'] = 0.0
                
            # Extract emitter (company) info
            emit_paths = ['.//emit', './/infNFe//emit']
            emit = None
            for path in emit_paths:
                emit = root.find(path)
                if emit is not None:
                    break
                    
            if emit is not None:
                data['emitente'] = {
                    'nome': self._get_element_text(emit, ['xNome']),
                    'cnpj': self._get_element_text(emit, ['CNPJ']),
                }
                
            # Extract destination (client) info
            dest_paths = ['.//dest', './/infNFe//dest']
            dest = None
            for path in dest_paths:
                dest = root.find(path)
                if dest is not None:
                    break
                    
            if dest is not None:
                data['destinatario'] = {
                    'nome': self._get_element_text(dest, ['xNome']),
                    'cnpj': self._get_element_text(dest, ['CNPJ']),
                }
                
            # Extract products
            products = []
            det_paths = ['.//det', './/infNFe//det']
            for det_path in det_paths:
                det_elements = root.findall(det_path)
                if det_elements:
                    for det in det_elements:
                        prod = det.find('prod')
                        if prod is not None:
                            try:
                                quantity = float(self._get_element_text(prod, ['qCom'], '0'))
                            except ValueError:
                                quantity = 0.0
                                
                            try:
                                unit_value = float(self._get_element_text(prod, ['vUnCom'], '0'))
                            except ValueError:
                                unit_value = 0.0
                                
                            try:
                                total_value = float(self._get_element_text(prod, ['vProd'], '0'))
                            except ValueError:
                                total_value = 0.0
                                
                            product = {
                                'codigo': self._get_element_text(prod, ['cProd']),
                                'descricao': self._get_element_text(prod, ['xProd']),
                                'quantidade': quantity,
                                'valor_unitario': unit_value,
                                'valor_total': total_value,
                            }
                            products.append(product)
                    break  # If we found products in one path, no need to try others
                    
            data['produtos'] = products
            
            return data
        except ET.ParseError as e:
            raise ValueError(f"Erro ao fazer parse do XML: {str(e)}")
        except Exception as e:
            raise ValueError(f"Erro ao processar XML: {str(e)}")
    
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

class NFSystem:
    def __init__(self):
        self.audit_tool = InvoiceAuditTool()
        self.current_file: Optional[str] = None
        self.current_result: Optional[str] = None
        self.analysis_result: Optional[str] = None

    def _format_currency(self, value: float) -> str:
        """Formata valores monetários no padrão brasileiro."""
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _format_invoice_data(self, invoice: Dict) -> str:
        """Formata os dados da nota fiscal de forma legível."""
        output = []
        output.append("=== DADOS DA NOTA FISCAL ===\n")
        output.append(f"Número da NF: {invoice['invoice_id']}")
        output.append(f"Cliente ID: {invoice['customer_id']}")
        output.append(f"Fornecedor ID: {invoice['supplier_id']}")
        
        # Items
        output.append("\nITENS:")
        output.append("-" * 60)
        output.append(f"{'Descrição':<30} {'Qtd':<8} {'Valor Unit.':<15} {'Total':<15}")
        output.append("-" * 60)
        
        total_items = 0.0
        for item in invoice['items']:
            unit_price = float(item['unit_price'])
            quantity = float(item['quantity'])
            total = unit_price * quantity
            total_items += total
            
            output.append(
                f"{item['description']:<30} "
                f"{quantity:<8.0f} "
                f"{self._format_currency(unit_price):<15} "
                f"{self._format_currency(total):<15}"
            )
        
        output.append("-" * 60)
        output.append(f"{'Subtotal:':<39} {self._format_currency(total_items):>20}")
        
        # Impostos
        output.append("\nIMPOSTOS:")
        output.append("-" * 40)
        total_taxes = 0.0
        for tax_name, tax_value in invoice['taxes'].items():
            total_taxes += float(tax_value)
            output.append(f"{tax_name:<20} {self._format_currency(float(tax_value)):>19}")
        
        output.append("-" * 40)
        output.append(f"{'Total Impostos:':<20} {self._format_currency(total_taxes):>19}")
        
        # Total Geral
        output.append("\n" + "=" * 40)
        output.append(f"{'TOTAL NF:':<20} {self._format_currency(float(invoice['total'])):>19}")
        output.append("=" * 40)
        
        return "\n".join(output)

    def select_file(self) -> Tuple[bool, str]:
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        file_path = filedialog.askopenfilename(
            title="Selecione o arquivo XML da nota fiscal",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if file_path:
            try:
                # Tenta diferentes codificações
                encodings = ['utf-8', 'iso-8859-1', 'latin1', 'cp1252']
                xml_content = None
                
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            xml_content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue
                
                if xml_content is None:
                    # Se nenhuma codificação funcionou, tenta leitura binária
                    with open(file_path, 'rb') as f:
                        xml_content = f.read().decode('utf-8', errors='ignore')
                
                invoice_data = self.audit_tool._xml_to_dict(xml_content)
                self.current_file = file_path
                formatted_data = self._format_invoice_data(invoice_data)
                return True, f"Arquivo selecionado: {file_path}\n\n{formatted_data}"
            except Exception as e:
                return False, f"Erro ao ler o arquivo: {str(e)}\nTente verificar se o arquivo está em um formato XML válido e se não está corrompido."
        return False, "Nenhum arquivo selecionado"

    def analyze_invoice(self) -> Tuple[bool, str]:
        if not self.current_file:
            return False, "Nenhum arquivo selecionado. Por favor, selecione um arquivo primeiro."
        
        try:
            with open(self.current_file, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            invoice_data = self.audit_tool._xml_to_dict(xml_content)
            formatted_data = self._format_invoice_data(invoice_data)
            self.current_result = self.audit_tool._run(xml_content)
            
            # Generate AI analysis
            prompt = f"""
            Você é um assistente de auditoria fiscal. Analise este relatório de auditoria e forneça insights:
            
            {self.current_result}
            
            Por favor, forneça:
            1. Resumo das descobertas
            2. Avaliação de risco
            3. Ações recomendadas
            """
            
            response = model.generate_content(prompt)
            self.analysis_result = response.text
            
            return True, f"{formatted_data}\n\nAnálise concluída com sucesso!"
        except Exception as e:
            return False, f"Erro durante a análise: {str(e)}"

    def save_results(self) -> Tuple[bool, str]:
        if not self.current_result:
            return False, "Nenhuma análise realizada. Por favor, analise um arquivo primeiro."
        
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.asksaveasfilename(
            title="Salvar resultado da análise",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(self.current_file, 'r', encoding='utf-8') as f:
                    xml_content = f.read()
                invoice_data = self.audit_tool._xml_to_dict(xml_content)
                formatted_data = self._format_invoice_data(invoice_data)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(formatted_data)
                    f.write("\n\n")
                    f.write("=== RELATÓRIO DE AUDITORIA ===\n\n")
                    f.write(self.current_result)
                    if self.analysis_result:
                        f.write("\n\n=== ANÁLISE DA IA ===\n\n")
                        f.write(self.analysis_result)
                return True, f"Resultados salvos em: {file_path}"
            except Exception as e:
                return False, f"Erro ao salvar arquivo: {str(e)}"
        return False, "Operação cancelada"

    def send_email(self) -> Tuple[bool, str]:
        if not self.current_result:
            return False, "Nenhuma análise realizada. Por favor, analise um arquivo primeiro."
        
        # Get email details from environment variables or ask user
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        sender_email = os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("SENDER_PASSWORD")
        
        if not all([sender_email, sender_password]):
            return False, "Credenciais de email não configuradas. Configure as variáveis de ambiente SENDER_EMAIL e SENDER_PASSWORD."
        
        # Create email content
        receiver_email = input("Digite o email do destinatário: ")
        
        try:
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = receiver_email
            msg['Subject'] = f"Relatório de Auditoria - NF {datetime.now().strftime('%Y-%m-%d')}"
            
            with open(self.current_file, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            invoice_data = self.audit_tool._xml_to_dict(xml_content)
            formatted_data = self._format_invoice_data(invoice_data)
            
            body = formatted_data
            body += "\n\n=== RELATÓRIO DE AUDITORIA ===\n\n"
            body += self.current_result
            if self.analysis_result:
                body += "\n\n=== ANÁLISE DA IA ===\n\n"
                body += self.analysis_result
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect and send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            return True, f"Email enviado com sucesso para {receiver_email}"
        except Exception as e:
            return False, f"Erro ao enviar email: {str(e)}"

def show_menu():
    menu = """
    === SISTEMA DE ANÁLISE DE NOTAS FISCAIS ===
    
    1. Selecionar arquivo XML
    2. Analisar nota fiscal
    3. Salvar resultados
    4. Enviar resultados por email
    5. Sair
    
    Escolha uma opção: """
    return input(menu)

# Example usage
if __name__ == "__main__":
    import sys
    import unittest
    import argparse
    
    # Configuração do parser de argumentos
    parser = argparse.ArgumentParser(description='Ferramenta de Análise de Nota Fiscal')
    parser.add_argument('--test', action='store_true', help='Executar suite de testes')
    parser.add_argument('--file', type=str, help='Caminho para o arquivo XML da nota fiscal a ser analisada')
    args = parser.parse_args()
    
    # Check if --test parameter is provided
    if args.test:
        # Run tests
        import test_nf
        unittest.main(module=test_nf, argv=[sys.argv[0]])
        sys.exit(0)
        
    # Configure Gemini
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    def generate_sample_xml():
        root = ET.Element("invoice")
        ET.SubElement(root, "invoice_id").text = "INV-2025-001"
        ET.SubElement(root, "supplier_id").text = "789"
        ET.SubElement(root, "customer_id").text = "123"
        
        items = ET.SubElement(root, "items")
        item1 = ET.SubElement(items, "item")
        ET.SubElement(item1, "description").text = "Product A"
        ET.SubElement(item1, "quantity").text = "2"
        ET.SubElement(item1, "unit_price").text = "100.00"
        
        item2 = ET.SubElement(items, "item")
        ET.SubElement(item2, "description").text = "Product B"
        ET.SubElement(item2, "quantity").text = "1"
        ET.SubElement(item2, "unit_price").text = "150.00"
        
        taxes = ET.SubElement(root, "taxes")
        ET.SubElement(taxes, "ICMS").text = "63.00"
        ET.SubElement(taxes, "IPI").text = "52.50"
        ET.SubElement(taxes, "PIS").text = "5.78"
        ET.SubElement(taxes, "COFINS").text = "26.60"
        
        ET.SubElement(root, "total").text = "350.00"
        
        return ET.tostring(root, encoding='unicode')

    # If file is provided, read and analyze it
    if args.file:
        try:
            with open(args.file, 'r') as f:
                invoice_xml = f.read()
        except FileNotFoundError:
            print(f"Erro: Arquivo {args.file} não encontrado")
            sys.exit(1)
    else:
        # Use sample invoice if no file provided
        invoice_xml = generate_sample_xml()

    # Initialize system
    system = NFSystem()
    
    while True:
        choice = show_menu()
        
        if choice == "1":
            success, message = system.select_file()
            print(f"\n{message}\n")
            
        elif choice == "2":
            success, message = system.analyze_invoice()
            print(f"\n{message}")
            if success:
                print("\nRelatório de Auditoria:")
                print(system.current_result)
                print("\nAnálise da IA:")
                print(system.analysis_result)
            print()
            
        elif choice == "3":
            success, message = system.save_results()
            print(f"\n{message}\n")
            
        elif choice == "4":
            success, message = system.send_email()
            print(f"\n{message}\n")
            
        elif choice == "5":
            print("\nEncerrando o sistema...")
            sys.exit(0)
            
        else:
            print("\nOpção inválida. Por favor, escolha uma opção válida.\n")
