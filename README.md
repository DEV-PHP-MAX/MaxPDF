# MAX PDF

**Ferramentas para PDF**

Aplicativo desktop para Windows, 100% local e offline, para manipulação
rápida de documentos PDF em lote: inverter páginas, juntar, separar,
girar e converter imagens em PDF — sem perder qualidade e sem nunca
enviar seus arquivos para a internet.

## Download

Baixe o `MaxPDF.exe` na página de
[Releases](https://github.com/DEV-PHP-MAX/MaxPDF/releases/latest) e
execute. Não precisa instalar nada: é um arquivo só, que pode ser
copiado para qualquer computador com Windows 10 ou 11 (64 bits).

### "O Windows protegeu o computador"

Na primeira vez, o Windows pode mostrar esse aviso. Ele aparece porque
o Max PDF é um projeto pessoal e não tem assinatura digital, que é
paga. Não é sinal de vírus. Para abrir:

1. Clique em **Mais informações**.
2. Clique em **Executar assim mesmo**.

O aviso não aparece de novo para o mesmo arquivo. Todo o código-fonte
está neste repositório; se preferir, você pode gerar o `.exe` você
mesmo (veja [Geração do executável](#geração-do-executável-maxpdfexe)).

Se algum antivírus bloquear o arquivo, adicione-o às exceções. Isso às
vezes acontece com programas Python empacotados em um único `.exe`.

### Se o app não abrir

O Max PDF usa o Microsoft Edge WebView2 Runtime para desenhar a janela.
Ele já vem no Windows 11 e nas versões atualizadas do Windows 10. Se a
janela não aparecer, instale o
[WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)
(gratuito, da Microsoft) e tente de novo.

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

- Python 3.12 ou mais novo (testado no 3.14)
- Windows 10 ou 11 com o Microsoft Edge WebView2 Runtime (já vem
  instalado no Windows 11 e nas versões atualizadas do Windows 10)
- Dependências listadas em `requirements.txt`:
  - [`pywebview`](https://pywebview.flowrl.com/) — janela nativa que exibe a interface HTML
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

Com `python src/main.py --debug` o app abre com as ferramentas de
desenvolvedor do WebView (inspecionar elementos, console).

Para mexer só no visual, dá para abrir `src/web/index.html` em um
servidor local qualquer (ex.: `python -m http.server -d src/web`): fora
do app, a interface usa uma simulação da API com arquivos de exemplo.
Acrescente `?motion` à URL para ver as animações mesmo com "reduzir
movimento" ligado no sistema.

## Interface

A interface fica em `src/web/` (HTML, CSS e JavaScript puro) e roda
dentro de uma janela nativa do pywebview. Todas as bibliotecas estão
copiadas na pasta `src/web/vendor/`, sem CDN, então o app continua
100% offline:

- [GSAP](https://gsap.com/) 3.13 com os plugins Flip e SplitText —
  animações de entrada, troca de ferramenta, reordenação da lista,
  barra de progresso e resumo final
- [Lucide](https://lucide.dev/) — ícones
- Fonte [Inter](https://rsms.me/inter/) (variável, em `src/web/fonts/`)

O JavaScript conversa com o Python pela `window.pywebview.api`
(classe `Api` em `src/desktop/api.py`). Progresso e fim de
processamento chegam do Python via `window.maxpdf.receive(...)`.

A interface tem tema escuro e claro (botão no rodapé do menu) e
respeita a opção "reduzir movimento" do Windows.

## Geração do executável (MaxPDF.exe)

No Windows, com o Python instalado, basta clicar duas vezes em:

```
GERAR_EXE.bat
```

O script instala as dependências de build, limpa builds anteriores e
executa o PyInstaller equivalente a:

```bash
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "MaxPDF" --icon "assets\icons\maxpdf.ico" ^
    --add-data "src\web;src\web" ^
    --add-data "assets\icons\maxpdf.ico;assets\icons" src/main.py
```

O executável final é gerado em `dist/MaxPDF.exe` e pode ser copiado
para qualquer computador com Windows 10/11 — não requer Python,
pypdf, Pillow, pywebview ou PyInstaller instalados na máquina de
destino (só o WebView2 Runtime, que o Windows já traz).

## Estrutura do projeto

```
MaxPDF/
├── src/
│   ├── main.py                 # Ponto de entrada
│   ├── version.py              # Versão única do aplicativo (SemVer)
│   │
│   ├── desktop/                # Janela nativa (pywebview)
│   │   ├── app.py              # Cria a janela e liga o arrastar-e-soltar
│   │   └── api.py              # Ponte JS ↔ Python: filas, diálogos, execução
│   │
│   ├── web/                    # Interface (HTML/CSS/JS, sem build)
│   │   ├── index.html
│   │   ├── styles.css          # Tokens de cor, temas claro/escuro
│   │   ├── app.js              # Telas, animações GSAP, simulação p/ preview
│   │   ├── vendor/             # GSAP, Flip, SplitText, Lucide (locais)
│   │   └── fonts/              # Inter variável
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
├── assets/icons/                # Logo: maxpdf.svg (fonte), .png 512 px e .ico 16–256 px
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
   utilitários sem dependência de UI em `utils/`, ponte com a interface
   em `desktop/api.py` e telas em `web/`.
3. Reaproveite os componentes já existentes (`BatchRunner`,
   `FileQueue`, `FolderScanner`, a `Api` e os blocos do `app.js`) em vez de duplicar
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
  já foi preparada para recebê-las como novos módulos em `tools/`,
  um ramo em `Api.run` e uma entrada em `TOOLS` no `app.js`.
