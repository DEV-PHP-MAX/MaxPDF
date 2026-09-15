# Changelog

Todas as mudanças notáveis deste projeto são documentadas neste
arquivo. O formato segue aproximadamente o
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e o
projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.1.0] - 2026-09-15

### Adicionado

- O arrastar-e-soltar na ferramenta Juntar PDFs (e em Imagens → PDF)
  agora dá feedback visual em tempo real: a linha arrastada acompanha
  o cursor e a lista é redesenhada a cada movimento do mouse, em vez
  de só reordenar no momento em que o botão é solto.

### Corrigido

- Soltar o item arrastado acima da primeira linha ou abaixo da
  última agora move corretamente para o início/fim da lista — antes,
  essa ação não tinha efeito nenhum (só funcionava soltando bem em
  cima de outra linha existente).

## [1.0.2] - 2026-09-15

### Corrigido

- Corrige o botão principal de cada ferramenta (ex.: "INVERTER
  PÁGINAS", "JUNTAR PDFs", "GIRAR PÁGINAS") ficando cortado/invisível
  na parte inferior da janela quando a lista de arquivos e as demais
  opções da tela já ocupavam todo o espaço vertical disponível —
  especialmente perceptível com escala de DPI do Windows acima de
  100%. Os painéis agora têm rolagem própria, garantindo que todos os
  botões e controles fiquem sempre acessíveis, independentemente do
  tamanho da janela ou da escala de tela.
- Reduz a altura padrão da lista de arquivos e aumenta ligeiramente a
  altura padrão da janela para que o conteúdo caiba sem rolagem na
  maioria dos casos comuns.

## [1.0.1] - 2026-09-15

### Corrigido

- Melhora o contraste e a aparência dos botões em toda a interface:
  o botão secundário ("Selecionar pasta", "Remover selecionado",
  "Subir"/"Descer") agora usa fundo branco com borda visível em vez
  de se confundir com o fundo da página.
- Corrige o estado desabilitado dos botões principais (ex.: "INVERTER
  PÁGINAS", "CANCELAR"), que antes ficava com uma cor "lavada" da cor
  original e parecia quebrado; agora usa um cinza neutro consistente
  enquanto a ação não está disponível.
- Centraliza a criação de botões em `ui/buttons.py`, eliminando
  duplicação de estilo entre `file_list.py`, `progress.py` e os
  painéis de ferramenta.

## [1.0.0] - 2026-09-15

### Adicionado

- Estrutura inicial do projeto (`src/`, `tests/`, arquitetura modular
  `ui/` + `tools/` + `utils/`).
- Ferramenta **Inverter páginas**, com preservação opcional da
  estrutura de subpastas.
- Ferramenta **Juntar PDFs**, com ordenação natural, por caminho, por
  data de modificação e ordem manual (arrastar-e-soltar + subir/descer).
- Ferramenta **Separar PDF**, com os modos "uma página por arquivo" e
  "páginas/intervalos específicos".
- Ferramenta **Girar páginas** (90°/180°/270°), em todas as páginas ou
  em páginas específicas.
- Ferramenta **Imagens → PDF**, com tratamento de transparência (fundo
  branco) e reordenação manual.
- Seleção de arquivos e de pastas com busca recursiva em subpastas,
  em thread separada (interface nunca trava).
- Deduplicação automática de arquivos por caminho absoluto normalizado.
- Geração segura de nomes de saída (nunca sobrescreve arquivos
  existentes).
- Barra de progresso real, cancelamento seguro e resumo final para
  todas as operações em lote.
- Identidade visual completa (paleta azul `#1E90FF`, menu lateral,
  cards brancos, DPI awareness no Windows).
- Logging local (sem registrar conteúdo de documentos).
- Suíte de testes automatizados (`pytest`) para ordenação natural,
  parsing de intervalos, nomes duplicados, busca recursiva e
  preservação de estrutura de pastas.
- Scripts `EXECUTAR_MAX_PDF.bat` e `GERAR_EXE.bat`, sem caminhos fixos
  de máquina.

### Notas

- Primeira versão estável do Max PDF, cobrindo as cinco ferramentas
  principais do escopo inicial. Arquitetura preparada para receber
  novas ferramentas sem alterar as existentes.
