# Interface local do GeradorIaExercicios

Uma interface no navegador para preencher os parâmetros, gerar exercícios e consultar o JSON retornado pelo gerador.

## Instalação e execução

Na raiz do repositório, ative seu ambiente virtual e instale o pacote:

```bash
python -m pip install -e .
```

Para gerar pela interface, configure a chave de OpenAI, Gemini ou Grok em `.env` na raiz ou em `exercise_ai/.env`. Consulte as variáveis e os passos para Windows, Linux e macOS no [README principal](../README.md#geração-com-ia).

```bash
python demo/serve.py
```

Abra **[http://[::1]:8642/](http://[::1]:8642/)**. Para encerrar, pressione `Ctrl+C` no terminal.

## O que experimentar

1. Preencha o tópico e a quantidade de exercícios (até 40).
2. Distribua essa quantidade entre fáceis, médios e difíceis.
3. Escolha provedor, modelo e nível de raciocínio quando suportado.
4. Gere e consulte as abas **Exercícios** e **JSON**.
5. Abra **Uso** para consultar registros locais de sessões, tokens e estimativas de custo quando disponíveis.

A seleção de modelos usa um catálogo local, sem consultar o provedor. Nem todo modelo listado estará disponível para sua conta. As estimativas locais de custo não substituem a cobrança do provedor.

A interface não possui campo de habilidades BNCC. Para testar a geração local sem chave, siga o [exemplo offline](../README.md#experimente-sem-chave-de-api) pela CLI.

## Funcionamento local

O servidor escuta somente em **`[::1]:8642`**, o endereço de loopback IPv6 do seu computador. Use a URL com colchetes acima. Se IPv6 estiver desabilitado, habilite-o para usar a interface ou utilize a CLI.

As chamadas de geração são sequenciais: um pedido adicional durante uma geração recebe HTTP 409. A interface preserva o último lote bem-sucedido ao mostrar um erro.

Essa demonstração foi feita para uso local; ela não é um servidor de produção ou uma API para exposição na internet. Não há autenticação de usuários ou suporte a implantação pública nessa interface.

As rotas de consulta de uso leem arquivos em `exercise_ai/token-usage/`. Não compartilhe esses registros sem revisar o conteúdo. Mantenha `.env` e chaves fora dos commits.

## Testes

Os testes usam mocks e arquivos de exemplo, sem consumir APIs:

```bash
python -m pip install -e ".[dev]"
python -m pytest demo/tests -q
```
