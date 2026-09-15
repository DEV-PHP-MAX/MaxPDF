# MAX PDF

**Ferramentas para PDF**

Aplicativo desktop para Windows, 100% local e offline, para manipulação
rápida de documentos PDF em lote: inverter páginas, juntar, separar,
girar e converter imagens em PDF — sem perder qualidade e sem nunca
enviar seus arquivos para a internet.

## Funcionalidades

- **Inverter páginas** — inverte a ordem das páginas de um ou vários
  PDFs de uma só vez, sem rasterizar o conteúdo.
- **Juntar PDFs** — une vários PDFs em um único arquivo, com ordenação
  natural, por caminho, por data de modificação ou totalmente manual
  (arrastar-e-soltar ou botões subir/descer).
- **Separar PDF** — divide um PDF em uma página por arquivo, ou extrai
  páginas/intervalos específicos (ex.: `1-3,5,8-10`).
- **Girar páginas** — gira todas as páginas ou apenas páginas
  específicas em 90°, 180° ou 270°.
- **Imagens → PDF** — converte JPG, PNG, WEBP, BMP e TIFF em um único
  PDF, na ordem escolhida, tratando corretamente transparência (fundo
  branco).

Todas as ferramentas suportam:

- Seleção de arquivos individuais e de pastas inteiras, com **busca
  recursiva** em subpastas (aceita `.pdf` e `.PDF`, ignora duplicados e
  arquivos temporários).
- Processamento em lote de centenas ou milhares de arquivos sem
  travar a interface (tudo roda em segundo plano, com barra de
  progresso real).
- **Cancelamento seguro** a qualquer momento, sem corromper arquivos.
- Um resumo ao final de cada operação, com contagem de sucessos,
  erros e tempo total — um único arquivo com problema nunca interrompe
  o lote inteiro.
- Nomes de saída seguros: nunca sobrescreve um arquivo existente
  (`Lei001.pdf` → `Lei001_1.pdf` → `Lei001_2.pdf`...).
- Preservação opcional da estrutura de subpastas no destino.

