# Screen Ruler para o Omarchy

Mede qualquer coisa na tela. É o
[PowerToys Screen Ruler](https://learn.microsoft.com/windows/powertoys/screen-ruler)
portado para o [Omarchy](https://omarchy.org).

*[Read in English](README.md)*

```bash
omarchy-screen-ruler            # arraste para medir; clique para medir o que está embaixo
omarchy-screen-ruler bounds 320 240
omarchy-screen-ruler measure 100 100 500 400
```

- **Arraste** para uma distância: uma caixa com linhas-guia até as bordas da tela e uma
  leitura ao vivo que acompanha o ponteiro.
- **Clique** para o *bounds*: a extensão do que estiver sob o ponteiro — um botão, um
  painel, o espaço entre duas coisas — deduzida dos próprios pixels.
- **Botão direito** limpa a caixa, **Ctrl+C** copia a medida, **Esc** sai.

As medidas saem nos pixels reais da tela e em centímetros, quando o monitor informa o
próprio tamanho.

## Como o bounds funciona

A tela é capturada no instante em que a régua abre — antes de o overlay cobri-la — e a
medição caminha para fora a partir do ponto clicado até a cor mudar mais do que a
tolerância. Sem informação de janela, sem introspecção de toolkit: funciona sobre
qualquer coisa que esteja na tela, inclusive um vídeo, uma captura ou outra máquina por
VNC.

A captura é `grim -t ppm`, um cabeçalho binário e três bytes por pixel, que o Python lê
sem dependência nenhuma. PNG significaria zlib e uma máquina de filtros, ou o Pillow,
para ler alguns pixels.

## ⚠️ Pixels, escala, e o que "px" quer dizer

Em uma tela com escala 2, um arrasto de 100 pixels cobre 200 pixels reais. A leitura
mostra os da tela — os que um designer chama de "px" — e marca `@2x`, para que o número
nunca pareça o dobro da caixa de onde veio.

Uma tela virtual ou remota informa o tamanho físico como 0×0mm. Em vez de inventar um
DPI e colocar um número em centímetros confiantemente errado na tela, a régua
simplesmente omite.

## Instalação

### Arch / Omarchy

```bash
sudo pacman -U omarchy-screen-ruler-*-any.pkg.tar.zst   # dos Releases
omarchy-screen-ruler setup
```

No `~/.config/hypr/bindings.lua`:

```lua
o.bind("SUPER + SHIFT + R", "Régua de tela", "omarchy-screen-ruler")
```

Preferências em `~/.config/omarchy-screen-ruler/config.json`:

```json
{ "colour": "", "tolerance": 12, "thickness": 2 }
```

A `tolerance` é quanta variação de cor ainda conta como a mesma região — aumente para
gradientes, diminua para separar bordas suavizadas.

### Em outras distros

`pipx install git+https://github.com/andrebbruno/omarchy-screen-ruler`, com `quickshell`
e `grim`.

## Comandos

```
omarchy-screen-ruler                     a régua
omarchy-screen-ruler bounds <x> <y>      a extensão da cor ali  (--json)
omarchy-screen-ruler measure <x1> <y1> <x2> <y2>
omarchy-screen-ruler status              o ponteiro, o monitor e o tamanho real dele
```

O `bounds` e o `measure` são o que o próprio overlay chama, então qualquer outra coisa
também pode chamá-los.

## Desenvolvimento

```bash
python -m pytest tests -q     # 42 testes, sem precisar de tela
```

O leitor de PPM e a medição são funções puras sobre um buffer de pixels, então os testes
montam telinhas — um bloco azul no branco — e conferem exatamente os limites, a
tolerância, as bordas, a escala e a conversão de unidades. Depois o overlay foi
exercitado numa área de trabalho real: um arrasto medindo e um clique achando as bordas
de um painel.

## Licença

MIT © Andre Bruno
