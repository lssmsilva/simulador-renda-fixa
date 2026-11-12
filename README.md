# Vale a pena? Simulador de renda fixa

Simulador gratuito que compara **poupança, CDB, LCI/LCA e Tesouro Selic** e responde, em linguagem simples, se o dinheiro rende mais do que a inflação e do que a poupança, já com o imposto descontado.

> Projeto de portfólio de dados. É uma simulação educativa, **não é recomendação de investimento**.

**Veja funcionando:** _(link do site, depois de publicar)_

## O que ele faz
- Pede só valor, prazo e, se quiser, aporte mensal e o % do CDI de uma oferta.
- Mostra quanto sobra no bolso em cada produto, se ganha da inflação e da poupança, e como o dinheiro cresce mês a mês.
- Explica os termos (CDI, inflação, IR, FGC, carência) com um toque.
- Atualiza os dados sozinho todo dia, sem ninguém precisar rodar nada.

## Como funciona
```
Banco Central (SGS) ─┐
                     ├─> src/coletar.py ──> validação ──> data/dados.json ─┐
Tesouro Transparente ┘                                                    ├─> src/gerar_site.py ──> site/index.html ──> GitHub Pages
regras.json (IR, poupança, custódia, FGC) ────────────────────────────────┘
```
1. **Coleta** (`src/coletar.py`): baixa Selic meta, CDI diário, IPCA mensal e a taxa do Tesouro Selic, e calcula o CDI anualizado e o IPCA de 12 meses.
2. **Validação**: se o CDI divergir da Selic em mais de 0,5 p.p., se faltar dado ou se o IPCA for absurdo, a coleta falha e **nada novo é publicado**. O site continua com o último dado bom.
3. **Regras** (`regras.json`): imposto regressivo, regra da poupança, custódia do Tesouro e FGC ficam fora do código, com data da última conferência.
4. **Página** (`src/gerar_site.py` + `src/template.html`): um único HTML, sem dependências, que calcula tudo no navegador.
5. **Robô** (`.github/workflows`): todo dia roda os testes, coleta, gera a página e publica. Também dá para rodar na mão.

## Decisões de projeto
- Fórmulas em Python (`src/calc.py`, testadas) e espelhadas em JavaScript na página; os testes garantem os números de referência.
- IR calculado por aporte, conforme o tempo de cada um.
- LCI/LCA só aparece a partir de 6 meses (carência típica).
- Premissas explícitas na página: CDI e IPCA constantes no prazo, mês de 30,4 dias, TR considerada zero.

## Rodar no seu computador
```
pip install -r requirements.txt
python -m pytest
python src/coletar.py
python src/gerar_site.py      # abre site/index.html no navegador
```

## Estrutura
```
src/            coleta, cálculo, gerador e template da página
tests/          testes automáticos (21)
regras.json     regras que mudam (imposto, poupança, custódia, FGC)
data/           dados do dia (gerado, não versionado)
site/           página final (gerada, não versionada)
.github/        robô diário de atualização e publicação
```

## Fontes de dados
- Banco Central do Brasil, Sistema Gerenciador de Séries (SGS): Selic meta, CDI, IPCA.
- Tesouro Transparente: preços e taxas do Tesouro Direto.

## Limitações
Não inclui IPCA+, prefixados, ações nem fundos. Não considera carência e liquidez no cálculo, apenas avisa. Resgates antes de 30 dias (IOF) ficam fora.

## Autoria e direitos
Autora: Laura, engenheira eletricista e de telecomunicações, estudante de engenharia e análise de dados.
Todos os direitos reservados. Para usar ou adaptar este projeto, entre em contato.