O projeto foi estruturado de forma modular para receber novas
ferramentas no futuro (organizar páginas, excluir/extrair páginas,
comprimir, marca d'água, numeração, senha, OCR, etc.) sem precisar
reescrever o que já existe.

## Privacidade

O Max PDF funciona **100% localmente e offline**. Nenhum PDF, imagem,
nome de arquivo, caminho ou metadado é enviado para servidores, APIs
ou serviços externos, em nenhuma circunstância. Todo o processamento
acontece na sua máquina.

Os arquivos originais **nunca** são alterados, substituídos ou
apagados — todas as ferramentas geram novos arquivos em um destino
escolhido por você.

## Requisitos de desenvolvimento

- Python 3.12
- Windows 10 ou 11 (para gerar e usar o `.exe`; o código roda em
  qualquer plataforma com Python + Tkinter durante o desenvolvimento)
- Dependências listadas em `requirements.txt`:
  - [`customtkinter`](https://github.com/TomSchimansky/CustomTkinter) — interface gráfica
  - [`pypdf`](https://github.com/py-pdf/pypdf) — manipulação de PDF sem rasterização
  - [`Pillow`](https://python-pillow.org/) — leitura/conversão de imagens
- Para desenvolvimento/build, também: `pytest` e `pyinstaller`
  (`requirements-dev.txt`)

## Instalação (ambiente de desenvolvimento)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt
```

## Execução em desenvolvimento

No Windows, basta clicar duas vezes em:

```
EXECUTAR_MAX_PDF.bat
```

Ou, manualmente, a partir da raiz do projeto:

```bash
python src/main.py
```

## Geração do executável (MaxPDF.exe)

No Windows, com o Python instalado, basta clicar duas vezes em:

```
GERAR_EXE.bat
```

O script instala as dependências de build, limpa builds anteriores e
executa o PyInstaller equivalente a:

```bash
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "MaxPDF" --collect-all customtkinter src/main.py
```

O executável final é gerado em `dist/MaxPDF.exe` e pode ser copiado
para qualquer computador com Windows 10/11 — não requer Python,
pypdf, Pillow, CustomTkinter ou PyInstaller instalados na máquina de
destino.

## Estrutura do projeto

```
MaxPDF/
├── src/
│   ├── main.py                 # Ponto de entrada
│   ├── version.py              # Versão única do aplicativo (SemVer)
│   │
│   ├── ui/                     # Interface gráfica (CustomTkinter)
│   │   ├── main_window.py      # Janela principal (menu lateral + conteúdo)
│   │   ├── sidebar.py          # Menu lateral azul
│   │   ├── file_list.py        # Lista de arquivos reutilizável (Treeview)
│   │   ├── progress.py         # Barra de progresso + cancelamento
│   │   ├── dialogs.py          # Diálogos de resumo/erro
│   │   ├── theme.py            # Cores, fontes e DPI awareness
│   │   └── tool_panels/        # Um painel por ferramenta
│   │       ├── common.py       # Seleção de arquivos/pastas, busca assíncrona
│   │       ├── reverse_panel.py
│   │       ├── merge_panel.py
│   │       ├── split_panel.py
│   │       ├── rotate_panel.py
│   │       └── images_panel.py
│   │
│   ├── tools/                  # Lógica de manipulação de PDF (sem UI)
│   │   ├── reverse.py
│   │   ├── merge.py
│   │   ├── split.py
│   │   ├── rotate.py
│   │   └── images_to_pdf.py
│   │
│   └── utils/                  # Utilitários reutilizáveis
│       ├── file_scanner.py     # Busca recursiva + fila de arquivos (dedup)
│       ├── natural_sort.py     # Ordenação natural ("Lei 2" < "Lei 10")
│       ├── page_ranges.py      # Parsing de intervalos ("1-3,5,8-10")
│       ├── paths.py            # Normalização e caminhos relativos
│       ├── naming.py           # Nomes de saída seguros (nunca sobrescreve)
│       ├── output_paths.py     # Preservação de estrutura de subpastas
│       ├── batch.py            # Motor genérico de processamento em lote
│       ├── logger.py           # Logging local
│       └── helpers.py          # Diversos (tempo, pastas, recursos)
│
├── assets/icons/                # Ícones do aplicativo
├── tests/                       # Testes automatizados (pytest)
├── requirements.txt             # Dependências de runtime
├── requirements-dev.txt         # + pytest e pyinstaller
├── EXECUTAR_MAX_PDF.bat         # Executa em desenvolvimento
├── GERAR_EXE.bat                # Gera dist/MaxPDF.exe
├── CHANGELOG.md
└── .gitignore
```

## Versionamento

O projeto segue [Semantic Versioning](https://semver.org/lang/pt-BR/)
(`MAJOR.MINOR.PATCH`). A versão vive em um único local,
`src/version.py`, e é importada por todo o restante do aplicativo —
nunca é escrita manualmente em mais de um arquivo.

Consulte o [`CHANGELOG.md`](CHANGELOG.md) para o histórico de versões.

## Como contribuir / desenvolver

1. Crie uma branch a partir de `main`.
2. Siga a arquitetura modular existente: lógica de PDF em `tools/`,
   utilitários sem dependência de UI em `utils/`, e interface em `ui/`.
3. Reaproveite os componentes já existentes (`FileListWidget`,
   `ProgressPanel`, `BatchRunner`, `FileQueue`, etc.) em vez de duplicar
   lógica de seleção de arquivos, busca recursiva, barra de progresso
   ou cancelamento.
4. Adicione testes em `tests/` para qualquer lógica pura (parsing,
   ordenação, nomes, caminhos).
5. Use [Conventional Commits](https://www.conventionalcommits.org/pt-br/)
   (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `ui:`, `release:`).
6. Rode `pytest` antes de abrir um PR.

## Limitações conhecidas

- PDFs protegidos por senha não são processados automaticamente; o
  Max PDF tenta apenas uma senha vazia e, se falhar, reporta o
  arquivo como erro no resumo do lote (a remoção de senha é uma
  ferramenta futura planejada).
- A geração do `.exe` é específica para Windows (PyInstaller
  `--onefile --windowed`); em outras plataformas, execute a partir do
  código-fonte com Python.
- O aplicativo não modifica PDFs criptografados com criptografia forte
  sem a senha correta, por design — isso é uma proteção, não um bug.
- Ferramentas futuras (organizar páginas visualmente, excluir/extrair
  páginas, comprimir, marca d'água, numeração, senha, metadados, OCR,
  assinatura, comparação) ainda não estão implementadas; a arquitetura
  já foi preparada para recebê-las como novos módulos em `tools/` e
  `ui/tool_panels/`.
