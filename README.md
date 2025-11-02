# Sistema de Análise de Notas Fiscais

Este é um sistema de análise de notas fiscais eletrônicas (NF-e) que oferece uma interface gráfica para processamento, validação e análise de documentos fiscais. O sistema utiliza inteligência artificial para fornecer insights sobre as notas fiscais analisadas.

## Funcionalidades

- 📄 Leitura e processamento de arquivos XML de NF-e
- 🔍 Validação automática de dados fiscais
- 💡 Análise inteligente usando IA (Gemini Pro)
- 📊 Visualização clara dos dados da nota fiscal
- 💾 Exportação de resultados
- 📧 Envio de relatórios por email
- 🖥️ Interface gráfica intuitiva

## Requisitos

- Python 3.8 ou superior
- Bibliotecas Python necessárias:
  ```bash
  pip install google-generativeai langchain-core
  ```
- Chave de API do Google (Gemini)
  - Defina a variável de ambiente: `GOOGLE_API_KEY`

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/mrsx0/nf.git
   cd nf
   ```

2. Configure a chave da API do Google:
   ```bash
   export GOOGLE_API_KEY="sua-chave-aqui"
   ```

3. Execute o programa:
   ```bash
   python3 nf.py
   ```

## Como Usar

1. **Iniciar o Programa**
   - Execute o script `nf.py`
   - Uma interface gráfica será aberta

2. **Selecionar Arquivo**
   - Clique no botão "Selecionar Arquivo"
   - Escolha um arquivo XML de NF-e

3. **Analisar Nota Fiscal**
   - Clique em "Analisar NF"
   - O sistema processará o arquivo e mostrará:
     - Dados da nota fiscal
     - Resultados da validação
     - Análise da IA

4. **Salvar Resultados**
   - Clique em "Salvar Resultados"
   - Escolha onde salvar o arquivo de relatório

## Funcionalidades Detalhadas

### Processamento de XML
- Suporte a diferentes codificações (UTF-8, ISO-8859-1, etc.)
- Tratamento automático de namespaces
- Validação de estrutura do XML

### Análise Fiscal
- Verificação de campos obrigatórios
- Validação de cálculos
- Verificação de consistência de dados

### Análise com IA
- Identificação de padrões
- Sugestões de melhorias
- Detecção de anomalias

### Interface Gráfica
- Design intuitivo
- Feedback visual de operações
- Área de visualização com rolagem
- Barra de status informativa

## Configuração de Email

Para usar a função de envio de email, configure as seguintes variáveis de ambiente:
```bash
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export SENDER_EMAIL="seu-email@gmail.com"
export SENDER_PASSWORD="sua-senha-de-app"
```

## Estrutura do Projeto

```
nf/
├── nf.py              # Arquivo principal
├── README.md          # Este arquivo
└── LICENSE            # Licença do projeto
```

## Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## Suporte

Para suporte, abra uma issue no GitHub ou envie um email para o mantenedor do projeto.

## Release Notes

### Versão 1.1.0 (29 de Outubro, 2025)
- ✨ **Nova Interface Gráfica**
  - Adicionada interface gráfica com tkinter
  - Novo layout mais intuitivo e amigável
  - Barra de status para feedback visual
  - Área de visualização com rolagem

- 🔧 **Melhorias no Processamento XML**
  - Suporte para múltiplas codificações de caracteres
  - Melhor tratamento de namespaces
  - Correção de bugs na leitura de arquivos

- 🚀 **Recursos Adicionados**
  - Análise com IA usando Gemini Pro
  - Exportação de resultados em formato texto
  - Envio de relatórios por email

### Versão 1.0.0 (15 de Outubro, 2025)
- 🎉 **Lançamento Inicial**
  - Processamento básico de NF-e
  - Validação de campos obrigatórios
  - Verificação de cálculos fiscais
  - Interface de linha de comando
  - Suporte a arquivos XML de NF-e
  - Análise fiscal básica

### Próximas Atualizações Planejadas
- 📊 Geração de gráficos e relatórios visuais
- 📱 Interface responsiva para diferentes tamanhos de tela
- 📦 Suporte a processamento em lote de múltiplos arquivos
- 🔐 Melhorias na segurança e criptografia
- 🌐 Suporte a múltiplos idiomas
- 💾 Integração com banco de dados para histórico

## Autor

- Nome: mrsx0
- GitHub: [@mrsx0](https://github.com/mrsx0)
